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
  default     = ""
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

variable "rds_publicly_accessible" {
  description = "Temporarily expose RDS to the internet for one-off ops (revert after)"
  type        = bool
  default     = false
}

variable "rds_allowed_cidr_blocks" {
  description = "CIDRs allowed to reach RDS directly (e.g. developer IP for ingestion)"
  type        = list(string)
  default     = []
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

module "networking" {
  source      = "./modules/networking"
  environment = var.environment
}

module "rds" {
  source = "./modules/rds"

  environment         = var.environment
  vpc_id              = module.networking.vpc_id
  subnet_ids          = module.networking.private_subnet_ids
  db_password         = var.db_password
  instance_class      = var.rds_instance_class
  deletion_protection = var.environment == "prod"
  publicly_accessible = var.rds_publicly_accessible
  allowed_cidr_blocks = var.rds_allowed_cidr_blocks
}

module "s3" {
  source      = "./modules/s3"
  environment = var.environment
  aws_region  = var.aws_region
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
  vpc_id                = module.networking.vpc_id
  subnet_ids            = module.networking.private_subnet_ids
  rds_security_group_id = module.rds.security_group_id

  bedrock_model_id      = var.bedrock_model_id
  database_url          = "postgresql://${module.rds.db_username}:${var.db_password}@${module.rds.db_endpoint}/${module.rds.db_name}"
  athena_database       = module.athena.database_name
  athena_s3_output      = module.s3.athena_results_s3_uri
  athena_s3_data_bucket = module.s3.analytics_data_bucket
  api_key               = var.api_key
  langsmith_api_key     = var.langsmith_api_key
  langchain_tracing_v2  = var.langchain_tracing_v2
}

module "frontend" {
  source      = "./modules/frontend"
  environment = var.environment
  aws_region  = var.aws_region
}

module "cognito" {
  source = "./modules/cognito"

  environment  = var.environment
  aws_region   = var.aws_region
  callback_url = module.frontend.domain_name
}

module "api_gateway" {
  source = "./modules/api_gateway"

  environment                 = var.environment
  aws_region                  = var.aws_region
  lambda_function_name        = module.lambda.function_name
  lambda_function_arn         = module.lambda.function_arn
  enable_jwt_auth             = true
  cognito_user_pool_id        = module.cognito.user_pool_id
  cognito_user_pool_client_id = module.cognito.user_pool_client_id
}

module "cloudwatch" {
  source = "./modules/cloudwatch"

  environment             = var.environment
  aws_region              = var.aws_region
  api_id                  = module.api_gateway.api_id
  lambda_function_name    = module.lambda.function_name
  rds_instance_identifier = "compliancerag-${var.environment}"
  lambda_memory_mb        = 2048
}

# ── VPC Endpoints ─────────────────────────────────────────────────────────────
# Lambda runs inside the VPC (to reach RDS) but has no NAT gateway.
# These endpoints let Lambda call Bedrock, S3, and Athena through the AWS
# backbone without internet egress.

resource "aws_security_group" "vpc_endpoints" {
  name        = "compliancerag-${var.environment}-vpc-endpoints"
  description = "Allow HTTPS from Lambda to Interface VPC endpoints"
  vpc_id      = module.networking.vpc_id

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [module.lambda.lambda_security_group_id]
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = module.networking.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [module.networking.private_route_table_id]

  tags = {
    Environment = var.environment
  }
}

resource "aws_vpc_endpoint" "bedrock_runtime" {
  vpc_id              = module.networking.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.bedrock-runtime"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [module.networking.private_subnet_ids[0]]
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Environment = var.environment
  }
}

resource "aws_vpc_endpoint" "athena" {
  vpc_id              = module.networking.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.athena"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [module.networking.private_subnet_ids[0]]
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Environment = var.environment
  }
}

resource "aws_vpc_endpoint" "bedrock_agent_runtime" {
  vpc_id              = module.networking.vpc_id
  service_name        = "com.amazonaws.${var.aws_region}.bedrock-agent-runtime"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [module.networking.private_subnet_ids[0]]
  security_group_ids  = [aws_security_group.vpc_endpoints.id]
  private_dns_enabled = true

  tags = {
    Environment = var.environment
  }
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

output "cloudwatch_dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = module.cloudwatch.dashboard_url
}

output "frontend_url" {
  description = "CloudFront URL — share with users"
  value       = module.frontend.domain_name
}

output "frontend_bucket_name" {
  description = "S3 bucket name — used by task frontend:deploy"
  value       = module.frontend.bucket_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID — used by task frontend:deploy for cache invalidation"
  value       = module.frontend.distribution_id
}

output "cognito_client_id" {
  description = "Set as COGNITO_CLIENT_ID in frontend config"
  value       = module.cognito.user_pool_client_id
}

output "cognito_login_url" {
  description = "Set as COGNITO_LOGIN_URL in frontend config"
  value       = module.cognito.login_url
}
