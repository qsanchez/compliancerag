data "aws_caller_identity" "current" {}

locals {
  # Domain prefix must be globally unique across all AWS accounts
  domain_prefix = "${var.environment}-compliancerag-${data.aws_caller_identity.current.account_id}"
}

resource "aws_cognito_user_pool" "this" {
  name = "compliancerag-${var.environment}"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 8
    require_uppercase = true
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_cognito_user_pool_client" "this" {
  name         = "compliancerag-${var.environment}-web"
  user_pool_id = aws_cognito_user_pool.this.id

  # Public client — no client secret (browser app)
  generate_secret = false

  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["implicit"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]

  callback_urls = [var.callback_url]
  logout_urls   = [var.callback_url]

  supported_identity_providers = ["COGNITO"]
}

resource "aws_cognito_user_pool_domain" "this" {
  domain       = local.domain_prefix
  user_pool_id = aws_cognito_user_pool.this.id
}
