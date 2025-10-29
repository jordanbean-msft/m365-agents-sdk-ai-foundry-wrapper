output "ai_foundry_id" {
  description = "ID of the AI Foundry resource"
  value       = azapi_resource.ai_foundry.id
}

output "ai_foundry_name" {
  description = "Name of the AI Foundry resource"
  value       = azapi_resource.ai_foundry.name
}

output "ai_foundry_endpoint" {
  description = "Endpoint of the AI Foundry resource"
  value       = "https://${azapi_resource.ai_foundry.name}.cognitiveservices.azure.com/"
}

output "ai_model_deployment_name" {
  description = "Name of the default AI model deployment provisioned in this Foundry account"
  value       = azurerm_cognitive_deployment.aifoundry_deployment_gpt_4o.name
}
