output "logic_app_id" {
  description = "ID of the Logic App Standard"
  value       = azurerm_logic_app_standard.logic_app.id
}

output "logic_app_name" {
  description = "Name of the Logic App Standard"
  value       = azurerm_logic_app_standard.logic_app.name
}

output "logic_app_principal_id" {
  description = "Principal ID of the Logic App managed identity"
  value       = azurerm_logic_app_standard.logic_app.identity[0].principal_id
}

output "logic_app_default_hostname" {
  description = "Default hostname of the Logic App"
  value       = azurerm_logic_app_standard.logic_app.default_hostname
}

output "storage_account_id" {
  description = "ID of the Logic Apps storage account"
  value       = azurerm_storage_account.logic_apps_storage.id
}

output "storage_account_name" {
  description = "Name of the Logic Apps storage account"
  value       = azurerm_storage_account.logic_apps_storage.name
}

output "app_service_plan_id" {
  description = "ID of the App Service Plan"
  value       = azurerm_service_plan.logic_apps_plan.id
}
