import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import db_manager
from app.routers import compliance
from app.routers import ledger
from app.routers import documents
from app.api import endpoints
from app.routers.analytics import router as analytics_router
from app.routers import chat

# Configure logging baseline
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("carbon_ledger")

@asynccontextmanager
async def lifespan(app: FastAPI):
   # Startup Phase: Trigger pool initializations before accepting HTTP traffic
    await db_manager.connect()
    
    # ─── DATA RECOVERY ROUTINE ───
    logger.info("🔍 Running startup diagnostics and data recovery...")
    try:
        # Failsafe: Reset any jobs orphaned by a hard shutdown, crash, or quota lock
        # NOTE: If your db_manager uses SQLAlchemy, wrap this string in text() 
        # (e.g., await db_manager.execute(text("UPDATE tasks...")))
        await db_manager.execute(
            """
            UPDATE ingestion_tasks
            SET status = 'failed' 
            WHERE status IN ('processing', 'pending');
            """
        )
        logger.info("✅ Data recovery complete: Unstuck orphaned background worker tasks.")
    except Exception as e:
        logger.error(f"⚠️ Data recovery routine skipped or failed: {e}")
        logger.info("💡 (Ensure your database tables are migrated and 'db_manager.execute' matches your driver signatures)")

    yield
    
    # Shutdown Phase: Safe termination when the process receives a SIGTERM signal
    await db_manager.disconnect()

app = FastAPI(
    title="Carbon Ledger Intelligence Core",
    version="2.0.0",
    lifespan=lifespan
)

# Permit local React web client configurations
origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(compliance.router)

app.include_router(ledger.router)

app.include_router(documents.router)

app.include_router(endpoints.router)

app.include_router(analytics_router)

app.include_router(chat.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "cluster_routing": "active"}