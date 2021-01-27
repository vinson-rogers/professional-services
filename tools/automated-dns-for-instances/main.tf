# must set billing_project & user_project_override
# for cloud asset api to work via terraform
provider "google" {
  project               = var.project_id
  billing_project       = var.project_id
  region                = var.region
  zone                  = var.zone
  user_project_override = true
}

provider "google-beta" {
  project               = var.project_id
  billing_project       = var.project_id
  region                = var.region
  zone                  = var.zone
  user_project_override = true
}
