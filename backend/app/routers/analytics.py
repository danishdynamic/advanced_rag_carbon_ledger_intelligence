
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_read_db
from app.services.risk_engine import ClimateRiskService

logger = logging.getLogger("carbon_ledger.api.routers.analytics")

# 🎯 Clean, dedicated prefix and OpenAPI tag group
router = APIRouter(prefix="/api/analytics", tags=["Climate & Green Finance Analytics"])

@router.get("/climate-risk")
def get_climate_risk_analytics(db: Session = Depends(get_read_db)):
    """
    Fetches real-time carbon tax liabilities, facility exposures, and system alert statuses.
    """
    logger.info("Fetching green finance and climate risk calculations")
    return ClimateRiskService.get_analytics(db)