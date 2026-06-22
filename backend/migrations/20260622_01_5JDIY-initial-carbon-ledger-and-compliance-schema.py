from yoyo import step

__depends__ = {}

steps = [
    # Step 1: Activate the pgvector extension on the database instance
    step(
        "CREATE EXTENSION IF NOT EXISTS vector;",
        "DROP EXTENSION IF EXISTS vector;"
    ),
    
    # Step 2: Create the Corporate Emissions Audit Log (Scope 1, 2, 3 Tracking)
    step(
        """
        CREATE TABLE emissions_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id VARCHAR(100) NOT NULL,
            facility_name VARCHAR(100) NOT NULL,
            scope_type INT NOT NULL CHECK (scope_type IN (1, 2, 3)),
            metric_tons_co2e NUMERIC(12, 4) NOT NULL,
            activity_data JSONB NOT NULL, -- Holds raw tracking variables like gas metrics or MWh values
            recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """,
        "DROP TABLE emissions_logs;"
    ),

    # Step 3: Create the Carbon Credit Registry Asset Table
    step(
        """
        CREATE TABLE carbon_credits (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            serial_number VARCHAR(150) UNIQUE NOT NULL,
            project_name TEXT NOT NULL,
            registry_provider VARCHAR(50) NOT NULL, -- e.g., 'Verra', 'Gold Standard'
            vintage_year INT NOT NULL,
            volume_tco2e NUMERIC(12, 4) NOT NULL,
            current_status VARCHAR(30) DEFAULT 'Available' CHECK (current_status IN ('Available', 'Pending', 'Retired')),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """,
        "DROP TABLE carbon_credits;"
    ),

    # Step 4: Create the Unstructured Regulatory Framework Table for RAG
    step(
        """
        CREATE TABLE compliance_documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            framework_name VARCHAR(100) NOT NULL, -- e.g., 'EU CSRD', 'IFRS S2'
            section_identifier VARCHAR(100) NOT NULL,
            raw_text_chunk TEXT NOT NULL,
            metadata_tags JSONB NOT NULL DEFAULT '{}'::jsonb,
            embedding_vector vector(1536) NOT NULL -- Configured for standard Gemini/OpenAI embedding lengths
        );
        """,
        "DROP TABLE compliance_documents;"
    )
]