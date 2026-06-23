import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import asyncpg
from app.database import get_write_db

logger = logging.getLogger("carbon_ledger.routers.ledger")
router = APIRouter(prefix="/api/ledger", tags=["Carbon Ledger Core"])

class EmissionLogCreate(BaseModel):
    company_id: str = Field(
        default=..., 
        examples=["COMP-99"]
    )
    facility_name: str = Field(
        default=..., 
        examples=["Rotterdam Refinery alpha"]
    )
    scope_type: int = Field(
        default=...,
        description="Must be 1, 2, or 3", 
        ge=1, 
        le=3
    )
    metric_tons_co2e: float = Field(
        default=...,
        ge=0.0
    )
    activity_data: dict = Field(
        default_factory=dict, 
        examples=[{"gas_mwh": 1250.5}]
    )

@router.post("/log", status_code=201)
async def create_emissions_entry(
    payload: EmissionLogCreate,
    db_conn: asyncpg.Connection = Depends(get_write_db)
):
    """Logs a transactional audit record into the Primary read-write database pool."""
    import json
    sql = """
        INSERT INTO emissions_logs (company_id, facility_name, scope_type, metric_tons_co2e, activity_data)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        RETURNING id, recorded_at;
    """
    try:
        record = await db_conn.fetchrow(
            sql, 
            payload.company_id, 
            payload.facility_name, 
            payload.scope_type, 
            payload.metric_tons_co2e, 
            json.dumps(payload.activity_data)
        )
        if not record:
            raise HTTPException(status_code=500, detail="Failed to capture ledger receipt.")
            
        return {
            "status": "committed",
            "log_id": record["id"],
            "timestamp": record["recorded_at"]
        }
    except Exception as e:
        logger.error(f"Ledger commitment failure: {str(e)}")
        raise HTTPException(status_code=500, detail="Database write transaction aborted.")