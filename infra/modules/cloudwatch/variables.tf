variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "api_id" {
  description = "API Gateway HTTP API ID"
  type        = string
}

variable "lambda_function_name" {
  description = "Lambda function name"
  type        = string
}

variable "rds_instance_identifier" {
  description = "RDS instance identifier"
  type        = string
}

variable "lambda_memory_mb" {
  description = "Lambda memory allocation in MB (used for cost estimation)"
  type        = number
  default     = 2048
}

variable "billing_alarm_threshold_usd" {
  description = "Monthly estimated charges (USD) that trigger the billing alarm"
  type        = number
  default     = 50
}

variable "alarm_email" {
  description = "Email address that receives CloudWatch alarm notifications"
  type        = string
  default     = ""
}
