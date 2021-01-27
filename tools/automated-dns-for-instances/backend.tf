terraform {
  required_version = ">=0.12"
  required_providers {
    google = {
      source = "hashicorp/google"
    }
  }
  backend "gcs" {
    bucket = "asset-inventory-org-feed-state"
    //prefix = ""
  }
}
