# Shared PostgreSQL Setup with dev-nexus

## Overview

Pattern-miner shares the same PostgreSQL VM instance deployed by dev-nexus. This provides:

- **Cost savings**: One PostgreSQL VM instead of two ($0-1/month total)
- **Shared knowledge base**: Both services can query each other's data
- **Simplified infrastructure**: Single database to manage and backup
- **Private VPC networking**: Secure internal-only database access

## Architecture

```
┌─────────────────────────────────────────────────┐
│              GCP Project                        │
│                                                 │
│  ┌──────────────┐      ┌──────────────┐       │
│  │  dev-nexus   │      │pattern-miner │       │
│  │  Cloud Run   │      │  Cloud Run   │       │
│  └──────┬───────┘      └──────┬───────┘       │
│         │                     │                │
│         │   VPC Connector     │                │
│         └─────────┬───────────┘                │
│                   │                            │
│         ┌─────────▼──────────┐                │
│         │  Private VPC       │                │
│         │  10.8.0.0/28       │                │
│         └─────────┬──────────┘                │
│                   │                            │
│         ┌─────────▼──────────┐                │
│         │   PostgreSQL VM    │                │
│         │   10.8.0.2:5432    │                │
│         │   e2-micro         │                │
│         │   + pgvector       │                │
│         └────────────────────┘                │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Prerequisites

1. **dev-nexus already deployed** with PostgreSQL VM
2. **VPC Connector** created by dev-nexus Terraform
3. **POSTGRES_PASSWORD** secret in Secret Manager
4. Access to dev-nexus database credentials

## Database Setup

### Option 1: Use Same Database User (Simplest)

Use the existing `devnexus` user that dev-nexus already uses:

```bash
# No setup needed - just use same credentials
DB_USER=devnexus
DB_PASSWORD=<from POSTGRES_PASSWORD secret>
```

**Pros**: No additional setup
**Cons**: Shared permissions with dev-nexus

### Option 2: Create Dedicated User (Recommended)

Create a separate `pattern_miner` user with limited permissions:

```bash
# SSH into PostgreSQL VM
gcloud compute ssh devnexus-postgres --zone=us-central1-a

# Connect to PostgreSQL
sudo -u postgres psql devnexus

# Create user
CREATE USER pattern_miner WITH PASSWORD 'secure-password-here';

# Grant permissions
GRANT CONNECT ON DATABASE devnexus TO pattern_miner;
GRANT USAGE ON SCHEMA public TO pattern_miner;

# Grant access to existing tables (if any)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO pattern_miner;

# Grant access to future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO pattern_miner;

# Grant sequence access (for auto-increment IDs)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO pattern_miner;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO pattern_miner;

# Exit
\q
exit
```

Then create a separate secret:
```bash
echo -n "secure-password-here" | gcloud secrets create PATTERN_MINER_DB_PASSWORD --data-file=-
```

## Terraform Configuration

### 1. Verify VPC Connector Exists

```bash
# Check if dev-nexus VPC connector exists
gcloud compute networks vpc-access connectors list --region=us-central1

# You should see: devnexus-connector
```

### 2. Configure terraform.tfvars

```hcl
# Database Configuration (shared with dev-nexus)
use_database = true

# PostgreSQL VM internal IP (from dev-nexus deployment)
db_host = "10.8.0.2"  # Check with: gcloud compute instances describe devnexus-postgres --zone=us-central1-a --format="value(networkInterfaces[0].networkIP)"
db_port = 5432
db_name = "devnexus"

# Option 1: Use same user as dev-nexus
db_user = "devnexus"
db_password_secret = "POSTGRES_PASSWORD"

# Option 2: Use dedicated pattern_miner user
# db_user = "pattern_miner"
# db_password_secret = "PATTERN_MINER_DB_PASSWORD"

# VPC Connector (shared with dev-nexus)
vpc_connector = "devnexus-connector"
vpc_connector_region = "us-central1"
```

### 3. Deploy

```bash
cd terraform/

terraform init
terraform plan
terraform apply
```

Terraform will:
- ✅ Reuse existing VPC connector
- ✅ Reference existing POSTGRES_PASSWORD secret
- ✅ Configure Cloud Run to connect via private VPC
- ✅ Grant pattern-miner service account access to secrets

## Database Schema

Pattern-miner creates its own table in the shared database:

```sql
CREATE TABLE pattern_analyses (
    analysis_id TEXT PRIMARY KEY,
    repository TEXT NOT NULL,
    results JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

This table is **separate** from dev-nexus tables, but both services can query each other's data if needed.

### dev-nexus Tables (Reference)

```
repositories
patterns (with vector embeddings)
technical_decisions
reusable_components
dependencies
deployment_scripts
lessons_learned
analysis_history
```

## Local Development

To test locally, create an SSH tunnel to the PostgreSQL VM:

```bash
# Open SSH tunnel
gcloud compute ssh devnexus-postgres \
  --zone=us-central1-a \
  -- -L 5432:localhost:5432 -N

# In another terminal, set environment variables
export USE_DATABASE=true
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=devnexus
export DB_USER=devnexus
export DB_PASSWORD="your-password"

# Run pattern-miner
python -m uvicorn pattern_miner.a2a.skills.server:app --reload --port 8080
```

## Cross-Service Queries

### Pattern-miner Querying dev-nexus Data

```python
# In pattern_miner code
async with self._pool.acquire() as conn:
    # Get all patterns from dev-nexus
    nexus_patterns = await conn.fetch("""
        SELECT name, description, pattern_type
        FROM patterns
        WHERE similarity > 0.8
        ORDER BY created_at DESC
    """)

    # Find similar patterns using vector search
    similar = await conn.fetch("""
        SELECT name, embedding <=> $1::vector as distance
        FROM patterns
        ORDER BY distance
        LIMIT 5
    """, query_embedding)
```

### dev-nexus Querying Pattern-miner Data

```python
# In dev-nexus code
async with self.db.acquire() as conn:
    # Get recent pattern analyses
    analyses = await conn.fetch("""
        SELECT repository, results
        FROM pattern_analyses
        WHERE created_at > NOW() - INTERVAL '7 days'
    """)

    # Find high-similarity patterns
    high_similarity = await conn.fetch("""
        SELECT
            repository,
            jsonb_array_elements(results->'patterns')->>'type' as pattern_type,
            (jsonb_array_elements(results->'patterns')->>'similarity_score')::float as score
        FROM pattern_analyses
        WHERE (jsonb_array_elements(results->'patterns')->>'similarity_score')::float > 0.85
    """)
```

## Monitoring

### Check Connection Status

```bash
# SSH into PostgreSQL VM
gcloud compute ssh devnexus-postgres --zone=us-central1-a

# Check active connections
sudo -u postgres psql -c "
SELECT
    datname,
    usename,
    application_name,
    client_addr,
    state,
    query_start
FROM pg_stat_activity
WHERE datname = 'devnexus'
ORDER BY query_start DESC;
"

# You should see connections from both dev-nexus and pattern-miner
```

### Storage Usage

```bash
# Check database size
sudo -u postgres psql devnexus -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

### Cloud Monitoring

The existing dev-nexus monitoring dashboard tracks:
- CPU usage
- Memory usage
- Disk I/O
- Query performance
- Connection counts

Pattern-miner connections will show up automatically.

## Backup and Recovery

Pattern-miner data is automatically backed up with dev-nexus:

- **Automated backups**: Daily at 2 AM UTC
- **Storage location**: Cloud Storage bucket (dev-nexus-backups)
- **Retention**: 30 days
- **Backup includes**: All tables including pattern_analyses

### Manual Backup

```bash
# SSH into VM
gcloud compute ssh devnexus-postgres --zone=us-central1-a

# Backup pattern_analyses table
sudo -u postgres pg_dump devnexus -t pattern_analyses > pattern_analyses_backup.sql

# Copy to Cloud Storage
gsutil cp pattern_analyses_backup.sql gs://your-bucket/backups/
```

### Restore

```bash
# Restore from backup
sudo -u postgres psql devnexus < pattern_analyses_backup.sql
```

## Security

### Network Security

- ✅ PostgreSQL VM has **no public IP**
- ✅ Only accessible via private VPC (10.8.0.0/28)
- ✅ Cloud Run connects via VPC Connector
- ✅ Firewall rules limit access to VPC only

### Secrets Management

- ✅ Database password stored in Secret Manager
- ✅ Cloud Run pulls from Secret Manager at runtime
- ✅ Never hardcoded in code or Terraform
- ✅ Automatic rotation supported

### Access Control

```bash
# Grant pattern-miner service account access to database secret
gcloud secrets add-iam-policy-binding POSTGRES_PASSWORD \
  --member="serviceAccount:pattern-miner-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Troubleshooting

### Connection Issues

```bash
# 1. Verify VPC connector exists
gcloud compute networks vpc-access connectors describe devnexus-connector \
  --region=us-central1

# 2. Check PostgreSQL VM is running
gcloud compute instances describe devnexus-postgres \
  --zone=us-central1-a \
  --format="value(status)"

# 3. Verify internal IP
gcloud compute instances describe devnexus-postgres \
  --zone=us-central1-a \
  --format="value(networkInterfaces[0].networkIP)"

# 4. Check Cloud Run logs
gcloud run services logs read pattern-miner --region=us-central1 --limit=50

# Look for:
# ✅ "Connected to PostgreSQL database: devnexus"
# ❌ "Failed to connect to database"
```

### Permission Errors

```sql
-- SSH into PostgreSQL VM
gcloud compute ssh devnexus-postgres --zone=us-central1-a
sudo -u postgres psql devnexus

-- Check user permissions
\du pattern_miner

-- Grant missing permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON pattern_analyses TO pattern_miner;
```

### Table Not Found

The service automatically creates tables on startup. If tables aren't created:

```bash
# Manually run schema
gcloud compute ssh devnexus-postgres --zone=us-central1-a
sudo -u postgres psql devnexus < /path/to/schema.sql
```

## Cost Breakdown

Using shared PostgreSQL VM:

| Component | Cost |
|-----------|------|
| PostgreSQL e2-micro VM | $0 (free tier) |
| 30GB Persistent Disk | $0.60/month |
| VPC Connector | $0.10-0.30/month |
| Cloud Storage Backups | $0.60/month |
| **Total** | **~$1.30/month** |

**Compared to separate Cloud SQL**: Would cost $7-10/month

**Savings**: ~$70-100/year by sharing PostgreSQL VM

## Scaling Considerations

### Current Capacity (e2-micro)

- **Suitable for**: Development, testing, small production
- **Connections**: 10-20 concurrent (dev-nexus + pattern-miner)
- **Storage**: 30GB (expandable)

### When to Upgrade

Upgrade to **e2-small** ($20/month) if:
- Connection count > 20
- CPU usage consistently > 80%
- Query response time > 500ms
- Storage > 25GB

Upgrade to **Cloud SQL** if:
- Need high availability (99.95% SLA)
- Need read replicas
- Need automatic failover
- Multiple regions

## Migration to Cloud SQL (Future)

If you later decide to move to Cloud SQL:

1. **Export data**:
   ```bash
   pg_dump devnexus > backup.sql
   ```

2. **Create Cloud SQL instance**:
   ```bash
   gcloud sql instances create devnexus-cloudsql \
     --database-version=POSTGRES_15 \
     --tier=db-f1-micro \
     --region=us-central1
   ```

3. **Import data**:
   ```bash
   gcloud sql import sql devnexus-cloudsql gs://bucket/backup.sql
   ```

4. **Update Terraform** to use Cloud SQL connection

## Summary

✅ **Shared PostgreSQL VM** with dev-nexus
✅ **Private VPC networking** for security
✅ **Cost-effective**: ~$1.30/month total
✅ **Automatic backups** included
✅ **Cross-service queries** enabled
✅ **Separate users** for better isolation (optional)

Pattern-miner integrates seamlessly with dev-nexus's existing PostgreSQL infrastructure, providing persistent storage without additional infrastructure costs.
