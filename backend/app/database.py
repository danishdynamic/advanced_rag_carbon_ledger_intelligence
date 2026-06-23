import logging
import asyncio
import asyncpg
from fastapi import HTTPException
from app.config import settings

logger = logging.getLogger("carbon_ledger.database")

class SplitDatabaseManager:
    def __init__(self):
        self.write_pool: asyncpg.Pool | None = None  # Targets Primary DB
        self.read_pool: asyncpg.Pool | None = None   # Targets Replica DB

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

async def get_read_db():
    """
    Leases a connection from the Read Replica pool.
    Safely falls back to the Primary pool if the replica connection fails to lease.
    """
    connection = None
    fallback_needed = False

    # 1. Attempt to safely lease a connection from the read pool
    if db_manager.read_pool:
        try:
            connection = await db_manager.read_pool.acquire()
        except (asyncpg.InterfaceError, asyncpg.CannotConnectNowError, ConnectionRefusedError, OSError) as e:
            logger.critical(f"Read Replica lease failed. Activating fallback path. Error: {str(e)}")
            fallback_needed = True
    else:
        fallback_needed = True

    # 2. Execute connection lifecycles outside of the acquisition try-block
    if fallback_needed or connection is None:
        if not db_manager.write_pool:
            raise HTTPException(status_code=500, detail="Entire database cluster pool is completely offline.")
        
        logger.info("Routing read request to Primary write pool via fallback connection.")
        async with db_manager.write_pool.acquire() as fallback_conn:
            yield fallback_conn
    else:
        # Connection was successfully obtained from the replica pool
        try:
            yield connection
        finally:
            # Explicitly return connection to the replica pool when the request ends
            await db_manager.read_pool.release(connection)