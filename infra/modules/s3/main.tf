locals {
  name_prefix = "compliancerag-${var.environment}"
  common_tags = merge({ Project = "compliancerag", Environment = var.environment, ManagedBy = "terraform" }, var.tags)
}

# ── Analytics data bucket (Parquet files consumed by Athena) ──────────────────
resource "aws_s3_bucket" "analytics_data" {
  bucket        = "${local.name_prefix}-${var.aws_region}-analytics-data"
  force_destroy = true
  tags          = local.common_tags
}

resource "aws_s3_bucket_versioning" "analytics_data" {
  bucket = aws_s3_bucket.analytics_data.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "analytics_data" {
  bucket = aws_s3_bucket.analytics_data.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "analytics_data" {
  bucket                  = aws_s3_bucket.analytics_data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ── Athena query results bucket ───────────────────────────────────────────────
resource "aws_s3_bucket" "athena_results" {
  bucket        = "${local.name_prefix}-${var.aws_region}-athena-results"
  force_destroy = true
  tags          = local.common_tags
}

resource "aws_s3_bucket_server_side_encryption_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "athena_results" {
  bucket                  = aws_s3_bucket.athena_results.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id
  rule {
    id     = "expire-results"
    status = "Enabled"
    filter {}
    expiration { days = 7 }
  }
}
