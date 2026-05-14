variable "environment" {
  type = string
}

variable "lambda_function_name" {
  type = string
}

variable "lambda_function_arn" {
  type = string
}

variable "aws_region" {
  type    = string
  default = "eu-west-1"
}

variable "enable_jwt_auth" {
  description = "Enable Cognito JWT authorizer on all routes"
  type        = bool
  default     = false
}

variable "cognito_user_pool_id" {
  description = "Cognito User Pool ID — required when enable_jwt_auth is true"
  type        = string
  default     = ""
}

variable "cognito_user_pool_client_id" {
  description = "Cognito App Client ID — used as the JWT audience"
  type        = string
  default     = ""
}
