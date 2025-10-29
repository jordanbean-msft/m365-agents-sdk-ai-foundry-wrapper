output "acr_id" {
  description = "ID of the Azure Container Registry"
  value       = azurerm_container_registry.main.id
}

output "acr_name" {
  description = "Name of the Azure Container Registry"
  value       = azurerm_container_registry.main.name
}

output "acr_login_server" {
  description = "Login server (registry hostname)"
  value       = azurerm_container_registry.main.login_server
}

output "acr_private_endpoint_id" {
  description = "ID of the ACR private endpoint"
  value       = azurerm_private_endpoint.acr.id
}
