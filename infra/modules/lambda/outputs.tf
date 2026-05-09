output "function_name" {
  description = "Lambda function name — use as FUNCTION_NAME in deploy tasks"
  value       = aws_lambda_function.this.function_name
}

output "function_arn" {
  description = "Lambda function ARN — referenced by API Gateway integration"
  value       = aws_lambda_function.this.arn
}

output "ecr_repository_url" {
  description = "ECR repository URL — use as ECR_REPO in deploy tasks"
  value       = aws_ecr_repository.this.repository_url
}

output "lambda_security_group_id" {
  value = aws_security_group.lambda.id
}
