# Pattern Miner - Terraform Variables

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run deployment"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Name of the Cloud Run service"
  type        = string
  default     = "pattern-miner"
}

variable "container_image" {
  description = "Container image URL (auto-built by Cloud Build if not specified)"
  type        = string
  default     = ""
}

variable "auto_build_image" {
  description = "Automatically build Docker image using Cloud Build"
  type        = bool
  default     = true
}

variable "create_secrets" {
  description = "Create new secrets in Secret Manager (set false if secrets already exist)"
  type        = bool
  default     = false  # Default to using existing secrets
}

variable "cpu" {
  description = "CPU allocation for Cloud Run service"
  type        = string
  default     = "1"
}

variable "memory" {
  description = "Memory allocation for Cloud Run service"
  type        = string
  default     = "2Gi"
}

variable "min_instances" {
  description = "Minimum number of instances"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
  default     = 10
}

variable "allow_public_access" {
  description = "Allow unauthenticated public access to the service"
  type        = bool
  default     = true
}

variable "dev_nexus_url" {
  description = "URL for dev-nexus integration (optional)"
  type        = string
  default     = ""
}

variable "enable_scheduled_mining" {
  description = "Enable Cloud Scheduler for periodic pattern mining"
  type        = bool
  default     = false
}

variable "mining_schedule" {
  description = "Cron schedule for pattern mining (e.g., '0 9 * * 1' for every Monday at 9 AM)"
  type        = string
  default     = "0 9 * * 1"  # Every Monday at 9 AM
}

variable "require_auth" {
  description = "Require authentication for A2A endpoints"
  type        = bool
  default     = false
}

variable "use_database" {
  description = "Enable PostgreSQL database storage (shared with dev-nexus)"
  type        = bool
  default     = true
}

variable "database_url" {
  description = "PostgreSQL connection string (optional, can use individual db_* variables instead)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "db_host" {
  description = "Database host (internal VPC IP, e.g., 10.8.0.2)"
  type        = string
  default     = "10.8.0.2"
}

variable "db_port" {
  description = "Database port"
  type        = number
  default     = 5432
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "devnexus"
}

variable "db_user" {
  description = "Database user"
  type        = string
  default     = ""
}

variable "db_password_secret" {
  description = "Secret Manager secret name for database password"
  type        = string
  default     = "PATTERN_MINER_DB_PASSWORD"
}

variable "vpc_connector" {
  description = "VPC connector name for private VPC access (shared with dev-nexus)"
  type        = string
  default     = "devnexus-connector"
}

variable "vpc_connector_region" {
  description = "Region of the VPC connector"
  type        = string
  default     = "us-central1"
}

# PostgreSQL VM Configuration
variable "create_postgres_vm" {
  description = "Create a dedicated PostgreSQL VM (like dev-nexus architecture)"
  type        = bool
  default     = false  # Default to sharing dev-nexus PostgreSQL
}

variable "postgres_machine_type" {
  description = "Machine type for PostgreSQL VM (e2-micro for free tier)"
  type        = string
  default     = "e2-micro"
}

variable "postgres_zone" {
  description = "Zone for PostgreSQL VM"
  type        = string
  default     = "us-central1-a"
}

variable "postgres_disk_size_gb" {
  description = "Disk size for PostgreSQL VM in GB"
  type        = number
  default     = 30
}

variable "postgres_vm_password" {
  description = "Password for PostgreSQL (will be set in VM, also store in Secret Manager)"
  type        = string
  sensitive   = true
}

variable "enable_pgvector" {
  description = "Install pgvector extension (for vector similarity search)"
  type        = bool
  default     = false
}

variable "backup_retention_days" {
  description = "Number of days to retain PostgreSQL backups"
  type        = number
  default     = 30
}

# VPC Configuration
variable "create_vpc" {
  description = "Create new VPC network (set false to use existing)"
  type        = bool
  default     = true
}

variable "existing_vpc_name" {
  description = "Name of existing VPC network (if create_vpc=false)"
  type        = string
  default     = "default"
}

variable "existing_subnet_name" {
  description = "Name of existing subnet (if create_vpc=false)"
  type        = string
  default     = "default"
}

variable "vpc_cidr_range" {
  description = "CIDR range for VPC subnet"
  type        = string
  default     = "10.8.0.0/28"
}

variable "vpc_connector_cidr" {
  description = "CIDR range for VPC connector"
  type        = string
  default     = "10.8.0.0/28"
}

variable "allow_ssh" {
  description = "Allow SSH access to PostgreSQL VM"
  type        = bool
  default     = true
}

variable "ssh_allowed_cidrs" {
  description = "CIDR ranges allowed to SSH into PostgreSQL VM"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Restrict this in production!
}
