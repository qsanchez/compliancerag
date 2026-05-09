terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment to store state in S3 (recommended for prod):
  # backend "s3" {
  #   bucket = "compliancerag-tfstate"
  #   key    = "infra/terraform.tfstate"
  #   region = var.aws_region
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "compliancerag"
      ManagedBy = "terraform"
    }
  }
}

# ── Variables ─────────────────────────────────────────────────────────────────

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for all resources"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs (min 2, different AZs) for RDS"
  type        = list(string)
}

variable "compute_security_group_ids" {
  description = "Security group IDs of compute resources (Lambda, ECS) that need DB access"
  type        = list(string)
  default     = []
}

variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "bedrock_model_id" {
  description = "Bedrock model ID for LLM generation"
  type        = string
}

variable "database_url" {
  description = "Full PostgreSQL connection URL including password"
  type        = string
  sensitive   = true
}

variable "athena_s3_output" {
  description = "S3 URI for Athena query results"
  type        = string
  default     = ""
}

variable "athena_s3_data_bucket" {
  description = "S3 bucket name for analytics Parquet data"
  type        = string
  default     = ""
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

variable "langchain_tracing_v2" {
  type    = bool
  default = false
}

# ── Modules ───────────────────────────────────────────────────────────────────

module "rds" {
  source = "./modules/rds"

  environment                = var.environment
  vpc_id                     = var.vpc_id
  subnet_ids                 = var.private_subnet_ids
  allowed_security_group_ids = var.compute_security_group_ids
  db_password                = var.db_password
  instance_class             = var.rds_instance_class
  deletion_protection        = var.environment == "prod"
}

module "s3" {
  source      = "./modules/s3"
  environment = var.environment
}

module "athena" {
  source = "./modules/athena"

  environment           = var.environment
  analytics_data_bucket = module.s3.analytics_data_bucket
  athena_results_bucket = module.s3.athena_results_bucket
}

module "lambda" {
  source = "./modules/lambda"

  environment           = var.environment
  aws_region            = var.aws_region
  vpc_id                = var.vpc_id
  subnet_ids            = var.private_subnet_ids
  rds_security_group_id = module.rds.security_group_id

  bedrock_model_id      = var.bedrock_model_id
  database_url          = var.database_url
  athena_database       = module.athena.database_name
  athena_s3_output      = module.s3.athena_results_s3_uri
  athena_s3_data_bucket = module.s3.analytics_data_bucket
  api_key               = var.api_key
  langsmith_api_key     = var.langsmith_api_key
  langchain_tracing_v2  = var.langchain_tracing_v2
}

module "api_gateway" {
  source = "./modules/api_gateway"

  environment          = var.environment
  aws_region           = var.aws_region
  lambda_function_name = module.lambda.function_name
  lambda_function_arn  = module.lambda.function_arn
}

# ── Outputs ───────────────────────────────────────────────────────────────────

output "rds_endpoint" {
  description = "RDS connection endpoint"
  value       = module.rds.db_endpoint
}

output "rds_connection_url" {
  description = "PostgreSQL connection URL (password not included)"
  value       = module.rds.connection_url
}

output "rds_security_group_id" {
  value = module.rds.security_group_id
}

output "analytics_data_bucket" {
  description = "Set as ATHENA_S3_DATA_BUCKET env var"
  value       = module.s3.analytics_data_bucket
}

output "athena_s3_output" {
  description = "Set as ATHENA_S3_OUTPUT env var"
  value       = module.s3.athena_results_s3_uri
}

output "athena_database" {
  description = "Set as ATHENA_DATABASE env var"
  value       = module.athena.database_name
}

output "ecr_repository_url" {
  description = "Set as ECR_REPO for deploy tasks"
  value       = module.lambda.ecr_repository_url
}

output "lambda_function_name" {
  description = "Set as FUNCTION_NAME for deploy:update-lambda"
  value       = module.lambda.function_name
}

output "api_endpoint" {
  description = "API Gateway invoke URL"
  value       = module.api_gateway.api_endpoint
}
