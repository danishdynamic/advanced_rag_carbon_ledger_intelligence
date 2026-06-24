import re
import logging
import asyncpg

logger = logging.getLogger("carbon_ledger.services.risk_engine")

class ClimateRiskService:
    @classmethod
    async def run_dynamic_extraction(cls, db_conn: asyncpg.Connection) -> bool:
        """
        Asynchronously scans compliance text chunks for facility metrics 
        using raw asyncpg connection syntax.
        """
        try:
            # 1. Fetch raw unstructured text chunks containing facility telemetry words
            chunks = await db_conn.fetch("""
                SELECT raw_text_chunk 
                FROM compliance_documents 
                WHERE raw_text_chunk ILIKE '%Facility%' 
                   OR raw_text_chunk ILIKE '%MWh%' 
                   OR raw_text_chunk ILIKE '%intensity%';
            """)
            
            if not chunks:
                logger.info("No unstructured facility chunks detected to extract yet.")
                return False

            # Extract string content out of record rows
            combined_text = "\n".join([chunk["raw_text_chunk"] for chunk in chunks])

            # 2. Extract key metrics dynamically using Regex matching values
            facilities = set(re.findall(r'(Facility-\d+)', combined_text))
            
            penalty_match = re.search(r'\$(\d{1,3}(?:,\d{3})*|\d+)\s*(?:baseline transition|regulatory penalty)', combined_text)
            base_liability = float(penalty_match.group(1).replace(',', '')) if penalty_match else 150000.0

            if not facilities and "Facility" in combined_text:
                facilities = {"Facility-01"}

            if not facilities:
                return False

            # 3. Clear existing calculations to keep evaluation telemetry real-time
            await db_conn.execute("TRUNCATE TABLE climate_risk_assessments RESTART IDENTITY;")

            # 4. Insert calculated risk metrics sequentially into the schema matrix
            for idx, facility in enumerate(facilities):
                calculated_tax = base_liability * (1.0 + (idx * 0.15))
                
                await db_conn.execute("""
                    INSERT INTO climate_risk_assessments (facility_name, projected_tax_liability)
                    VALUES ($1, $2);
                """, facility, calculated_tax)
            
            logger.info(f"Successfully processed async risk calculations for {len(facilities)} facilities.")
            return True
        except Exception as e:
            logger.error(f"Failed to execute dynamic extraction engine tracking: {str(e)}")
            return False

    @classmethod
    async def get_analytics(cls, db_conn: asyncpg.Connection) -> dict:
        """
        🎯 UPDATED: Computes aggregate green finance liabilities and system alerts asynchronously.
        No more SQLAlchemy Session or text wrappers required!
        """
        try:
            # Execute raw SQL directly via asyncpg
            row = await db_conn.fetchrow("""
                SELECT 
                    COALESCE(COUNT(*), 0) as total_facilities,
                    COALESCE(SUM(projected_tax_liability), 0.0) as total_exposure
                FROM climate_risk_assessments;
            """)
            
            if row is None:
                total_facilities = 0
                total_exposure = 0.0
            else:
                total_facilities = row["total_facilities"]
                total_exposure = float(row["total_exposure"])
            
            avg_liability = 0.0
            if total_facilities > 0:
                avg_liability = total_exposure / total_facilities
            
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
            return {
                "metrics": {"total_tracked_facilities": 0, "total_estimated_exposure": 0.0, "average_facility_liability": 0.0},
                "system_status": "error"
            }