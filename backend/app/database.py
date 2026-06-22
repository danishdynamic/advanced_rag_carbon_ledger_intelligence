import logging
import asyncpg
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
            
            # Open pools concurrently using asyncio.gather
            import asyncio
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
                    max_size=25,  # Replica gets a larger pool to support heavy concurrent RAG lookups
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

# Instantiate a single global manager to be referenced across the application lifecycle
db_manager = SplitDatabaseManager()

# --- FastAPI Dependency Injectors ---

async def get_write_db():
    """
    Dependency provider for transactional endpoints (Ledger entries, audits).
    Leases an isolated connection from the Primary pool.
    """
    if not db_manager.write_pool:
        raise RuntimeError("Database write pool is not initialized.")
    
    async with db_manager.write_pool.acquire() as connection:
        yield connection

async def get_read_db():
    """
    Dependency provider for heavy analytical/retrieval endpoints (RAG searches).
    Leases an isolated connection from the Read Replica pool.
    """
    if not db_manager.read_pool:
        raise RuntimeError("Database read pool is not initialized.")
    
    async with db_manager.read_pool.acquire() as connection:
        yield connection