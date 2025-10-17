########## Create resources required for agent data storage
##########

## Create a storage account for agent data
##
resource "azurerm_storage_account" "storage_account" {
  name                = "aifoundry${var.unique_suffix}storage"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.common_tags

  account_kind             = "StorageV2"
  account_tier             = "Standard"
  account_replication_type = "LRS"

  ## Identity configuration
  shared_access_key_enabled = false

  ## Network access configuration
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  network_rules {
    default_action = "Deny"
    bypass = [
      "AzureServices"
    ]
  }
}

## Create the Cosmos DB account to store agent threads
##
resource "azurerm_cosmosdb_account" "cosmosdb" {
  name                = "aifoundry${var.unique_suffix}cosmosdb"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.common_tags

  # General settings
  offer_type        = "Standard"
  kind              = "GlobalDocumentDB"
  free_tier_enabled = false

  # Set security-related settings
  local_authentication_disabled = true
  public_network_access_enabled = false

  # Set high availability and failover settings
  automatic_failover_enabled       = false
  multiple_write_locations_enabled = false

  # Configure consistency settings
  consistency_policy {
    consistency_level = "Session"
  }

  # Configure single location with no zone redundancy to reduce costs
  geo_location {
    location          = var.location
    failover_priority = 0
    zone_redundant    = false
  }
}

## Create an AI Search instance that will be used to store vector embeddings
##
resource "azapi_resource" "ai_search" {
  type                      = "Microsoft.Search/searchServices@2025-05-01"
  name                      = "aifoundry${var.unique_suffix}search"
  parent_id                 = "/subscriptions/${var.subscription_id}/resourceGroups/${var.resource_group_name}"
  location                  = var.location
  schema_validation_enabled = true
  tags                      = var.common_tags

  body = {
    sku = {
      name = "standard"
    }

    identity = {
      type = "SystemAssigned"
    }

    properties = {

      # Search-specific properties
      replicaCount   = 1
      partitionCount = 1
      hostingMode    = "default"
      semanticSearch = "disabled"

      # Identity-related controls
      disableLocalAuth = false
      authOptions = {
        aadOrApiKey = {
          aadAuthFailureMode = "http401WithBearerChallenge"
        }
      }
      # Networking-related controls
      publicNetworkAccess = "Disabled"
      networkRuleSet = {
        bypass = "None"
      }
    }
  }
}

## Diagnostic Settings
resource "azurerm_monitor_diagnostic_setting" "storage_account" {
  count                      = var.enable_diagnostics ? 1 : 0
  name                       = "${azurerm_storage_account.storage_account.name}-diag"
  target_resource_id         = azurerm_storage_account.storage_account.id
  log_analytics_workspace_id = var.log_analytics_workspace_id
  # Removed unsupported log categories; keeping metrics only until correct categories confirmed.
  enabled_metric { category = "AllMetrics" }
}

resource "azurerm_monitor_diagnostic_setting" "cosmosdb" {
  count                      = var.enable_diagnostics ? 1 : 0
  name                       = "${azurerm_cosmosdb_account.cosmosdb.name}-diag"
  target_resource_id         = azurerm_cosmosdb_account.cosmosdb.id
  log_analytics_workspace_id = var.log_analytics_workspace_id
  enabled_log { category_group = "allLogs" }
  enabled_metric { category = "AllMetrics" }
}

resource "azurerm_monitor_diagnostic_setting" "ai_search" {
  count                      = var.enable_diagnostics ? 1 : 0
  name                       = "${azapi_resource.ai_search.name}-diag"
  target_resource_id         = azapi_resource.ai_search.id
  log_analytics_workspace_id = var.log_analytics_workspace_id
  enabled_log { category_group = "allLogs" }
  enabled_metric { category = "AllMetrics" }
}
