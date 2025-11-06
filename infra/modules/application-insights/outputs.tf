output "application_insights_id" {
  description = "Resource ID of the Application Insights component (existing or newly created)"
  value       = var.existing_application_insights_id != null ? var.existing_application_insights_id : azurerm_application_insights.main[0].id
}

output "app_id" {
  description = "Application Insights application ID"
  value       = var.existing_application_insights_id != null ? data.azurerm_application_insights.existing[0].app_id : azurerm_application_insights.main[0].app_id
}

output "instrumentation_key" {
  description = "Instrumentation key for Application Insights"
  value       = var.existing_application_insights_id != null ? data.azurerm_application_insights.existing[0].instrumentation_key : azurerm_application_insights.main[0].instrumentation_key
}

output "connection_string" {
  description = "Connection string for Application Insights"
  value       = var.existing_application_insights_id != null ? data.azurerm_application_insights.existing[0].connection_string : azurerm_application_insights.main[0].connection_string
}
