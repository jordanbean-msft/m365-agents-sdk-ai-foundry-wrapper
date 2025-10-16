variable "resource_group_name" {
  description = "Resource group name for private endpoints"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "subnet_id_private_endpoint" {
  description = "Subnet ID for private endpoints"
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

variable "cosmosdb_id" {
  description = "ID of the Cosmos DB account"
  type        = string
}

variable "cosmosdb_name" {
  description = "Name of the Cosmos DB account"
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

variable "ai_foundry_id" {
  description = "ID of the AI Foundry resource"
  type        = string
}

variable "ai_foundry_name" {
  description = "Name of the AI Foundry resource"
  type        = string
}
