-- backend/migrations/0002_green_finance_risk.sql

CREATE TABLE IF NOT EXISTS climate_risk_assessments (
    assessment_id UUID PRIMARY KEY,
    facility_name VARCHAR(255) NOT NULL,
    projected_tax_liability NUMERIC(15, 2) NOT NULL,
    risk_level VARCHAR(50) NOT NULL DEFAULT 'low',
    scenario_type VARCHAR(100) NOT NULL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS green_finance_instruments (
    instrument_id UUID PRIMARY KEY,
    asset_name VARCHAR(255) NOT NULL,
    instrument_type VARCHAR(100) NOT NULL, -- 'Green Bond', 'SLL'
    allocated_capital NUMERIC(15, 2) NOT NULL,
    sustainability_discount NUMERIC(4, 2) DEFAULT 0.00, -- Interest rate deduction basis
    status VARCHAR(50) DEFAULT 'active'
);