# PostgreSQL VM for Pattern Miner
# Based on dev-nexus architecture (e2-micro, private VPC, no public IP)

# VPC Network (or use existing)
resource "google_compute_network" "pattern_miner_vpc" {
  count                   = var.create_vpc ? 1 : 0
  name                    = "${var.service_name}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "pattern_miner_subnet" {
  count         = var.create_vpc ? 1 : 0
  name          = "${var.service_name}-subnet"
  ip_cidr_range = var.vpc_cidr_range
  region        = var.region
  network       = google_compute_network.pattern_miner_vpc[0].id
}

# Firewall rule - allow PostgreSQL from VPC Connector
resource "google_compute_firewall" "allow_postgres" {
  count   = var.create_postgres_vm ? 1 : 0
  name    = "${var.service_name}-allow-postgres"
  network = var.create_vpc ? google_compute_network.pattern_miner_vpc[0].name : var.existing_vpc_name

  allow {
    protocol = "tcp"
    ports    = ["5432"]
  }

  # Allow from VPC connector range and internal subnet
  source_ranges = [
    var.vpc_connector_cidr,
    var.vpc_cidr_range
  ]

  target_tags = ["postgres-server"]
}

# Firewall rule - allow SSH (optional, for maintenance)
resource "google_compute_firewall" "allow_ssh" {
  count   = var.create_postgres_vm && var.allow_ssh ? 1 : 0
  name    = "${var.service_name}-allow-ssh"
  network = var.create_vpc ? google_compute_network.pattern_miner_vpc[0].name : var.existing_vpc_name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = var.ssh_allowed_cidrs
  target_tags   = ["postgres-server"]
}

# Cloud Storage bucket for backups
resource "google_storage_bucket" "postgres_backups" {
  count         = var.create_postgres_vm ? 1 : 0
  name          = "${var.project_id}-${var.service_name}-postgres-backups"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = var.backup_retention_days
    }
    action {
      type = "Delete"
    }
  }

  versioning {
    enabled = true
  }
}

# Service account for PostgreSQL VM
resource "google_service_account" "postgres_vm" {
  count        = var.create_postgres_vm ? 1 : 0
  account_id   = "${var.service_name}-postgres-vm"
  display_name = "PostgreSQL VM Service Account for ${var.service_name}"
}

# Grant backup bucket access to VM service account
resource "google_storage_bucket_iam_member" "postgres_backup_access" {
  count  = var.create_postgres_vm ? 1 : 0
  bucket = google_storage_bucket.postgres_backups[0].name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.postgres_vm[0].email}"
}

# PostgreSQL VM instance
resource "google_compute_instance" "postgres" {
  count        = var.create_postgres_vm ? 1 : 0
  name         = "${var.service_name}-postgres"
  machine_type = var.postgres_machine_type
  zone         = var.postgres_zone

  tags = ["postgres-server"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = var.postgres_disk_size_gb
      type  = "pd-standard"
    }
  }

  network_interface {
    network    = var.create_vpc ? google_compute_network.pattern_miner_vpc[0].name : var.existing_vpc_name
    subnetwork = var.create_vpc ? google_compute_subnetwork.pattern_miner_subnet[0].name : var.existing_subnet_name

    # No external IP for security
    # access_config {} # Uncomment to add external IP if needed
  }

  service_account {
    email  = google_service_account.postgres_vm[0].email
    scopes = ["cloud-platform"]
  }

  metadata = {
    db_name         = var.db_name
    db_user         = var.db_user
    db_password     = var.postgres_vm_password
    backup_bucket   = google_storage_bucket.postgres_backups[0].name
    enable_pgvector = tostring(var.enable_pgvector)
  }

  metadata_startup_script = file("${path.module}/scripts/postgres-startup.sh")

  allow_stopping_for_update = true

  depends_on = [
    google_storage_bucket.postgres_backups,
    google_service_account.postgres_vm
  ]
}

# VPC Access Connector for Cloud Run to connect to PostgreSQL
resource "google_vpc_access_connector" "pattern_miner" {
  count  = var.create_postgres_vm ? 1 : 0
  name   = "${var.service_name}-connector"
  region = var.region

  subnet {
    name = var.create_vpc ? google_compute_subnetwork.pattern_miner_subnet[0].name : var.existing_subnet_name
  }

  machine_type  = "e2-micro"
  min_instances = 2
  max_instances = 3

  depends_on = [
    google_compute_subnetwork.pattern_miner_subnet
  ]
}

# Output PostgreSQL VM internal IP
output "postgres_internal_ip" {
  description = "Internal IP address of PostgreSQL VM"
  value       = var.create_postgres_vm ? google_compute_instance.postgres[0].network_interface[0].network_ip : "N/A"
}

output "postgres_vm_name" {
  description = "Name of PostgreSQL VM"
  value       = var.create_postgres_vm ? google_compute_instance.postgres[0].name : "N/A"
}

output "postgres_backup_bucket" {
  description = "Cloud Storage bucket for PostgreSQL backups"
  value       = var.create_postgres_vm ? google_storage_bucket.postgres_backups[0].name : "N/A"
}

output "vpc_connector_name" {
  description = "VPC Connector name for Cloud Run"
  value       = var.create_postgres_vm ? google_vpc_access_connector.pattern_miner[0].name : var.vpc_connector
}
