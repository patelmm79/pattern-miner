#!/bin/bash
# PostgreSQL Startup Script for Pattern Miner
# Based on dev-nexus PostgreSQL setup

set -e

# Get metadata from GCP instance metadata server
METADATA_URL="http://metadata.google.internal/computeMetadata/v1/instance/attributes"
METADATA_HEADER="Metadata-Flavor: Google"

DB_NAME=$(curl -s -H "${METADATA_HEADER}" "${METADATA_URL}/db_name")
DB_USER=$(curl -s -H "${METADATA_HEADER}" "${METADATA_URL}/db_user")
DB_PASSWORD=$(curl -s -H "${METADATA_HEADER}" "${METADATA_URL}/db_password")
BACKUP_BUCKET=$(curl -s -H "${METADATA_HEADER}" "${METADATA_URL}/backup_bucket")
ENABLE_PGVECTOR=$(curl -s -H "${METADATA_HEADER}" "${METADATA_URL}/enable_pgvector")

echo "Starting PostgreSQL installation for Pattern Miner..."

# Update system
apt-get update
apt-get upgrade -y

# Install PostgreSQL 15
apt-get install -y postgresql-15 postgresql-contrib-15 postgresql-server-dev-15

# Install build tools for pgvector (if enabled)
if [ "$ENABLE_PGVECTOR" = "true" ]; then
    apt-get install -y build-essential git
fi

# Configure PostgreSQL to listen on all interfaces
cat >> /etc/postgresql/15/main/postgresql.conf <<EOF

# Pattern Miner Configuration
listen_addresses = '*'
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 2621kB
min_wal_size = 1GB
max_wal_size = 4GB
EOF

# Configure pg_hba.conf to allow connections from VPC
cat >> /etc/postgresql/15/main/pg_hba.conf <<EOF

# Allow connections from VPC
host    all             all             10.0.0.0/8              md5
host    all             all             172.16.0.0/12           md5
host    all             all             192.168.0.0/16          md5
EOF

# Restart PostgreSQL
systemctl restart postgresql

# Wait for PostgreSQL to start
sleep 5

# Create database and user
sudo -u postgres psql <<EOF
-- Create database
CREATE DATABASE ${DB_NAME};

-- Create user
CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};

-- Connect to database and grant schema privileges
\c ${DB_NAME}
GRANT ALL ON SCHEMA public TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${DB_USER};
EOF

# Install pgvector if enabled
if [ "$ENABLE_PGVECTOR" = "true" ]; then
    echo "Installing pgvector extension..."

    cd /tmp
    git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
    cd pgvector
    make
    make install

    # Enable extension
    sudo -u postgres psql -d ${DB_NAME} <<EOF
CREATE EXTENSION IF NOT EXISTS vector;
EOF

    echo "pgvector installed successfully"
fi

# Create pattern_analyses table
sudo -u postgres psql -d ${DB_NAME} <<'EOF'
CREATE TABLE IF NOT EXISTS pattern_analyses (
    analysis_id TEXT PRIMARY KEY,
    repository TEXT NOT NULL,
    results JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analyses_repository ON pattern_analyses(repository);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON pattern_analyses(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_patterns ON pattern_analyses USING GIN ((results->'patterns'));

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON pattern_analyses TO ${DB_USER};
EOF

echo "Database schema created successfully"

# Set up automated backups
cat > /usr/local/bin/backup-postgres.sh <<BACKUP_SCRIPT
#!/bin/bash
set -e

# Get metadata
METADATA_URL="http://metadata.google.internal/computeMetadata/v1/instance/attributes"
METADATA_HEADER="Metadata-Flavor: Google"
DB_NAME=\$(curl -s -H "\${METADATA_HEADER}" "\${METADATA_URL}/db_name")
BACKUP_BUCKET=\$(curl -s -H "\${METADATA_HEADER}" "\${METADATA_URL}/backup_bucket")

TIMESTAMP=\$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/tmp/pattern_miner_backup_\${TIMESTAMP}.sql.gz"

# Perform backup
sudo -u postgres pg_dump \${DB_NAME} | gzip > \$BACKUP_FILE

# Upload to Cloud Storage
gsutil cp \$BACKUP_FILE gs://\${BACKUP_BUCKET}/backups/

# Clean up local backup
rm \$BACKUP_FILE

echo "Backup completed: \$TIMESTAMP"
BACKUP_SCRIPT

chmod +x /usr/local/bin/backup-postgres.sh

# Set up daily backup cron job (2 AM UTC)
cat > /etc/cron.d/postgres-backup <<'CRON'
0 2 * * * root /usr/local/bin/backup-postgres.sh >> /var/log/postgres-backup.log 2>&1
CRON

# Enable pg_stat_statements for monitoring
sudo -u postgres psql -d ${DB_NAME} <<EOF
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
EOF

# Create monitoring script
cat > /usr/local/bin/postgres-health.sh <<HEALTH_SCRIPT
#!/bin/bash
# Get metadata
METADATA_URL="http://metadata.google.internal/computeMetadata/v1/instance/attributes"
METADATA_HEADER="Metadata-Flavor: Google"
DB_NAME=\$(curl -s -H "\${METADATA_HEADER}" "\${METADATA_URL}/db_name")

echo "=== PostgreSQL Health Check ==="
echo "Uptime:"
systemctl status postgresql | grep Active

echo -e "\nConnections:"
sudo -u postgres psql -c "SELECT count(*) as connections FROM pg_stat_activity;"

echo -e "\nDatabase size:"
sudo -u postgres psql -d \${DB_NAME} -c "SELECT pg_size_pretty(pg_database_size('\${DB_NAME}'));"

echo -e "\nTop queries:"
sudo -u postgres psql -d \${DB_NAME} -c "SELECT query, calls, total_time, mean_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 5;"
HEALTH_SCRIPT

chmod +x /usr/local/bin/postgres-health.sh

# Install Google Cloud Ops Agent for monitoring
curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
bash add-google-cloud-ops-agent-repo.sh --also-install

echo "PostgreSQL installation and configuration complete!"
echo "Database: ${DB_NAME}"
echo "User: ${DB_USER}"
echo "Backup bucket: ${BACKUP_BUCKET}"

# Run initial backup
/usr/local/bin/backup-postgres.sh
