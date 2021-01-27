
# bucket to house function source
resource "google_storage_bucket" "function_bucket" {
  project                     = var.project_id
  name                        = var.function_bucket_name
  location                    = var.function_location
  force_destroy               = true
  uniform_bucket_level_access = true
}

# package up cloud function
data "archive_file" "function_archive" {
  type        = "zip"
  source_dir  = "./cloud-function/"
  output_path = "./cloud-function/asset-inventory-to-cloud-dns.zip"
}

# uploads function zip with randomized suffix to trigger re-deployment of cloud function
resource "google_storage_bucket_object" "archive" {
  #name = format("%s#%s", "asset-inventory-to-cloud-dns.zip", data.archive_file.function_archive.output_md5)
  name   = "asset-inventory-to-cloud-dns.zip" # keep package name to prevent function from re-deploying
  bucket = var.function_bucket_name
  source = data.archive_file.function_archive.output_path
}

resource "google_cloudfunctions_function" "function" {
  project     = var.project_id
  name        = var.function_name
  description = var.function_desc
  region      = var.region
  runtime     = "python38"

  available_memory_mb   = 128
  source_archive_bucket = google_storage_bucket.function_bucket.name
  source_archive_object = google_storage_bucket_object.archive.name
  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = google_pubsub_topic.feed_output.id
    //service    = "pubsub.googleapis.com"
  }
  ingress_settings = "ALLOW_INTERNAL_ONLY"
  timeout          = 60
  entry_point      = "vmToDNS"
  #entry_point = "justprintdata" # used for debugging asset feed & function trigger
}
