# PostgreSQL Integration with dev-nexus

## Overview

Pattern-miner now integrates with the existing PostgreSQL database used by dev-nexus, enabling:

- **Shared infrastructure**: One database for both services
- **Cross-service queries**: dev-nexus can query pattern analysis results
- **Persistent storage**: Analysis results survive service restarts
- **Data consistency**: Single source of truth for pattern data

## What Was Changed

### 1. Storage Layer (`pattern_miner/storage.py`)

- Added full PostgreSQL support using `asyncpg`
- Automatic fallback to in-memory storage if database unavailable
- Connection pooling for performance
- Auto-creates tables on startup

### 2. Configuration (`pattern_miner/config.py`)

Added database configuration parameters:
```python
database_url: Optional[str]  # Full connection string
db_host: Optional[str]       # Database host/socket
db_port: int                 # Database port (default: 5432)
db_name: Optional[str]       # Database name (default: devnexus)
db_user: Optional[str]       # Database user
db_password: Optional[str]   # Database password
use_database: bool           # Enable/disable database (default: False)
```

### 3. Database Schema (`database/schema.sql`)

Created `pattern_analyses` table:
- `analysis_id` (TEXT PK) - Unique identifier
- `repository` (TEXT) - Repository name
- `results` (JSONB) - Analysis results
- `created_at`, `updated_at` (TIMESTAMP)

Indexes:
- Repository lookups
- Time-based queries
- JSONB pattern searches

### 4. Terraform Configuration

Added database support:
- Environment variables for database connection
- Secret Manager integration for DB password
- Cloud SQL connection support
- Configurable via `terraform.tfvars`

### 5. Dependencies

Added to `requirements.txt`:
- `asyncpg==0.29.0` - PostgreSQL async driver

## Configuration Options

### Option 1: DATABASE_URL (Simplest)

```bash
export DATABASE_URL="postgresql://user:password@host:5432/devnexus"
export USE_DATABASE="true"
```

### Option 2: Individual Parameters

```bash
export USE_DATABASE="true"
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="devnexus"
export DB_USER="pattern_miner"
export DB_PASSWORD="your-password"
```

### Option 3: Cloud SQL Unix Socket (GCP)

```bash
export USE_DATABASE="true"
export DB_HOST="/cloudsql/project-id:us-central1:instance-name"
export DB_NAME="devnexus"
export DB_USER="pattern_miner"
# Password from Secret Manager
```

## Setup Instructions

### Local Development

1. **Get dev-nexus database credentials**:
   ```bash
   # Ask dev-nexus team or check their .env
   ```

2. **Create database user** (if needed):
   ```sql
   CREATE USER pattern_miner WITH PASSWORD 'your-password';
   GRANT CONNECT ON DATABASE devnexus TO pattern_miner;
   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pattern_miner;
   GRANT USAGE ON SCHEMA public TO pattern_miner;
   ```

3. **Set environment variables**:
   ```bash
   export DATABASE_URL="postgresql://pattern_miner:password@localhost:5432/devnexus"
   export USE_DATABASE="true"
   ```

4. **Run the service**:
   ```bash
   python -m uvicorn pattern_miner.a2a.skills.server:app --reload --port 8080
   ```

   The service will automatically:
   - Connect to PostgreSQL
   - Create tables if they don't exist
   - Start accepting requests

### GCP Deployment with Terraform

1. **Set database password in Secret Manager**:
   ```bash
   echo -n "your-db-password" | gcloud secrets create DB_PASSWORD --data-file=-
   ```

2. **Configure `terraform.tfvars`**:
   ```hcl
   use_database = true

   # For Cloud SQL with Unix socket
   db_host = "/cloudsql/project-id:us-central1:dev-nexus-db"
   db_name = "devnexus"
   db_user = "pattern-miner"
   db_password_secret = "DB_PASSWORD"
   ```

3. **Deploy**:
   ```bash
   terraform apply
   ```

### Using Existing Cloud SQL Instance

If dev-nexus already has a Cloud SQL instance:

1. **Get connection details**:
   ```bash
   gcloud sql instances describe INSTANCE_NAME --format="value(connectionName)"
   ```

2. **Create pattern-miner user**:
   ```bash
   gcloud sql users create pattern-miner \
     --instance=INSTANCE_NAME \
     --password=SECURE_PASSWORD
   ```

3. **Grant Cloud Run access** (Terraform does this automatically):
   ```bash
   gcloud projects add-iam-policy-binding PROJECT_ID \
     --member="serviceAccount:pattern-miner-sa@PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/cloudsql.client"
   ```

## Database Schema

### Table: pattern_analyses

```sql
CREATE TABLE pattern_analyses (
    analysis_id TEXT PRIMARY KEY,
    repository TEXT NOT NULL,
    results JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Example Data

```json
{
  "analysis_id": "analysis_20250101_001",
  "repository": "patelmm79/vllm-container-ngc",
  "results": {
    "patterns": [
      {
        "type": "deployment",
        "files": ["deploy-gcp.sh"],
        "similarity_score": 0.85
      }
    ],
    "extraction_opportunities": [
      {
        "pattern_type": "deployment",
        "similarity_score": 0.85,
        "suggested_library": "gcp-deployment-toolkit"
      }
    ],
    "files_analyzed": 10,
    "timestamp": "2025-01-01T12:00:00Z"
  }
}
```

## Querying from dev-nexus

Dev-nexus can now query pattern-miner data:

```python
# In dev-nexus Python code
import asyncpg

conn = await asyncpg.connect(DATABASE_URL)

# Get all analyses for a repository
analyses = await conn.fetch("""
    SELECT * FROM pattern_analyses
    WHERE repository = $1
    ORDER BY created_at DESC
""", "patelmm79/vllm-container-ngc")

# Find high-similarity patterns
patterns = await conn.fetch("""
    SELECT
        repository,
        jsonb_array_elements(results->'patterns')->>'type' as pattern_type,
        (jsonb_array_elements(results->'patterns')->>'similarity_score')::float as score
    FROM pattern_analyses
    WHERE (jsonb_array_elements(results->'patterns')->>'similarity_score')::float > 0.85
""")

await conn.close()
```

## Fallback Behavior

If database connection fails:
1. Service logs error
2. Automatically falls back to in-memory storage
3. Service continues to work (no downtime)
4. Returns `"storage_type": "in_memory"` in statistics

This ensures the service is resilient to database outages.

## Migration Path

If you have existing in-memory data:

1. **Export current data** (before enabling database):
   ```bash
   curl http://localhost:8080/api/statistics > current_data.json
   ```

2. **Enable database**:
   ```bash
   export USE_DATABASE="true"
   export DATABASE_URL="postgresql://..."
   ```

3. **Restart service** - tables created automatically

4. **Re-run analyses** - new results stored in database

## Monitoring

### Check Connection Status

```bash
# Via API
curl http://localhost:8080/health

# Response includes storage type
{
  "status": "healthy",
  "storage_type": "postgresql",  # or "in_memory"
  "skills_registered": 4
}
```

### Database Queries

```sql
-- Count analyses
SELECT COUNT(*) FROM pattern_analyses;

-- Recent analyses
SELECT repository, created_at
FROM pattern_analyses
ORDER BY created_at DESC
LIMIT 10;

-- Storage size
SELECT pg_size_pretty(pg_total_relation_size('pattern_analyses'));
```

## Performance Considerations

1. **Connection Pooling**:
   - Min: 2 connections
   - Max: 10 connections
   - Configurable in `storage.py`

2. **Indexes**:
   - GIN index on JSONB for fast pattern searches
   - B-tree indexes on repository and timestamp

3. **Query Optimization**:
   - Use JSONB operators for pattern filtering
   - Limit results to avoid large result sets
   - Use prepared statements (asyncpg does this automatically)

4. **Scaling**:
   - Cloud SQL can scale vertically (more CPU/memory)
   - Read replicas for heavy read workloads
   - Connection pooling prevents connection exhaustion

## Security

1. **Passwords in Secret Manager**:
   - Never commit passwords to code
   - Use GCP Secret Manager
   - Terraform automatically configures access

2. **IAM Authentication** (recommended):
   ```bash
   # Use Cloud SQL IAM auth instead of passwords
   gcloud sql users create pattern-miner-sa \
     --instance=INSTANCE \
     --type=CLOUD_IAM_SERVICE_ACCOUNT
   ```

3. **Network Security**:
   - Cloud SQL private IP
   - VPC peering with Cloud Run
   - SSL/TLS connections enforced

## Troubleshooting

### Connection Failures

```bash
# Check logs
gcloud run services logs read pattern-miner --region us-central1

# Look for:
# "Connected to PostgreSQL database: devnexus" ✅
# "Failed to connect to database" ❌
# "Falling back to in-memory storage" ⚠️
```

### Table Creation Issues

```bash
# Manually create tables
psql $DATABASE_URL -f database/schema.sql
```

### Permission Errors

```sql
-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE pattern_analyses TO pattern_miner;
GRANT USAGE ON SCHEMA public TO pattern_miner;
```

### Cloud SQL Connection Issues

```bash
# Test Cloud SQL connection
gcloud sql connect INSTANCE_NAME --user=pattern_miner

# Verify service account has cloudsql.client role
gcloud projects get-iam-policy PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.role:roles/cloudsql.client"
```

## Cost Impact

Using existing dev-nexus database has **minimal cost impact**:

- **Storage**: ~$0.17/GB/month (JSONB compresses well)
- **IOPS**: Included in Cloud SQL tier
- **Connections**: Shared pool (pattern-miner uses 2-10)

Estimated additional storage per month:
- 100 analyses × ~10KB each = 1MB = **$0.00017/month**

## Benefits

✅ **Persistent storage** - Results survive restarts
✅ **Cross-service queries** - dev-nexus can query pattern data
✅ **Reduced infrastructure** - One database instead of two
✅ **Data consistency** - Single source of truth
✅ **Automatic backups** - Cloud SQL handles backups
✅ **Scalability** - PostgreSQL scales well
✅ **SQL analytics** - Complex queries on pattern data

## Next Steps

1. Set up database connection
2. Run test analysis
3. Verify data in database
4. Configure dev-nexus to query pattern data
5. Set up monitoring/alerting
6. Document cross-service queries

See `database/README.md` for detailed database setup instructions.
