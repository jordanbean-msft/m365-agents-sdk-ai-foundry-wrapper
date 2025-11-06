output "workspace_id" {
  description = "Resource ID of the Log Analytics workspace (existing or newly created)"
  value       = var.existing_workspace_id != null ? var.existing_workspace_id : azurerm_log_analytics_workspace.main[0].id
}

output "workspace_name" {
  description = "Name of the Log Analytics workspace"
  value       = var.existing_workspace_id != null ? split("/", var.existing_workspace_id)[8] : azurerm_log_analytics_workspace.main[0].name
}
