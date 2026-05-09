variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the Lambda security group"
  type        = string
}

variable "subnet_ids" {
  description = "Private subnet IDs for Lambda VPC config"
  type        = list(string)
}

variable "rds_security_group_id" {
  description = "RDS security group ID — Lambda will be granted ingress on port 5432"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "lambda_memory_mb" {
  description = "Lambda memory in MB — needs headroom for the reranker model"
  type        = number
  default     = 2048
}

variable "lambda_timeout_s" {
  description = "Lambda timeout in seconds — LLM calls can be slow"
  type        = number
  default     = 60
}

# ── App config passed as Lambda env vars ─────────────────────────────────────

variable "bedrock_model_id" {
  type = string
}

variable "bedrock_embedding_model_id" {
  type    = string
  default = "amazon.titan-embed-text-v2:0"
}

variable "database_url" {
  description = "Full PostgreSQL connection URL including password"
  type        = string
  sensitive   = true
}

variable "athena_database" {
  type    = string
  default = "compliancerag"
}

variable "athena_table_fines" {
  type    = string
  default = "gdpr_fines"
}

variable "athena_s3_output" {
  type = string
}

variable "athena_s3_data_bucket" {
  type = string
}

variable "api_key" {
  description = "API key for the /chat endpoint (empty = no auth)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "langsmith_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "langsmith_project" {
  type    = string
  default = "compliancerag"
}

variable "langchain_tracing_v2" {
  type    = bool
  default = false
}
