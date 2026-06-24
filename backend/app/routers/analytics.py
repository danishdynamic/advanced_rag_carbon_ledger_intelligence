import logging
from fastapi import APIRouter, Depends
import asyncpg  # 🎯 Updated: Import asyncpg instead of sqlalchemy.orm
from app.database import get_read_db
from app.services.risk_engine import ClimateRiskService

logger = logging.getLogger("carbon_ledger.api.routers.analytics")

# 🎯 Clean, dedicated prefix and OpenAPI tag group
router = APIRouter(prefix="/api/analytics", tags=["Climate & Green Finance Analytics"])

@router.get("/climate-risk")
async def get_climate_risk_analytics(db_conn: asyncpg.Connection = Depends(get_read_db)):
    """
    🎯 UPDATED: Fetches real-time carbon tax liabilities, facility exposures, 
    and system alert statuses utilizing an async connection pool.
    """
    logger.info("Fetching green finance and climate risk calculations")
    # 🎯 Fixed: Passing the matching asyncpg Connection object with await
    return await ClimateRiskService.get_analytics(db_conn)