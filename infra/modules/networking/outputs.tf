output "pe_storage_id" {
  description = "ID of the storage account private endpoint (blob)"
  value       = azurerm_private_endpoint.pe_storage.id
}

output "pe_storage_file_id" {
  description = "ID of the storage account private endpoint (file)"
  value       = azurerm_private_endpoint.pe_storage_file.id
}

output "pe_storage_queue_id" {
  description = "ID of the storage account private endpoint (queue)"
  value       = azurerm_private_endpoint.pe_storage_queue.id
}

output "pe_storage_table_id" {
  description = "ID of the storage account private endpoint (table)"
  value       = azurerm_private_endpoint.pe_storage_table.id
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
