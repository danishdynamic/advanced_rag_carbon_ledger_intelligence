-- 🚀 Automatically grant replication access across the Docker network bridge
COPY (SELECT 1) TO PROGRAM 'echo "host replication all all trust" >> /var/lib/postgresql/data/pg_hba.conf';
SELECT pg_reload_conf();

-- Ensure the pgvector extension is activated if not already done
CREATE EXTENSION IF NOT EXISTS vector;

-- 📋 1. Create the ingestion_tasks table (MATCHED TO BACKEND ROUTER EXPECTATIONS)
CREATE TABLE IF NOT EXISTS ingestion_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL UNIQUE, -- 🎯 Added to match backend routers
    file_name VARCHAR(255) NOT NULL,      -- 🎯 Added to match backend routers
    status VARCHAR(50) NOT NULL DEFAULT 'pending', 
    total_chunks INTEGER DEFAULT 0,                 -- 🎯 Added for worker tracking
    error_message TEXT,                             -- 🎯 Added for worker error logging
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 📄 2. Create the compliance_documents table
CREATE TABLE IF NOT EXISTS compliance_documents (
    id SERIAL PRIMARY KEY,
    framework_name VARCHAR(255) NOT NULL,
    section_identifier VARCHAR(100),
    raw_text_chunk TEXT NOT NULL,
    metadata_tags JSONB DEFAULT '{}'::jsonb,
    embedding_vector VECTOR(3072), -- Matches Gemini 3.1 Flash-Lite , chunk_vector + meta_vector i.e 1536 * 2
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 🛠️ Safety Upgrades: Explicitly force types and drop indexing blockers
ALTER TABLE compliance_documents ALTER COLUMN embedding_vector TYPE VECTOR(3072);
DROP INDEX IF EXISTS compliance_documents_vector_idx;

-- 📈 Construct the fast HNSW index
CREATE INDEX IF NOT EXISTS compliance_documents_vector_idx 
ON compliance_documents USING hnsw (embedding_vector vector_cosine_ops);