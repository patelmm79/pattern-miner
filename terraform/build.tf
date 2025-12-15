# Cloud Build integration for Pattern Miner
# Builds Docker image using Cloud Build before deploying to Cloud Run

# Enable Cloud Build API
resource "google_project_service" "cloudbuild_api" {
  service            = "cloudbuild.googleapis.com"
  disable_on_destroy = false
}

# Build Docker image using Cloud Build
resource "null_resource" "build_image" {
  # Trigger rebuild when source code changes
  triggers = {
    # Use git commit SHA or timestamp
    source_hash = timestamp()
  }

  provisioner "local-exec" {
    command = <<-EOT
      cd ${path.module}/..
      gcloud builds submit \
        --config=cloudbuild.yaml \
        --project=${var.project_id} \
        --substitutions=SHORT_SHA=$(git rev-parse --short HEAD || echo "manual")
    EOT
  }

  depends_on = [
    google_project_service.cloudbuild_api
  ]
}

# Output the image URL that was built
locals {
  built_image_url = "gcr.io/${var.project_id}/pattern-miner:latest"
}

output "built_image_url" {
  description = "URL of the Docker image built by Cloud Build"
  value       = local.built_image_url
}
