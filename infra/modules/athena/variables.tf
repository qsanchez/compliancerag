variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "database_name" {
  description = "Glue/Athena database name"
  type        = string
  default     = "compliancerag"
}

variable "analytics_data_bucket" {
  description = "S3 bucket name where Parquet data files are stored"
  type        = string
}

variable "athena_results_bucket" {
  description = "S3 bucket name for Athena query results"
  type        = string
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
