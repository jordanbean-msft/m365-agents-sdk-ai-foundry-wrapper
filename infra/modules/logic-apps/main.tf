########## Create Logic Apps Standard resources
##########

## Create a storage account for Logic Apps Standard
##
resource "azurerm_storage_account" "logic_apps_storage" {
  name                = "logicapps${var.unique_suffix}st"
  resource_group_name = var.resource_group_name
  location            = var.location

  account_kind             = "StorageV2"
  account_tier             = "Standard"
  account_replication_type = "LRS"

  ## Identity configuration
  shared_access_key_enabled = true # Required for Logic Apps Standard

  ## Network access configuration
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  network_rules {
    default_action = "Deny"
    bypass = [
      "AzureServices"
    ]
  }
  tags = var.common_tags
}

## Create App Service Plan for Logic Apps Standard
##
resource "azurerm_service_plan" "logic_apps_plan" {
  name                = "asp-logicapps-${var.unique_suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Windows"
  sku_name            = "WS1"
  tags                = var.common_tags
}

## Create Logic App Standard (Workflow)
##
resource "azurerm_logic_app_standard" "logic_app" {
  name                       = "logic-${var.unique_suffix}"
  resource_group_name        = var.resource_group_name
  location                   = var.location
  app_service_plan_id        = azurerm_service_plan.logic_apps_plan.id
  storage_account_name       = azurerm_storage_account.logic_apps_storage.name
  storage_account_access_key = azurerm_storage_account.logic_apps_storage.primary_access_key

  ## Enable system-assigned managed identity
  identity {
    type = "SystemAssigned"
  }

  ## VNet integration
  virtual_network_subnet_id = var.subnet_id_logic_apps

  ## Disable public network access
  public_network_access = "Disabled"

  ## App settings
  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"     = "node"
    "WEBSITE_NODE_DEFAULT_VERSION" = "~18"
    "WEBSITE_CONTENTOVERVNET"      = "1"
  }

  ## Site configuration
  site_config {
    dotnet_framework_version = "v6.0"
    ftps_state               = "FtpsOnly"
    min_tls_version          = "1.2"

    ## Enable VNet route all
    vnet_route_all_enabled = true
  }
  tags = var.common_tags
}

## Create Private Endpoint for Logic Apps Storage Account
##
resource "azurerm_private_endpoint" "pe_logic_apps_storage" {
  depends_on = [
    azurerm_storage_account.logic_apps_storage
  ]

  name                = "${azurerm_storage_account.logic_apps_storage.name}-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id_private_endpoint

  private_service_connection {
    name                           = "${azurerm_storage_account.logic_apps_storage.name}-private-link-service-connection"
    private_connection_resource_id = azurerm_storage_account.logic_apps_storage.id
    subresource_names = [
      "blob"
    ]
    is_manual_connection = false
  }
  tags = var.common_tags
}

## Create Private Endpoint for Logic Apps (sites)
##
resource "azurerm_private_endpoint" "pe_logic_app" {
  depends_on = [
    azurerm_logic_app_standard.logic_app
  ]

  name                = "${azurerm_logic_app_standard.logic_app.name}-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id_private_endpoint

  private_service_connection {
    name                           = "${azurerm_logic_app_standard.logic_app.name}-private-link-service-connection"
    private_connection_resource_id = azurerm_logic_app_standard.logic_app.id
    subresource_names = [
      "sites"
    ]
    is_manual_connection = false
  }
  tags = var.common_tags
}

## Diagnostic Settings for Logic Apps Storage Account
resource "azurerm_monitor_diagnostic_setting" "logicapps_storage" {
  count                      = var.enable_diagnostics ? 1 : 0
  name                       = "${azurerm_storage_account.logic_apps_storage.name}-diag"
  target_resource_id         = azurerm_storage_account.logic_apps_storage.id
  log_analytics_workspace_id = var.log_analytics_workspace_id
  # Removed unsupported log categories; metrics only until valid categories confirmed.
  enabled_metric { category = "AllMetrics" }
}

## Diagnostic Settings for Logic App Standard
resource "azurerm_monitor_diagnostic_setting" "logic_app" {
  count                      = var.enable_diagnostics ? 1 : 0
  name                       = "${azurerm_logic_app_standard.logic_app.name}-diag"
  target_resource_id         = azurerm_logic_app_standard.logic_app.id
  log_analytics_workspace_id = var.log_analytics_workspace_id
  enabled_log { category_group = "allLogs" }
  enabled_metric { category = "AllMetrics" }
}
