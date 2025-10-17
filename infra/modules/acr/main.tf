########## Azure Container Registry Module ##########

resource "azurerm_container_registry" "main" {
  name                          = "acr${var.unique_suffix}"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  sku                           = var.sku
  admin_enabled                 = false
  anonymous_pull_enabled        = false
  data_endpoint_enabled         = false
  public_network_access_enabled = false
  zone_redundancy_enabled       = false
  tags                          = var.common_tags
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = var.pull_principal_id
  depends_on           = [azurerm_container_registry.main]
}

## Private Endpoint for ACR (registry)
resource "azurerm_private_endpoint" "acr" {
  name                = "pe-acr-${var.unique_suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id_private_endpoint
  tags                = var.common_tags

  private_service_connection {
    name                           = "acr-psc-${var.unique_suffix}"
    private_connection_resource_id = azurerm_container_registry.main.id
    is_manual_connection           = false
    subresource_names              = ["registry"]
  }
}

## Diagnostic Settings for ACR
resource "azurerm_monitor_diagnostic_setting" "acr" {
  count                      = var.enable_diagnostics ? 1 : 0
  name                       = "${azurerm_container_registry.main.name}-diag"
  target_resource_id         = azurerm_container_registry.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id
  enabled_log { category_group = "allLogs" }
  enabled_metric { category = "AllMetrics" }
}
