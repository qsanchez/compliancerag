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
