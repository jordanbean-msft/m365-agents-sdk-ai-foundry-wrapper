########## Create Azure Key Vault resources
##########

## Create Azure Key Vault for storing secrets
##
resource "azurerm_key_vault" "main" {
  name                = "kv-${var.unique_suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tenant_id           = var.tenant_id
  sku_name            = "standard"

  ## Network configuration
  public_network_access_enabled = false
  network_acls {
    bypass         = "AzureServices"
    default_action = "Deny"
  }

  ## RBAC authorization model (not access policies)
  rbac_authorization_enabled = true

  ## Soft delete and purge protection
  soft_delete_retention_days = 7
  purge_protection_enabled   = true

  tags = var.common_tags
}

## Private endpoint for Key Vault
##
resource "azurerm_private_endpoint" "kv" {
  name                = "pe-kv-${var.unique_suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.subnet_id_private_endpoint

  private_service_connection {
    name                           = "psc-kv-${var.unique_suffix}"
    private_connection_resource_id = azurerm_key_vault.main.id
    is_manual_connection           = false
    subresource_names              = ["vault"]
  }

  tags = var.common_tags

  lifecycle {
    ignore_changes = [
      private_dns_zone_group
    ]
  }
}

## Diagnostic settings for Key Vault
## Note: Resource always created but skipped internally if log_analytics_workspace_id is null or diagnostics disabled
##
resource "azurerm_monitor_diagnostic_setting" "kv" {
  count                      = var.enable_diagnostics && var.log_analytics_workspace_id != null && var.log_analytics_workspace_id != "" ? 1 : 0
  name                       = "${azurerm_key_vault.main.name}-diag"
  target_resource_id         = azurerm_key_vault.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "AuditEvent"
  }

  enabled_log {
    category = "AzurePolicyEvaluationDetails"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
