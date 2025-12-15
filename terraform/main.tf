# Pattern Miner - Terraform Configuration for GCP Cloud Run

terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "run_api" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifact_registry_api" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secretmanager_api" {
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

# Create Secret Manager secrets for sensitive data
# Secrets - Create or Reference Existing
# Use create_secrets=true to create new secrets
# Use create_secrets=false to reference existing secrets (default)

resource "google_secret_manager_secret" "github_token" {
  count     = var.create_secrets ? 1 : 0
  secret_id = "GITHUB_TOKEN"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager_api]
}

data "google_secret_manager_secret" "github_token_existing" {
  count     = var.create_secrets ? 0 : 1
  secret_id = "GITHUB_TOKEN"
}

resource "google_secret_manager_secret" "anthropic_api_key" {
  count     = var.create_secrets ? 1 : 0
  secret_id = "ANTHROPIC_API_KEY"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager_api]
}

data "google_secret_manager_secret" "anthropic_api_key_existing" {
  count     = var.create_secrets ? 0 : 1
  secret_id = "ANTHROPIC_API_KEY"
}

# Database password secret
# Create new secret if deploying standalone PostgreSQL VM
# Otherwise, reference existing secret (e.g., shared with dev-nexus)

resource "google_secret_manager_secret" "db_password" {
  count     = var.use_database && var.create_postgres_vm ? 1 : 0
  secret_id = var.db_password_secret

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager_api]
}

# Note: You need to manually add the secret value:
# echo -n "your-db-password" | gcloud secrets versions add PATTERN_MINER_DB_PASSWORD --data-file=-

# Reference existing secret if not creating new one
data "google_secret_manager_secret" "db_password_existing" {
  count     = var.use_database && !var.create_postgres_vm ? 1 : 0
  secret_id = var.db_password_secret
}

# Note: You need to manually add secret versions via:
# echo -n "your-github-token" | gcloud secrets versions add GITHUB_TOKEN --data-file=-
# echo -n "your-anthropic-key" | gcloud secrets versions add ANTHROPIC_API_KEY --data-file=-

# Service account for Cloud Run
resource "google_service_account" "pattern_miner" {
  account_id   = "pattern-miner-sa"
  display_name = "Pattern Miner Service Account"
  description  = "Service account for pattern-miner Cloud Run service"
}

# Grant service account access to secrets
resource "google_secret_manager_secret_iam_member" "github_token_access" {
  secret_id = var.create_secrets ? google_secret_manager_secret.github_token[0].id : data.google_secret_manager_secret.github_token_existing[0].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.pattern_miner.email}"
}

resource "google_secret_manager_secret_iam_member" "anthropic_key_access" {
  secret_id = var.create_secrets ? google_secret_manager_secret.anthropic_api_key[0].id : data.google_secret_manager_secret.anthropic_api_key_existing[0].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.pattern_miner.email}"
}

resource "google_secret_manager_secret_iam_member" "db_password_access" {
  count     = var.use_database ? 1 : 0
  secret_id = var.create_postgres_vm ? google_secret_manager_secret.db_password[0].id : data.google_secret_manager_secret.db_password_existing[0].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.pattern_miner.email}"
}

# VPC Connector
# If create_postgres_vm=true, uses the connector created in postgres-vm.tf
# If create_postgres_vm=false, references existing connector (e.g., from dev-nexus)

data "google_vpc_access_connector" "existing" {
  count  = var.use_database && !var.create_postgres_vm ? 1 : 0
  name   = var.vpc_connector
  region = var.vpc_connector_region
}

# Cloud Run service
resource "google_cloud_run_v2_service" "pattern_miner" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.pattern_miner.email

    # VPC Access for connecting to PostgreSQL VM
    dynamic "vpc_access" {
      for_each = var.use_database ? [1] : []
      content {
        connector = var.create_postgres_vm ? google_vpc_access_connector.pattern_miner[0].id : data.google_vpc_access_connector.existing[0].id
        egress    = "PRIVATE_RANGES_ONLY"
      }
    }

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.auto_build_image ? local.built_image_url : var.container_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
        cpu_idle = true
      }

      env {
        name  = "AGENT_URL"
        value = "https://${var.service_name}-${var.project_id}.a.run.app"
      }

      env {
        name  = "DEV_NEXUS_URL"
        value = var.dev_nexus_url
      }

      env {
        name  = "PORT"
        value = "8080"
      }

      env {
        name  = "REQUIRE_AUTH"
        value = var.require_auth ? "true" : "false"
      }

      env {
        name  = "USE_DATABASE"
        value = var.use_database ? "true" : "false"
      }

      env {
        name  = "DATABASE_URL"
        value = var.database_url
      }

      env {
        name  = "DB_HOST"
        value = var.create_postgres_vm ? (length(google_compute_instance.postgres) > 0 ? google_compute_instance.postgres[0].network_interface[0].network_ip : var.db_host) : var.db_host
      }

      env {
        name  = "DB_PORT"
        value = tostring(var.db_port)
      }

      env {
        name  = "DB_NAME"
        value = var.db_name
      }

      env {
        name  = "DB_USER"
        value = var.db_user
      }

      env {
        name = "GITHUB_TOKEN"
        value_source {
          secret_key_ref {
            secret  = var.create_secrets ? google_secret_manager_secret.github_token[0].secret_id : data.google_secret_manager_secret.github_token_existing[0].secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.create_secrets ? google_secret_manager_secret.anthropic_api_key[0].secret_id : data.google_secret_manager_secret.anthropic_api_key_existing[0].secret_id
            version = "latest"
          }
        }
      }

      dynamic "env" {
        for_each = var.use_database ? [1] : []
        content {
          name = "DB_PASSWORD"
          value_source {
            secret_key_ref {
              secret  = var.create_postgres_vm ? google_secret_manager_secret.db_password[0].secret_id : data.google_secret_manager_secret.db_password_existing[0].secret_id
              version = "latest"
            }
          }
        }
      }
    }

    timeout = "3600s"  # 1 hour timeout for long-running pattern mining
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.run_api,
    google_secret_manager_secret_iam_member.github_token_access,
    google_secret_manager_secret_iam_member.anthropic_key_access,
    null_resource.build_image
  ]
}

# Allow unauthenticated access
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  count = var.allow_public_access ? 1 : 0

  location = google_cloud_run_v2_service.pattern_miner.location
  name     = google_cloud_run_v2_service.pattern_miner.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Optional: Cloud Scheduler for periodic pattern mining
resource "google_cloud_scheduler_job" "pattern_mining_schedule" {
  count = var.enable_scheduled_mining ? 1 : 0

  name             = "pattern-mining-weekly"
  description      = "Trigger pattern mining weekly"
  schedule         = var.mining_schedule
  time_zone        = "America/New_York"
  attempt_deadline = "3600s"

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.pattern_miner.uri}/api/mine-patterns"

    oidc_token {
      service_account_email = google_service_account.pattern_miner.email
    }
  }

  depends_on = [google_cloud_run_v2_service.pattern_miner]
}