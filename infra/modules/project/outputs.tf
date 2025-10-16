output "ai_foundry_project_id" {
  description = "ID of the AI Foundry project"
  value       = azapi_resource.ai_foundry_project.id
}

output "ai_foundry_project_name" {
  description = "Name of the AI Foundry project"
  value       = azapi_resource.ai_foundry_project.name
}

output "ai_foundry_project_principal_id" {
  description = "Principal ID of the AI Foundry project managed identity"
  value       = azapi_resource.ai_foundry_project.output.identity.principalId
}

output "ai_foundry_project_internal_id" {
  description = "Internal ID of the AI Foundry project"
  value       = azapi_resource.ai_foundry_project.output.properties.internalId
}
