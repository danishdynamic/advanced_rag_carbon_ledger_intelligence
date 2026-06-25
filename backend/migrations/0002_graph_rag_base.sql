-- Core Entity Store (The Vertices of your Knowledge Graph)
CREATE TABLE IF NOT EXISTS graph_entities (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_name VARCHAR(255) NOT NULL UNIQUE,
    entity_type VARCHAR(100) NOT NULL, -- e.g., 'FRAMEWORK', 'FACILITY', 'METRIC'
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Relationship Edge Matrix (The Connections connecting your documents)
CREATE TABLE IF NOT EXISTS graph_relationships (
    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID REFERENCES graph_entities(entity_id) ON DELETE CASCADE,
    target_entity_id UUID REFERENCES graph_entities(entity_id) ON DELETE CASCADE,
    predicate VARCHAR(150) NOT NULL, -- e.g., 'GOVERNS', 'EMITS', 'VIOLATES'
    weight NUMERIC(3,2) DEFAULT 1.00,
    context_summary TEXT, -- Stores the raw excerpt confirming this link
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index optimizations for lightning fast join traversals
CREATE INDEX IF NOT EXISTS idx_relationship_source ON graph_relationships(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationship_target ON graph_relationships(target_entity_id);