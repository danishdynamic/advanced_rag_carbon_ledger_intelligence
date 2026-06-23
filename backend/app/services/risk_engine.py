from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

logger = logging.getLogger("carbon_ledger.services.risk_engine")

class ClimateRiskService:
    @classmethod
    def get_analytics(cls, db: Session) -> dict:
        """
        Computes aggregate green finance liabilities and system alerts
        by querying the climate risk tracking nodes.
        """
        try:
            query = text("""
                SELECT 
                    COALESCE(COUNT(*), 0) as total_facilities,
                    COALESCE(SUM(projected_tax_liability), 0.0) as total_exposure
                FROM climate_risk_assessments;
            """)
            result = db.execute(query).mappings().first()
            
            # 🛡️ ADD THIS GUARD CLAUSE RIGHT HERE
            if result is None:
                logger.warning("Database returned an empty result set. Falling back to zeros.")
                total_facilities = 0
                total_exposure = 0.0
            else:
                total_facilities = result["total_facilities"]
                total_exposure = float(result["total_exposure"])
            
            # 2. Compute deterministic analytics safely
            avg_liability = 0.0
            if total_facilities > 0:
                avg_liability = total_exposure / total_facilities
            
            # 3. Determine systemic security thresholds
            system_status = "stable"
            if total_exposure > 50000.0:
                system_status = "action_required"
                
            return {
                "metrics": {
                    "total_tracked_facilities": total_facilities,
                    "total_estimated_exposure": total_exposure,
                    "average_facility_liability": avg_liability
                },
                "system_status": system_status
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate climate risk indices: {str(e)}")
            # Fallback safeguard matrix to prevent downstream UI breaks
            return {
                "metrics": {
                    "total_tracked_facilities": 0,
                    "total_estimated_exposure": 0.0,
                    "average_facility_liability": 0.0
                },
                "system_status": "error"
            }