output "bot_id" {
  description = "ID of the Bot Service"
  value       = azurerm_bot_service_azure_bot.main.id
}

output "bot_name" {
  description = "Name of the Bot Service"
  value       = azurerm_bot_service_azure_bot.main.name
}

output "bot_endpoint" {
  description = "Endpoint URL of the Bot Service"
  value       = azurerm_bot_service_azure_bot.main.endpoint
}

output "microsoft_app_id" {
  description = "Microsoft App ID of the Bot Service"
  value       = azurerm_bot_service_azure_bot.main.microsoft_app_id
}
