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

## Create Private Endpoint for Logic Apps Storage Account (blob)
## Created before file share to establish network connectivity
##
resource "azurerm_private_endpoint" "pe_logic_apps_storage_blob" {
  depends_on = [
    azurerm_storage_account.logic_apps_storage
  ]

  name                = "${azurerm_storage_account.logic_apps_storage.name}-blob-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id_private_endpoint

  private_service_connection {
    name                           = "${azurerm_storage_account.logic_apps_storage.name}-blob-private-link-service-connection"
    private_connection_resource_id = azurerm_storage_account.logic_apps_storage.id
    subresource_names = [
      "blob"
    ]
    is_manual_connection = false
  }
  tags = var.common_tags

  lifecycle {
    ignore_changes = [
      private_dns_zone_group
    ]
  }
}

## Create Private Endpoint for Logic Apps Storage Account (file)
## Created before file share to establish network connectivity
##
resource "azurerm_private_endpoint" "pe_logic_apps_storage_file" {
  depends_on = [
    azurerm_storage_account.logic_apps_storage
  ]

  name                = "${azurerm_storage_account.logic_apps_storage.name}-file-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id_private_endpoint

  private_service_connection {
    name                           = "${azurerm_storage_account.logic_apps_storage.name}-file-private-link-service-connection"
    private_connection_resource_id = azurerm_storage_account.logic_apps_storage.id
    subresource_names = [
      "file"
    ]
    is_manual_connection = false
  }
  tags = var.common_tags

  lifecycle {
    ignore_changes = [
      private_dns_zone_group
    ]
  }
}

## Create Private Endpoint for Logic Apps Storage Account (queue)
## Created before file share to establish network connectivity
##
resource "azurerm_private_endpoint" "pe_logic_apps_storage_queue" {
  depends_on = [
    azurerm_storage_account.logic_apps_storage
  ]

  name                = "${azurerm_storage_account.logic_apps_storage.name}-queue-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id_private_endpoint

  private_service_connection {
    name                           = "${azurerm_storage_account.logic_apps_storage.name}-queue-private-link-service-connection"
    private_connection_resource_id = azurerm_storage_account.logic_apps_storage.id
    subresource_names = [
      "queue"
    ]
    is_manual_connection = false
  }
  tags = var.common_tags

  lifecycle {
    ignore_changes = [
      private_dns_zone_group
    ]
  }
}

## Create Private Endpoint for Logic Apps Storage Account (table)
## Created before file share to establish network connectivity
##
resource "azurerm_private_endpoint" "pe_logic_apps_storage_table" {
  depends_on = [
    azurerm_storage_account.logic_apps_storage
  ]

  name                = "${azurerm_storage_account.logic_apps_storage.name}-table-private-endpoint"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id_private_endpoint

  private_service_connection {
    name                           = "${azurerm_storage_account.logic_apps_storage.name}-table-private-link-service-connection"
    private_connection_resource_id = azurerm_storage_account.logic_apps_storage.id
    subresource_names = [
      "table"
    ]
    is_manual_connection = false
  }
  tags = var.common_tags

  lifecycle {
    ignore_changes = [
      private_dns_zone_group
    ]
  }
}

## Create file share for Logic Apps content
## Created after private endpoints to ensure network access
##
resource "azurerm_storage_share" "logic_apps_content" {
  name                 = "logic-apps-content-${var.unique_suffix}"
  storage_account_name = azurerm_storage_account.logic_apps_storage.name
  quota                = 5120 # 5 TB max for Standard tier

  depends_on = [
    azurerm_private_endpoint.pe_logic_apps_storage_blob,
    azurerm_private_endpoint.pe_logic_apps_storage_file,
    azurerm_private_endpoint.pe_logic_apps_storage_queue,
    azurerm_private_endpoint.pe_logic_apps_storage_table
  ]
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

  depends_on = [
    azurerm_storage_share.logic_apps_content,
    azurerm_private_endpoint.pe_logic_apps_storage_file
  ]

  ## Enable user-assigned managed identity
  identity {
    type = "UserAssigned"
    identity_ids = [
      var.user_assigned_identity_id
    ]
  }

  ## VNet integration
  virtual_network_subnet_id = var.subnet_id_logic_apps

  ## Disable public network access
  public_network_access = "Disabled"

  ## App settings
  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME"                 = "dotnet"
    "WEBSITE_NODE_DEFAULT_VERSION"             = "~22"
    "WEBSITE_CONTENTOVERVNET"                  = "1"
    "WEBSITE_CONTENTAZUREFILECONNECTIONSTRING" = "DefaultEndpointsProtocol=https;AccountName=${azurerm_storage_account.logic_apps_storage.name};AccountKey=${azurerm_storage_account.logic_apps_storage.primary_access_key};EndpointSuffix=core.windows.net"
    "WEBSITE_CONTENTSHARE"                     = azurerm_storage_share.logic_apps_content.name
    "AzureWebJobsStorage"                      = "DefaultEndpointsProtocol=https;AccountName=${azurerm_storage_account.logic_apps_storage.name};AccountKey=${azurerm_storage_account.logic_apps_storage.primary_access_key};EndpointSuffix=core.windows.net"
    "WEBSITE_AUTH_AAD_ALLOWED_TENANTS"         = "*"
    "WEBSITE_AUTH_AAD_REQUIRE_HTTPS"           = "true"
    "WEBSITE_DNS_SERVER"                       = var.website_dns_server
    "WEBSITE_VNET_ROUTE_ALL"                   = "1"
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

  lifecycle {
    ignore_changes = [
      private_dns_zone_group
    ]
  }
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

## Grant the user-assigned managed identity access to invoke the Logic App
## Logic App Contributor allows managing workflows and invoking them
resource "azurerm_role_assignment" "uami_logic_app_contributor" {
  scope                = azurerm_logic_app_standard.logic_app.id
  role_definition_name = "Logic App Contributor"
  principal_id         = var.user_assigned_identity_principal_id
}
