-- Pattern Miner Database Schema
-- This schema is designed to be compatible with dev-nexus PostgreSQL database
-- Table: pattern_analyses

CREATE TABLE IF NOT EXISTS pattern_analyses (
    analysis_id TEXT PRIMARY KEY,
    repository TEXT NOT NULL,
    results JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_analyses_repository
    ON pattern_analyses(repository);

CREATE INDEX IF NOT EXISTS idx_analyses_created_at
    ON pattern_analyses(created_at DESC);

-- GIN index for JSONB pattern searches
CREATE INDEX IF NOT EXISTS idx_analyses_patterns
    ON pattern_analyses USING GIN ((results->'patterns'));

-- Index for pattern type filtering
CREATE INDEX IF NOT EXISTS idx_analyses_pattern_types
    ON pattern_analyses USING GIN ((results->'patterns'));

-- Comments for documentation
COMMENT ON TABLE pattern_analyses IS 'Stores pattern analysis results from the pattern-miner service';
COMMENT ON COLUMN pattern_analyses.analysis_id IS 'Unique identifier for the analysis run';
COMMENT ON COLUMN pattern_analyses.repository IS 'GitHub repository in format owner/repo';
COMMENT ON COLUMN pattern_analyses.results IS 'JSONB containing patterns found, extraction opportunities, and metadata';
COMMENT ON COLUMN pattern_analyses.created_at IS 'Timestamp when analysis was first created';
COMMENT ON COLUMN pattern_analyses.updated_at IS 'Timestamp when analysis was last updated';

-- Example query to get recent analyses
-- SELECT * FROM pattern_analyses ORDER BY created_at DESC LIMIT 10;

-- Example query to find analyses for specific repository
-- SELECT * FROM pattern_analyses WHERE repository = 'patelmm79/vllm-container-ngc';

-- Example query to find analyses with specific pattern type
-- SELECT * FROM pattern_analyses WHERE results->'patterns' @> '[{"type": "deployment"}]'::jsonb;

-- Example query to get statistics
-- SELECT
--     COUNT(*) as total_analyses,
--     COUNT(DISTINCT repository) as unique_repositories,
--     jsonb_array_elements(results->'patterns')->>'type' as pattern_type
-- FROM pattern_analyses
-- GROUP BY pattern_type;
