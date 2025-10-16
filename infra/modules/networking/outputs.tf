output "pe_storage_id" {
  description = "ID of the storage account private endpoint"
  value       = azurerm_private_endpoint.pe_storage.id
}

output "pe_cosmosdb_id" {
  description = "ID of the Cosmos DB private endpoint"
  value       = azurerm_private_endpoint.pe_cosmosdb.id
}

output "pe_aisearch_id" {
  description = "ID of the AI Search private endpoint"
  value       = azurerm_private_endpoint.pe_aisearch.id
}

output "pe_aifoundry_id" {
  description = "ID of the AI Foundry private endpoint"
  value       = azurerm_private_endpoint.pe_aifoundry.id
}
