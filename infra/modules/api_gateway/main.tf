locals {
  name_prefix = "compliancerag-${var.environment}"
}

resource "aws_apigatewayv2_api" "this" {
  name          = local.name_prefix
  protocol_type = "HTTP"
  description   = "ComplianceRAG HTTP API"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type", "X-API-Key", "Authorization"]
    max_age       = 3600
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.lambda_function_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_authorizer" "cognito" {
  count = var.enable_jwt_auth ? 1 : 0

  api_id           = aws_apigatewayv2_api.this.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "cognito"

  jwt_configuration {
    issuer   = "https://cognito-idp.${var.aws_region}.amazonaws.com/${var.cognito_user_pool_id}"
    audience = [var.cognito_user_pool_client_id]
  }
}

resource "aws_apigatewayv2_route" "proxy" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"

  authorization_type = var.enable_jwt_auth ? "JWT" : "NONE"
  authorizer_id      = var.enable_jwt_auth ? aws_apigatewayv2_authorizer.cognito[0].id : null
}

resource "aws_apigatewayv2_route" "root" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "ANY /"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"

  authorization_type = var.enable_jwt_auth ? "JWT" : "NONE"
  authorizer_id      = var.enable_jwt_auth ? aws_apigatewayv2_authorizer.cognito[0].id : null
}


# OPTIONS routes bypass the JWT authorizer so CORS preflight succeeds.
# Managed cors_configuration adds headers but does NOT skip the JWT check on
# ANY /{proxy+} — explicit NONE-auth OPTIONS routes are required.
resource "aws_apigatewayv2_route" "options_proxy" {
  count     = var.enable_jwt_auth ? 1 : 0
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "OPTIONS /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"

  authorization_type = "NONE"
}

resource "aws_apigatewayv2_route" "options_root" {
  count     = var.enable_jwt_auth ? 1 : 0
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "OPTIONS /"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"

  authorization_type = "NONE"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gw.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      responseLength = "$context.responseLength"
      latency        = "$context.responseLatency"
    })
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "api_gw" {
  name              = "/aws/apigateway/${local.name_prefix}"
  retention_in_days = 30

  tags = {
    Environment = var.environment
  }
}

resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}
