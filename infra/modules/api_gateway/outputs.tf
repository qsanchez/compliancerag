output "api_endpoint" {
  description = "API Gateway invoke URL — set as API_ENDPOINT env var or share with consumers"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "api_id" {
  value = aws_apigatewayv2_api.this.id
}
