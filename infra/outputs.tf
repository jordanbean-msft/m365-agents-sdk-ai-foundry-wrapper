output "subscription_id" {
  description = "Subscription ID where resources are deployed"
  value       = var.subscription_id_resources
}

output "resource_group_name" {
  description = "Name of the resource group where resources are deployed"
  value       = var.resource_group_name_resources
}

output "ai_foundry_project_endpoint" {
  description = "Full endpoint URL for AI Foundry project SDK access"
  value       = module.project.ai_foundry_project_endpoint
}

output "logic_app_name" {
  description = "Name of the deployed Logic App"
  value       = module.logic_apps.logic_app_name
}

output "ai_model_deployment_name" {
  description = "Name of the AI model deployment (gpt-4o)"
  value       = module.ai_foundry.ai_model_deployment_name
}

# ACR outputs promoted for build/push scripting (previously only accessible via module references)
output "acr_login_server" {
  description = "Login server (FQDN) of the Azure Container Registry"
  value       = module.acr.acr_login_server
}

output "acr_name" {
  description = "Name of the Azure Container Registry"
  value       = module.acr.acr_name
}
