import logging
import asyncio
import time
import asyncpg
from fastapi import HTTPException, Request
from app.config import settings

logger = logging.getLogger("carbon_ledger.database")

# ⏳ Global in-memory registry to track user write timestamps.
# (For a multi-container production system, this would look at a shared Redis instance)
user_write_registry = {}

def register_user_write(user_id: str):
    """
    Call this helper function inside your write endpoints (e.g., POST upload) 
    to lock the user's reads to the primary database for the next 2 seconds.
    """
    user_write_registry[user_id] = time.time()


class SplitDatabaseManager:
    def __init__(self):
        self.write_pool: asyncpg.Pool | None = None  # Targets Primary DB (5433)
        self.read_pool: asyncpg.Pool | None = None   # Targets Replica DB (5434)

    async def connect(self):
        """Initializes primary and replica connection pools concurrently."""
        try:
            logger.info("Initializing dual-pool database cluster connections...")
            self.write_pool, self.read_pool = await asyncio.gather(
                asyncpg.create_pool(
                    settings.PRIMARY_DB_URL,
                    min_size=5,
                    max_size=15,
                    command_timeout=30.0,
                ),
                asyncpg.create_pool(
                    settings.REPLICA_DB_URL,
                    min_size=5,
                    max_size=25,
                    command_timeout=60.0,
                )
            )
            logger.info("Database cluster connection pools successfully mounted.")
        except Exception as e:
            logger.error(f"Critical error initializing database cluster: {str(e)}")
            raise e

    async def execute(self, query: str, *args):
        """Direct raw SQL execution interface against the Primary cluster (Startup Recovery)."""
        if not self.write_pool:
            raise RuntimeError("Database write pool is not initialized.")
        return await self.write_pool.execute(query, *args)

    async def disconnect(self):
        """Gracefully drains and closes all active database connections on shutdown."""
        logger.info("Draining database connection pools...")
        if self.write_pool:
            await self.write_pool.close()
        if self.read_pool:
            await self.read_pool.close()
        logger.info("Database pools safely terminated.")


db_manager = SplitDatabaseManager()

# --- FastAPI Dependency Injectors ---

async def get_write_db():
    """Leases an isolated connection from the Primary pool for transactional queries."""
    if not db_manager.write_pool:
        raise RuntimeError("Database write pool is not initialized.")
    
    async with db_manager.write_pool.acquire() as connection:
        yield connection


async def get_read_db(request: Request):
    """
    Leases a connection from the Read Replica pool.
    Intercepts the request and routes to the Primary Write DB if the client 
    recently updated data, mitigating replication lag vulnerabilities.
    """
    # 1. Identify the client user (extract from a header, session, or cookie)
    user_id = request.headers.get("X-User-ID", "anonymous_client")
    
    # 2. Evaluate if the client recently initiated a write sequence
    last_write_timestamp = user_write_registry.get(user_id, 0)
    elapsed_time = time.time() - last_write_timestamp
    
    # 🛡️ If the user updated data less than 2.0 seconds ago, force route to Primary Write Node
    if elapsed_time < 2.0:
        if not db_manager.write_pool:
            raise HTTPException(status_code=500, detail="Primary node offline during write-safety routing.")
        
        logger.warning(f"🔄 RYOW Safety Active for user '{user_id}' ({elapsed_time:.2f}s since write). Routing read to Primary.")
        async with db_manager.write_pool.acquire() as fallback_conn:
            yield fallback_conn
        return

    # 3. Standard Path: Lease connection from the dedicated Read Replica cluster
    connection = None
    fallback_needed = False

    if db_manager.read_pool:
        try:
            connection = await db_manager.read_pool.acquire()
        except (asyncpg.InterfaceError, asyncpg.CannotConnectNowError, ConnectionRefusedError, OSError) as e:
            logger.critical(f"⚠️ Read Replica lease failed. Activating backend pool fallback. Error: {str(e)}")
            fallback_needed = True
    else:
        fallback_needed = True

    if fallback_needed or connection is None:
        if not db_manager.write_pool:
            raise HTTPException(status_code=500, detail="Entire database cluster pool is completely offline.")
        
        logger.info("Routing read request to Primary write pool via fallback connection.")
        async with db_manager.write_pool.acquire() as fallback_conn:
            yield fallback_conn
    else:
        try:
            yield connection
        finally:
            if db_manager.read_pool is not None:
                await db_manager.read_pool.release(connection)