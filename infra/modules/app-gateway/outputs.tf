output "application_gateway_id" {
  description = "ID of the Application Gateway"
  value       = azurerm_application_gateway.main.id
}

output "application_gateway_name" {
  description = "Name of the Application Gateway"
  value       = azurerm_application_gateway.main.name
}

output "public_ip_address" {
  description = "Public IP address of the Application Gateway"
  value       = azurerm_public_ip.main.ip_address
}

output "public_ip_fqdn" {
  description = "FQDN of the Application Gateway public IP (if configured)"
  value       = azurerm_public_ip.main.fqdn
}

output "user_assigned_identity_principal_id" {
  description = "Principal ID of the Application Gateway user-assigned managed identity"
  value       = var.user_assigned_identity_principal_id
}

output "user_assigned_identity_id" {
  description = "Resource ID of the Application Gateway user-assigned managed identity"
  value       = var.user_assigned_identity_id
}
