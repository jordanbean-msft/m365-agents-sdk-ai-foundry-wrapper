output "user_assigned_identity_id" {
  description = "Resource ID of the user assigned managed identity"
  value       = azurerm_user_assigned_identity.container_app.id
}

output "user_assigned_identity_client_id" {
  description = "Client ID of the user assigned managed identity"
  value       = azurerm_user_assigned_identity.container_app.client_id
}

output "user_assigned_identity_principal_id" {
  description = "Principal ID of the user assigned managed identity"
  value       = azurerm_user_assigned_identity.container_app.principal_id
}
