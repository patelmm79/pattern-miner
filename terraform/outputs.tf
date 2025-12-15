# Pattern Miner - Terraform Outputs

output "service_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.pattern_miner.uri
}

output "service_name" {
  description = "Name of the Cloud Run service"
  value       = google_cloud_run_v2_service.pattern_miner.name
}

output "service_account_email" {
  description = "Email of the service account used by Cloud Run"
  value       = google_service_account.pattern_miner.email
}

output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP region where service is deployed"
  value       = var.region
}

output "github_token_secret_id" {
  description = "Secret Manager ID for GitHub token"
  value       = var.create_secrets ? google_secret_manager_secret.github_token[0].secret_id : data.google_secret_manager_secret.github_token_existing[0].secret_id
}

output "anthropic_api_key_secret_id" {
  description = "Secret Manager ID for Anthropic API key"
  value       = var.create_secrets ? google_secret_manager_secret.anthropic_api_key[0].secret_id : data.google_secret_manager_secret.anthropic_api_key_existing[0].secret_id
}

output "vpc_connector" {
  description = "VPC connector used for database access"
  value       = var.use_database ? (var.create_postgres_vm ? google_vpc_access_connector.pattern_miner[0].name : var.vpc_connector) : "N/A"
}

output "database_host" {
  description = "PostgreSQL database host (internal IP)"
  value       = var.use_database ? (var.create_postgres_vm && length(google_compute_instance.postgres) > 0 ? google_compute_instance.postgres[0].network_interface[0].network_ip : var.db_host) : "N/A"
}

output "database_connection_info" {
  description = "Database connection information"
  value = var.use_database ? (var.create_postgres_vm ? "Standalone PostgreSQL VM at ${var.create_postgres_vm && length(google_compute_instance.postgres) > 0 ? google_compute_instance.postgres[0].network_interface[0].network_ip : var.db_host}:${var.db_port}" : "Shared PostgreSQL VM at ${var.db_host}:${var.db_port}") : "Database disabled"
}

output "postgres_vm_name" {
  description = "Name of the PostgreSQL VM instance (if created)"
  value       = var.create_postgres_vm && length(google_compute_instance.postgres) > 0 ? google_compute_instance.postgres[0].name : "N/A"
}

output "postgres_backup_bucket" {
  description = "Cloud Storage bucket for PostgreSQL backups (if created)"
  value       = var.create_postgres_vm && length(google_storage_bucket.postgres_backups) > 0 ? google_storage_bucket.postgres_backups[0].name : "N/A"
}

output "db_password_secret_id" {
  description = "Secret Manager ID for database password"
  value       = var.use_database ? (var.create_postgres_vm ? google_secret_manager_secret.db_password[0].secret_id : data.google_secret_manager_secret.db_password_existing[0].secret_id) : "N/A"
}

output "test_commands" {
  description = "Commands to test the deployed service"
  value = <<-EOT
    # Health check
    curl ${google_cloud_run_v2_service.pattern_miner.uri}/

    # View configuration
    curl ${google_cloud_run_v2_service.pattern_miner.uri}/api/config

    # Trigger pattern mining
    curl -X POST ${google_cloud_run_v2_service.pattern_miner.uri}/api/mine-patterns

    # Mine specific pattern type
    curl -X POST "${google_cloud_run_v2_service.pattern_miner.uri}/api/mine-patterns?pattern_type=deployment"
  EOT
}
