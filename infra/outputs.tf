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
