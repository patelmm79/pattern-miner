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
  value       = google_secret_manager_secret.github_token.secret_id
}

output "anthropic_api_key_secret_id" {
  description = "Secret Manager ID for Anthropic API key"
  value       = google_secret_manager_secret.anthropic_api_key.secret_id
}

output "vpc_connector" {
  description = "VPC connector used for database access"
  value       = var.use_database ? var.vpc_connector : "N/A"
}

output "database_host" {
  description = "PostgreSQL database host (internal IP)"
  value       = var.use_database ? var.db_host : "N/A"
}

output "database_connection_info" {
  description = "Database connection information"
  value = var.use_database ? "PostgreSQL VM (shared with dev-nexus) at ${var.db_host}:${var.db_port}" : "Database disabled"
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
