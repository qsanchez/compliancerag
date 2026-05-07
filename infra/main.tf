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
