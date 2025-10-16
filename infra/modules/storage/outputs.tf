output "storage_account_id" {
  description = "ID of the storage account"
  value       = azurerm_storage_account.storage_account.id
}

output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.storage_account.name
}

output "storage_account_primary_blob_endpoint" {
  description = "Primary blob endpoint of the storage account"
  value       = azurerm_storage_account.storage_account.primary_blob_endpoint
}

output "cosmosdb_id" {
  description = "ID of the Cosmos DB account"
  value       = azurerm_cosmosdb_account.cosmosdb.id
}

output "cosmosdb_name" {
  description = "Name of the Cosmos DB account"
  value       = azurerm_cosmosdb_account.cosmosdb.name
}

output "cosmosdb_endpoint" {
  description = "Endpoint of the Cosmos DB account"
  value       = azurerm_cosmosdb_account.cosmosdb.endpoint
}

output "ai_search_id" {
  description = "ID of the AI Search service"
  value       = azapi_resource.ai_search.id
}

output "ai_search_name" {
  description = "Name of the AI Search service"
  value       = azapi_resource.ai_search.name
}
