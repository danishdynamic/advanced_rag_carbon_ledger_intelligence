import logging
import asyncpg
from fastapi import HTTPException

logger = logging.getLogger("carbon_ledger.quota_manager")

DAILY_MAX_BUDGET = 450  # 20-50 request cushion below the hard 500 limit

async def check_and_increment_quota(db_conn: asyncpg.Connection) -> int:
    """
    Tracks and enforces a hard ceiling on daily API calls using an atomic upsert.
    """
    # 1. Fetch the raw value (Inferred as Unknown | None by Pylance)
    raw_result = await db_conn.fetchval(
        """
        INSERT INTO gemini_daily_quota (usage_date, request_count)
        VALUES (CURRENT_DATE, 1)
        ON CONFLICT (usage_date)
        DO UPDATE SET request_count = gemini_daily_quota.request_count + 1
        RETURNING request_count;
        """
    )
    
    # 2. Type Guard: Explicitly handle the 'None' edge case to clear the union type
    if raw_result is None:
        logger.error("Atomic quota upsert failed to return a tracking row.")
        raise HTTPException(
            status_code=500,
            detail="Internal database tracking error handling API allocation."
        )
    
    # 3. Explicitly parse to int (Pylance now guarantees this is strictly 'int')
    current_count = int(raw_result)
    
    # 4. Safe comparison without static analysis warnings
    if current_count > DAILY_MAX_BUDGET:
        raise HTTPException(
            status_code=429,
            detail=f"Daily LLM API allocation exhausted ({current_count}/{DAILY_MAX_BUDGET} used). Try again tomorrow."
        )
        
    return current_count