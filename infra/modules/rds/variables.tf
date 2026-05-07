variable "environment" {
  description = "Deployment environment (prod, staging)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where RDS will be deployed"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the DB subnet group (minimum 2, different AZs)"
  type        = list(string)
}

variable "allowed_security_group_ids" {
  description = "Security group IDs allowed to connect to RDS (e.g. Lambda, ECS task SGs)"
  type        = list(string)
  default     = []
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to connect to RDS (use sparingly — prefer SG-to-SG)"
  type        = list(string)
  default     = []
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "compliancerag"
}

variable "db_username" {
  description = "Master DB username"
  type        = string
  default     = "compliancerag"
}

variable "db_password" {
  description = "Master DB password — provide via tfvars or secrets manager, never hardcode"
  type        = string
  sensitive   = true
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "allocated_storage_gb" {
  description = "Allocated storage in GB"
  type        = number
  default     = 20
}

variable "multi_az" {
  description = "Enable Multi-AZ deployment"
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Prevent accidental deletion"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
