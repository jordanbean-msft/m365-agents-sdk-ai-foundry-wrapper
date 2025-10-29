output "key_vault_id" {
  description = "Resource ID of the Key Vault"
  value       = azurerm_key_vault.main.id
}

output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  description = "URI of the Key Vault"
  value       = azurerm_key_vault.main.vault_uri
}

output "private_endpoint_id" {
  description = "Resource ID of the Key Vault private endpoint"
  value       = azurerm_private_endpoint.kv.id
}
