org_id     = <ORG_ID_NUMBER>
project_id = "<PROJECT_ID>"
region     = "us-central1"
zone       = "us-central1-f"
feed_id    = "org_ai_feed_compute"

function_name        = "asset-inventory-to-dns"
function_desc        = "parses asset inventory updates and creates Cloud DNS changes"
function_bucket_name = "asset-inventory-to-dns"
function_location    = "us-central1"
