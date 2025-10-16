########## Create Private Endpoints
##########

## Create Private Endpoint for Storage Account
##
resource "azurerm_private_endpoint" "pe_storage" {
  depends_on = [
    var.storage_account_id
  ]

  name                = "${var.storage_account_name}-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id_private_endpoint
  private_service_connection {
    name                           = "${var.storage_account_name}-private-link-service-connection"
    private_connection_resource_id = var.storage_account_id
    subresource_names = [
      "blob"
    ]
    is_manual_connection = false
  }
}

## Create Private Endpoint for Cosmos DB
##
resource "azurerm_private_endpoint" "pe_cosmosdb" {
  depends_on = [
    azurerm_private_endpoint.pe_storage,
    var.cosmosdb_id
  ]

  name                = "${var.cosmosdb_name}-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id_private_endpoint

  private_service_connection {
    name                           = "${var.cosmosdb_name}-private-link-service-connection"
    private_connection_resource_id = var.cosmosdb_id
    subresource_names = [
      "Sql"
    ]
    is_manual_connection = false
  }
}

## Create Private Endpoint for AI Search
##
resource "azurerm_private_endpoint" "pe_aisearch" {
  depends_on = [
    azurerm_private_endpoint.pe_cosmosdb,
    var.ai_search_id
  ]

  name                = "${var.ai_search_name}-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id_private_endpoint

  private_service_connection {
    name                           = "${var.ai_search_name}-private-link-service-connection"
    private_connection_resource_id = var.ai_search_id
    subresource_names = [
      "searchService"
    ]
    is_manual_connection = false
  }
}

## Create Private Endpoint for AI Foundry
##
resource "azurerm_private_endpoint" "pe_aifoundry" {
  depends_on = [
    azurerm_private_endpoint.pe_aisearch,
    var.ai_foundry_id
  ]

  name                = "${var.ai_foundry_name}-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id_private_endpoint

  private_service_connection {
    name                           = "${var.ai_foundry_name}-private-link-service-connection"
    private_connection_resource_id = var.ai_foundry_id
    subresource_names = [
      "account"
    ]
    is_manual_connection = false
  }
}
