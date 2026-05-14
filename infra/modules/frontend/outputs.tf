output "bucket_name" {
  description = "S3 bucket name for frontend assets"
  value       = aws_s3_bucket.frontend.id
}

output "distribution_id" {
  description = "CloudFront distribution ID — used for cache invalidation"
  value       = aws_cloudfront_distribution.this.id
}

output "domain_name" {
  description = "CloudFront domain name — use as Cognito callback URL and REDIRECT_URI"
  value       = "https://${aws_cloudfront_distribution.this.domain_name}"
}
