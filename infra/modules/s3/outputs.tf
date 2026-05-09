output "analytics_data_bucket" {
  description = "S3 bucket name for Parquet analytics data"
  value       = aws_s3_bucket.analytics_data.bucket
}

output "analytics_data_bucket_arn" {
  description = "S3 bucket ARN for IAM policies"
  value       = aws_s3_bucket.analytics_data.arn
}

output "athena_results_bucket" {
  description = "S3 bucket name for Athena query results"
  value       = aws_s3_bucket.athena_results.bucket
}

output "athena_results_s3_uri" {
  description = "S3 URI for ATHENA_S3_OUTPUT env var"
  value       = "s3://${aws_s3_bucket.athena_results.bucket}/"
}
