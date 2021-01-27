
# Create a feed that sends notifications about compute instance updates under a
# particular organization.
resource "google_cloud_asset_organization_feed" "organization_feed" {
  provider        = google-beta
  billing_project = var.project_id
  org_id          = var.org_id
  feed_id         = var.feed_id
  content_type    = "RESOURCE"

  asset_types = [
    "compute.googleapis.com/Instance",
    "compute.googleapis.com/ForwardingRule",
  ]

  feed_output_config {
    pubsub_destination {
      topic = google_pubsub_topic.feed_output.id
    }
  }

  # setting conditions reduces the invocations of the function unecessarily
  condition {
    expression = <<-EOT
    ('status' in temporal_asset.asset.resource.data &&
    temporal_asset.asset.resource.data.status == "STAGING") ||
    temporal_asset.deleted ||
    'IPAddress' in temporal_asset.asset.resource.data
    EOT
    #('status' in temporal_asset.asset.resource.data &&
    #temporal_asset.asset.resource.data.status == "STAGING") ||
    #temporal_asset.deleted ||
    #("PRESENT" in temporal_asset.priorAssetState &&
    #'IPAddress' in temporal_asset.asset.resource.data)
    # send all events
    #expression  = <<-EOT
    #true
    #EOT
    title       = "GCE STAGING or Deletes"
    description = "Send notifications on instance STAGING and delete events"
  }

  # Wait for the permission to be ready on the destination topic.
  depends_on = [
    google_pubsub_topic_iam_member.cloud_asset_writer,
  ]
}

# The topic where the resource change notifications will be sent.
resource "google_pubsub_topic" "feed_output" {
  project = var.project_id
  name    = var.feed_id
}

# Find the project number of the project whose identity will be used for sending
# the asset change notifications.
data "google_project" "project" {
  project_id = var.project_id
}
