import logging
from fastapi import APIRouter, Depends, HTTPException
import asyncpg
from pydantic import BaseModel
from app.database import get_read_db, get_write_db

logger = logging.getLogger("carbon_ledger.api.endpoints")
router = APIRouter(prefix="/api/system", tags=["System Diagnostics & Metrics"])

# --- Pydantic Data Structures ---

class SystemHealthResponse(BaseModel):
    status: str
    primary_database: str
    replica_database: str

class DashboardStatsResponse(BaseModel):
    total_indexed_chunks: int
    tasks_pending: int
    tasks_processing: int
    tasks_completed: int
    tasks_failed: int

# --- Endpoints ---

@router.get("/health", response_model=SystemHealthResponse)
async def check_system_health(
    write_db: asyncpg.Connection = Depends(get_write_db),
    read_db: asyncpg.Connection = Depends(get_read_db)
):
    """Verifies operational responsiveness for backend database clusters."""
    try:
        # Ping the write instance
        await write_db.execute("SELECT 1;")
        primary_status = "connected"
    except Exception as e:
        logger.error(f"Primary database health check failed: {str(e)}")
        primary_status = "disconnected"

    try:
        # Ping the read instance
        await read_db.execute("SELECT 1;")
        replica_status = "connected"
    except Exception as e:
        logger.error(f"Replica database health check failed: {str(e)}")
        replica_status = "disconnected"

    if primary_status == "disconnected" or replica_status == "disconnected":
        raise HTTPException(status_code=503, detail="One or more database clusters are unreachable.")

    return SystemHealthResponse(
        status="healthy",
        primary_database=primary_status,
        replica_database=replica_status
    )


@router.get("/stats", response_model=DashboardStatsResponse)
async def fetch_dashboard_metrics(
    read_db: asyncpg.Connection = Depends(get_read_db)
):
    """Aggregates high-level inventory metrics for the frontend control panel."""
    try:
        # 1. Fetch total chunk records stored inside pgvector via the read replica
        total_chunks = await read_db.fetchval("SELECT COUNT(*) FROM compliance_documents;")
        
        # 2. Fetch breakdown of background processing tasks grouped by state
        task_rows = await read_db.fetch(
            "SELECT status, COUNT(*) as count FROM ingestion_tasks GROUP BY status;"
        )
        
        # Map out database states to structural variables cleanly
        stats_map = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
        for row in task_rows:
            status_type = row["status"].lower()
            if status_type in stats_map:
                stats_map[status_type] = row["count"]

        return DashboardStatsResponse(
            total_indexed_chunks=total_chunks or 0,
            tasks_pending=stats_map["pending"],
            tasks_processing=stats_map["processing"],
            tasks_completed=stats_map["completed"],
            tasks_failed=stats_map["failed"]
        )
    except Exception as e:
        logger.error(f"Failed to gather system-wide dashboard matrix details: {str(e)}")
        raise HTTPException(status_code=500, detail="Database metric extraction execution failure.")
    