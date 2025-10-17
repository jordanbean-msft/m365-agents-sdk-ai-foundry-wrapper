variable "unique_suffix" {
  description = "Unique suffix for resource naming"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name for project resources"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "ai_foundry_id" {
  description = "ID of the AI Foundry resource"
  type        = string
}

variable "storage_account_id" {
  description = "ID of the storage account"
  type        = string
}

variable "storage_account_name" {
  description = "Name of the storage account"
  type        = string
}

variable "storage_account_primary_blob_endpoint" {
  description = "Primary blob endpoint of the storage account"
  type        = string
}

variable "cosmosdb_id" {
  description = "ID of the Cosmos DB account"
  type        = string
}

variable "cosmosdb_name" {
  description = "Name of the Cosmos DB account"
  type        = string
}

variable "cosmosdb_endpoint" {
  description = "Endpoint of the Cosmos DB account"
  type        = string
}

variable "ai_search_id" {
  description = "ID of the AI Search service"
  type        = string
}

variable "ai_search_name" {
  description = "Name of the AI Search service"
  type        = string
}

variable "pe_storage_id" {
  description = "ID of the storage account private endpoint"
  type        = string
}

variable "pe_cosmosdb_id" {
  description = "ID of the Cosmos DB private endpoint"
  type        = string
}

variable "pe_aisearch_id" {
  description = "ID of the AI Search private endpoint"
  type        = string
}

variable "pe_aifoundry_id" {
  description = "ID of the AI Foundry private endpoint"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to tag-supporting resources in this module"
  type        = map(string)
  default     = {}
}
