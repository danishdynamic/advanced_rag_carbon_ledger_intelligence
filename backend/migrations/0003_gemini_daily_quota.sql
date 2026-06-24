CREATE TABLE IF NOT EXISTS gemini_daily_quota (
    usage_date DATE PRIMARY KEY DEFAULT CURRENT_DATE,
    request_count INT DEFAULT 0
);