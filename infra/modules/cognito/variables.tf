variable "environment" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "callback_url" {
  description = "CloudFront URL — Cognito redirects here after login"
  type        = string
}
