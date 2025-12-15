# Pattern Miner Database Setup

## Overview

Pattern Miner uses the same PostgreSQL database as dev-nexus for storing pattern analysis results. This allows both services to share data and enables cross-service queries.

## Database Schema

The pattern-miner service creates one table:

### `pattern_analyses`

Stores results from pattern analysis runs.

| Column | Type | Description |
|--------|------|-------------|
| `analysis_id` | TEXT (PK) | Unique identifier for the analysis |
| `repository` | TEXT | GitHub repository (owner/repo) |
| `results` | JSONB | Analysis results with patterns found |
| `created_at` | TIMESTAMP | When analysis was created |
| `updated_at` | TIMESTAMP | When analysis was last updated |

**Indexes:**
- `idx_analyses_repository` - Fast lookups by repository
- `idx_analyses_created_at` - Ordered by time
- `idx_analyses_patterns` - GIN index for JSONB pattern searches

## Setup Options

### Option 1: Use Existing dev-nexus Database (Recommended)

If you already have dev-nexus running with PostgreSQL:

```bash
# Get database connection info from dev-nexus
# Use the same DATABASE_URL or connection parameters

export DATABASE_URL="postgresql://user:password@host:5432/devnexus"
# OR
export DB_HOST="your-db-host"
export DB_PORT="5432"
export DB_NAME="devnexus"
export DB_USER="your-db-user"
export DB_PASSWORD="your-db-password"
export USE_DATABASE="true"
```

The pattern-miner service will automatically create its tables when it starts.

### Option 2: Manual Schema Setup

If you want to create the schema manually:

```bash
# Connect to your PostgreSQL database
psql $DATABASE_URL

# Run the schema file
\i database/schema.sql
```

### Option 3: Cloud SQL (GCP)

For production deployments on GCP:

```bash
# Create Cloud SQL instance (if not exists)
gcloud sql instances create dev-nexus-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database
gcloud sql databases create devnexus --instance=dev-nexus-db

# Get connection name
gcloud sql instances describe dev-nexus-db --format="value(connectionName)"
# Output: project-id:us-central1:dev-nexus-db
```

## Configuration

### Environment Variables

```bash
# Option 1: Use DATABASE_URL (easiest)
export DATABASE_URL="postgresql://user:password@host:5432/devnexus"
export USE_DATABASE="true"

# Option 2: Use individual parameters
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="devnexus"
export DB_USER="postgres"
export DB_PASSWORD="your-password"
export USE_DATABASE="true"
```

### Terraform Variables

Add to your `terraform.tfvars`:

```hcl
# Database configuration
use_database = true
database_url = "postgresql://user:password@host:5432/devnexus"

# Or use Cloud SQL with Unix socket
db_host = "/cloudsql/project-id:us-central1:dev-nexus-db"
db_name = "devnexus"
db_user = "pattern-miner"
```

## Security Best Practices

### Cloud SQL IAM Authentication (Recommended)

```bash
# Create a service account for pattern-miner
gcloud iam service-accounts create pattern-miner-db \
  --display-name="Pattern Miner DB Access"

# Grant Cloud SQL Client role
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:pattern-miner-db@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

# Grant database user permissions
gcloud sql users create pattern-miner-sa \
  --instance=dev-nexus-db \
  --type=CLOUD_IAM_SERVICE_ACCOUNT
```

### Secrets Management

Store database credentials in GCP Secret Manager:

```bash
# Create secret for database password
echo -n "your-db-password" | gcloud secrets create DB_PASSWORD --data-file=-

# Grant pattern-miner access
gcloud secrets add-iam-policy-binding DB_PASSWORD \
  --member="serviceAccount:pattern-miner-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Querying Data

### Example Queries

```sql
-- Get all analyses for a repository
SELECT * FROM pattern_analyses
WHERE repository = 'patelmm79/vllm-container-ngc'
ORDER BY created_at DESC;

-- Find analyses with deployment patterns
SELECT
  analysis_id,
  repository,
  results->'patterns' as patterns
FROM pattern_analyses
WHERE results->'patterns' @> '[{"type": "deployment"}]'::jsonb;

-- Get statistics by repository
SELECT
  repository,
  COUNT(*) as analysis_count,
  MAX(created_at) as last_analysis
FROM pattern_analyses
GROUP BY repository
ORDER BY analysis_count DESC;

-- Find high-similarity patterns
SELECT
  analysis_id,
  repository,
  jsonb_array_elements(results->'patterns')->>'type' as pattern_type,
  (jsonb_array_elements(results->'patterns')->>'similarity_score')::float as similarity
FROM pattern_analyses
WHERE (jsonb_array_elements(results->'patterns')->>'similarity_score')::float > 0.85;
```

### Python Example

```python
import asyncpg

# Connect to database
conn = await asyncpg.connect(
    host="localhost",
    port=5432,
    database="devnexus",
    user="postgres",
    password="password"
)

# Query analyses
rows = await conn.fetch("""
    SELECT analysis_id, repository, results
    FROM pattern_analyses
    WHERE repository = $1
    ORDER BY created_at DESC
    LIMIT 10
""", "patelmm79/vllm-container-ngc")

for row in rows:
    print(f"Analysis: {row['analysis_id']}")
    print(f"Repository: {row['repository']}")
    print(f"Patterns: {row['results']['patterns']}")

await conn.close()
```

## Backup and Restore

### Cloud SQL Backups

```bash
# Create on-demand backup
gcloud sql backups create --instance=dev-nexus-db

# List backups
gcloud sql backups list --instance=dev-nexus-db

# Restore from backup
gcloud sql backups restore BACKUP_ID --backup-instance=dev-nexus-db
```

### Manual Export

```bash
# Export pattern_analyses table
pg_dump -h localhost -U postgres -d devnexus -t pattern_analyses > pattern_analyses_backup.sql

# Restore
psql -h localhost -U postgres -d devnexus < pattern_analyses_backup.sql
```

## Monitoring

### Check Connection Status

```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity WHERE datname = 'devnexus';

-- Table statistics
SELECT
  schemaname,
  tablename,
  n_live_tup as row_count,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size
FROM pg_stat_user_tables
WHERE tablename = 'pattern_analyses';
```

### CloudWatch/Cloud Monitoring

Set up alerts for:
- Connection pool exhaustion
- Slow queries (> 1 second)
- Disk usage > 80%
- Failed connection attempts

## Troubleshooting

### Connection Issues

```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check if table exists
psql $DATABASE_URL -c "\dt pattern_analyses"

# Check logs
gcloud sql operations list --instance=dev-nexus-db
```

### Permission Issues

```sql
-- Grant permissions to pattern-miner user
GRANT SELECT, INSERT, UPDATE, DELETE ON pattern_analyses TO pattern_miner;
GRANT USAGE ON SCHEMA public TO pattern_miner;
```

### Performance Issues

```sql
-- Analyze table statistics
ANALYZE pattern_analyses;

-- Check index usage
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan as index_scans
FROM pg_stat_user_indexes
WHERE tablename = 'pattern_analyses';

-- Vacuum if needed
VACUUM ANALYZE pattern_analyses;
```

## Migration from In-Memory Storage

If you're migrating from in-memory to PostgreSQL:

1. Set `USE_DATABASE=false` initially
2. Run analysis to populate in-memory storage
3. Export results via API
4. Set `USE_DATABASE=true` and restart
5. Import results via API

## Integration with dev-nexus

The shared database enables:

1. **Cross-service queries**: dev-nexus can query pattern analysis results
2. **Unified knowledge base**: Both services contribute to same data store
3. **Reduced infrastructure**: One database instead of two
4. **Data consistency**: Single source of truth

Example dev-nexus query:
```python
# In dev-nexus, query pattern-miner results
patterns = await db.fetch("""
    SELECT * FROM pattern_analyses
    WHERE repository = $1
    AND results->'patterns' @> $2::jsonb
""", repo_name, json.dumps([{"type": "deployment"}]))
```

## Resources

- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
- [PostgreSQL JSONB Operators](https://www.postgresql.org/docs/current/functions-json.html)
- [GCP Cloud SQL Best Practices](https://cloud.google.com/sql/docs/postgres/best-practices)
