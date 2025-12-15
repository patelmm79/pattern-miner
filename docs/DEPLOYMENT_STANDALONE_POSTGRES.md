# Pattern Miner - Standalone PostgreSQL VM Deployment

## Overview

This guide covers deploying pattern-miner with its **own dedicated PostgreSQL VM**, following the same architecture pattern as dev-nexus:

- ✅ **PostgreSQL 15 on GCP Compute Engine** (e2-micro, free tier eligible)
- ✅ **Private VPC networking** (no public IP, secure)
- ✅ **VPC Connector** for Cloud Run → PostgreSQL communication
- ✅ **Automated daily backups** to Cloud Storage
- ✅ **Optional pgvector** for similarity search
- ✅ **Cloud Monitoring** integration

## Architecture

```
┌────────────────────────────────────────────┐
│          Pattern Miner Infrastructure       │
│                                            │
│  ┌──────────────┐                         │
│  │pattern-miner │                         │
│  │  Cloud Run   │                         │
│  └──────┬───────┘                         │
│         │                                  │
│         │ VPC Connector                    │
│         └────────┬────────                 │
│                  │                         │
│         ┌────────▼────────┐               │
│         │  Private VPC    │               │
│         │  10.8.0.0/28    │               │
│         └────────┬────────┘               │
│                  │                         │
│         ┌────────▼────────┐               │
│         │  PostgreSQL VM  │               │
│         │  e2-micro       │               │
│         │  30GB disk      │               │
│         │  PostgreSQL 15  │               │
│         └─────────────────┘               │
│                  │                         │
│         ┌────────▼────────┐               │
│         │ Cloud Storage   │               │
│         │ Daily Backups   │               │
│         └─────────────────┘               │
│                                            │
└────────────────────────────────────────────┘
```

## Cost Estimation

| Component | Cost |
|-----------|------|
| PostgreSQL e2-micro VM | **$0/month** (free tier) |
| 30GB Standard Persistent Disk | **$0.60/month** |
| VPC Connector (2 instances) | **$0.15/month** |
| Cloud Storage backups | **$0.60/month** |
| Cloud Run (pattern-miner) | **$0-5/month** (usage-based) |
| **Total** | **~$1.35-6/month** |

**vs Cloud SQL**: Saves ~$70-100/year

## Prerequisites

1. **GCP Project** with billing enabled
2. **Terraform** installed (>= 1.0)
3. **gcloud CLI** authenticated
4. **Docker** for building images

## Quick Start

### 1. Build and Push Docker Image

```bash
export PROJECT_ID="your-gcp-project-id"

# Build
docker build -t gcr.io/${PROJECT_ID}/pattern-miner:latest .

# Configure Docker
gcloud auth configure-docker

# Push
docker push gcr.io/${PROJECT_ID}/pattern-miner:latest
```

### 2. Configure Terraform

```bash
cd terraform/

# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit configuration
nano terraform.tfvars
```

**Required settings**:
```hcl
# Basic
project_id = "your-gcp-project-id"
container_image = "gcr.io/your-gcp-project-id/pattern-miner:latest"

# PostgreSQL VM
create_postgres_vm = true
postgres_vm_password = "your-secure-password-here"  # Will be stored in Secret Manager
db_name = "pattern_miner"
db_user = "pattern_miner"

# VPC
create_vpc = true
vpc_cidr_range = "10.8.0.0/28"
```

### 3. Create Secrets

```bash
# GitHub token (for pattern-miner)
echo -n "ghp_your_token" | gcloud secrets create GITHUB_TOKEN --data-file=-

# Anthropic API key
echo -n "sk-ant-your_key" | gcloud secrets create ANTHROPIC_API_KEY --data-file=-

# PostgreSQL password (matches postgres_vm_password in terraform.tfvars)
echo -n "your-secure-password-here" | gcloud secrets create PATTERN_MINER_DB_PASSWORD --data-file=-
```

### 4. Deploy

```bash
terraform init
terraform plan  # Review what will be created
terraform apply  # Type 'yes' to confirm
```

**Deployment takes ~10-15 minutes** to:
- Create VPC network and subnet
- Create PostgreSQL VM and install PostgreSQL
- Create VPC Connector
- Create Cloud Storage bucket for backups
- Deploy Cloud Run service
- Configure all IAM permissions

### 5. Verify Deployment

```bash
# Get service URL
SERVICE_URL=$(terraform output -raw service_url)

# Health check
curl $SERVICE_URL/health

# Expected response:
# {
#   "status": "healthy",
#   "service": "pattern-miner",
#   "version": "2.0.0",
#   "storage_type": "postgresql",  # ← Should be postgresql!
#   "skills_registered": 4
# }

# View configuration
curl $SERVICE_URL/.well-known/agent.json

# Test A2A endpoint
curl -X POST $SERVICE_URL/a2a/execute \
  -H "Content-Type: application/json" \
  -d '{
    "skill_id": "analyze_repository",
    "input": {
      "repository": "patelmm79/vllm-container-ngc",
      "focus_areas": ["deployment"]
    }
  }'
```

## What Gets Created

### Infrastructure Resources (20+)

1. **VPC Network**: `pattern-miner-vpc`
2. **Subnet**: `pattern-miner-subnet` (10.8.0.0/28)
3. **Firewall Rules**:
   - Allow PostgreSQL (5432) from VPC Connector
   - Allow SSH (22) for maintenance
4. **Compute Engine VM**: `pattern-miner-postgres`
   - Machine type: e2-micro (free tier)
   - Boot disk: 30GB Debian 11
   - Internal IP only (no public IP)
   - PostgreSQL 15 + auto-configured
5. **VPC Connector**: `pattern-miner-connector`
   - Links Cloud Run to private VPC
   - 2-3 e2-micro instances
6. **Cloud Storage Bucket**: `PROJECT_ID-pattern-miner-postgres-backups`
   - Automated daily backups
   - 30-day retention
   - Versioning enabled
7. **Service Accounts**:
   - `pattern-miner-sa` (Cloud Run)
   - `pattern-miner-postgres-vm` (PostgreSQL VM)
8. **IAM Bindings**: Secret access, bucket access
9. **Cloud Run Service**: `pattern-miner`
   - Connected to VPC via connector
   - Environment variables configured
   - Secrets injected

### Database Setup

The PostgreSQL VM startup script automatically:

1. ✅ Installs PostgreSQL 15
2. ✅ Installs pgvector (if enabled)
3. ✅ Creates database and user
4. ✅ Creates `pattern_analyses` table with indexes
5. ✅ Configures automated daily backups
6. ✅ Sets up monitoring with Cloud Ops Agent
7. ✅ Optimizes PostgreSQL settings for e2-micro

## Configuration Options

### Machine Type

```hcl
# Free tier (sufficient for development/testing)
postgres_machine_type = "e2-micro"  # 2 vCPU, 1GB RAM - FREE

# Production (handles more load)
postgres_machine_type = "e2-small"  # 2 vCPU, 2GB RAM - $15/month
postgres_machine_type = "e2-medium" # 2 vCPU, 4GB RAM - $30/month
```

### Disk Size

```hcl
# Default
postgres_disk_size_gb = 30  # ~$0.60/month

# For more data
postgres_disk_size_gb = 50  # ~$1/month
postgres_disk_size_gb = 100 # ~$2/month
```

### pgvector Extension

Enable for vector similarity search (like dev-nexus):

```hcl
enable_pgvector = true
```

Adds ~5 minutes to initial setup (builds from source).

### VPC Configuration

**Option 1: Create new VPC** (default):
```hcl
create_vpc = true
vpc_cidr_range = "10.8.0.0/28"  # 16 IP addresses
```

**Option 2: Use existing VPC** (share with other services):
```hcl
create_vpc = false
existing_vpc_name = "my-vpc"
existing_subnet_name = "my-subnet"
```

### SSH Access

```hcl
allow_ssh = true
ssh_allowed_cidrs = [
  "YOUR_IP/32"  # Restrict to your IP!
]
```

**Security best practice**: Set to your specific IP, not `0.0.0.0/0`

## Management & Operations

### SSH into PostgreSQL VM

```bash
gcloud compute ssh pattern-miner-postgres --zone=us-central1-a

# Connect to PostgreSQL
sudo -u postgres psql pattern_miner

# Check tables
\dt

# Query analyses
SELECT COUNT(*) FROM pattern_analyses;

# Exit
\q
exit
```

### Health Check Script

```bash
# SSH into VM
gcloud compute ssh pattern-miner-postgres --zone=us-central1-a

# Run health check
sudo /usr/local/bin/postgres-health.sh
```

Output shows:
- PostgreSQL uptime
- Active connections
- Database size
- Top queries

### Manual Backup

```bash
# SSH into VM
gcloud compute ssh pattern-miner-postgres --zone=us-central1-a

# Run backup
sudo /usr/local/bin/backup-postgres.sh

# Verify backup
gsutil ls gs://PROJECT_ID-pattern-miner-postgres-backups/backups/
```

### Restore from Backup

```bash
# Download backup
gsutil cp gs://PROJECT_ID-pattern-miner-postgres-backups/backups/pattern_miner_backup_XXXXXXXX.sql.gz .

# Gunzip
gunzip pattern_miner_backup_XXXXXXXX.sql.gz

# Restore
sudo -u postgres psql pattern_miner < pattern_miner_backup_XXXXXXXX.sql
```

### View Logs

```bash
# Cloud Run logs
gcloud run services logs read pattern-miner --region=us-central1 --limit=100

# PostgreSQL VM logs
gcloud compute ssh pattern-miner-postgres --zone=us-central1-a
sudo journalctl -u postgresql -f
```

## Monitoring

### Cloud Console Dashboards

1. **Compute Engine → pattern-miner-postgres**
   - CPU usage
   - Disk I/O
   - Network traffic

2. **Cloud Run → pattern-miner**
   - Request count
   - Request latency
   - Instance count

3. **Cloud Storage → backups bucket**
   - Backup size
   - Backup count

### Query Performance

```bash
# SSH into VM
gcloud compute ssh pattern-miner-postgres --zone=us-central1-a

# Connect to database
sudo -u postgres psql pattern_miner

# Top queries by total time
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;

# Database size
SELECT pg_size_pretty(pg_database_size('pattern_miner'));

# Table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Scaling

### Vertical Scaling (More Resources)

```hcl
# In terraform.tfvars
postgres_machine_type = "e2-small"  # Upgrade to 2GB RAM
postgres_disk_size_gb = 50          # Increase disk
```

```bash
terraform apply
```

**Note**: Requires VM restart (~2 minutes downtime)

### Horizontal Scaling (Read Replicas)

Not supported with Compute Engine VMs. Consider migrating to Cloud SQL if you need:
- Read replicas
- High availability (HA)
- Automatic failover
- Multi-region

## Troubleshooting

### PostgreSQL VM Not Starting

```bash
# Check VM status
gcloud compute instances describe pattern-miner-postgres \
  --zone=us-central1-a \
  --format="value(status)"

# Should be: RUNNING

# View startup script logs
gcloud compute instances get-serial-port-output pattern-miner-postgres \
  --zone=us-central1-a
```

### Connection Issues from Cloud Run

```bash
# Check VPC Connector
gcloud compute networks vpc-access connectors describe pattern-miner-connector \
  --region=us-central1

# Should show: state=READY

# Check Cloud Run logs
gcloud run services logs read pattern-miner --region=us-central1 --limit=50 | grep -i database
```

### Database Connection Refused

```bash
# SSH into VM
gcloud compute ssh pattern-miner-postgres --zone=us-central1-a

# Check PostgreSQL status
sudo systemctl status postgresql

# Check PostgreSQL is listening
sudo netstat -tlnp | grep 5432

# Check firewall rules
sudo iptables -L -n | grep 5432

# Test local connection
sudo -u postgres psql -c "SELECT 1"
```

### Backups Not Working

```bash
# Check backup logs
gcloud compute ssh pattern-miner-postgres --zone=us-central1-a
sudo tail -f /var/log/postgres-backup.log

# Check service account permissions
gsutil iam get gs://PROJECT_ID-pattern-miner-postgres-backups/

# Manually run backup
sudo /usr/local/bin/backup-postgres.sh
```

## Updating

### Code Changes

```bash
# Rebuild image
docker build -t gcr.io/${PROJECT_ID}/pattern-miner:latest .
docker push gcr.io/${PROJECT_ID}/pattern-miner:latest

# Redeploy Cloud Run (terraform not needed)
gcloud run services update pattern-miner \
  --image gcr.io/${PROJECT_ID}/pattern-miner:latest \
  --region=us-central1
```

### Infrastructure Changes

```bash
# Edit terraform.tfvars
nano terraform.tfvars

# Apply changes
terraform plan
terraform apply
```

### PostgreSQL Upgrades

```bash
# Major version upgrades require manual migration
# For patch updates:
gcloud compute ssh pattern-miner-postgres --zone=us-central1-a
sudo apt-get update
sudo apt-get upgrade postgresql-15
sudo systemctl restart postgresql
```

## Destroying Infrastructure

**⚠️ WARNING**: This deletes everything including backups!

```bash
# Destroy all resources
terraform destroy

# Manual cleanup (if needed)
gcloud secrets delete GITHUB_TOKEN
gcloud secrets delete ANTHROPIC_API_KEY
gcloud secrets delete PATTERN_MINER_DB_PASSWORD
```

## Migration to Cloud SQL (Future)

If you later need Cloud SQL features:

```bash
# 1. Backup data
gcloud compute ssh pattern-miner-postgres --zone=us-central1-a
sudo -u postgres pg_dump pattern_miner | gzip > backup.sql.gz
gsutil cp backup.sql.gz gs://your-bucket/

# 2. Create Cloud SQL instance
gcloud sql instances create pattern-miner-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# 3. Import data
gsutil cp gs://your-bucket/backup.sql.gz .
gunzip backup.sql.gz
gcloud sql import sql pattern-miner-db gs://your-bucket/backup.sql

# 4. Update Terraform to use Cloud SQL
```

## Comparison: VM vs Cloud SQL

| Feature | Compute Engine VM | Cloud SQL |
|---------|-------------------|-----------|
| **Cost** | $0-1/month | $7-50/month |
| **Setup** | Manual (Terraform) | Managed |
| **Backups** | Manual/scripted | Automatic |
| **HA** | No | Yes (optional) |
| **Scaling** | Manual | Automatic |
| **Maintenance** | You manage | Google manages |
| **Free Tier** | Yes (e2-micro) | No |

**Recommendation**: Use VM for development/small projects, Cloud SQL for production with high availability requirements.

## Summary

✅ **Own PostgreSQL VM** (not shared, not Cloud SQL)
✅ **Same architecture** as dev-nexus
✅ **Free tier eligible** (e2-micro VM)
✅ **Automated backups** to Cloud Storage
✅ **Private VPC** for security
✅ **Fully managed** by Terraform
✅ **~$1-2/month** total cost

You now have a production-ready, cost-effective PostgreSQL deployment following GCP best practices!
