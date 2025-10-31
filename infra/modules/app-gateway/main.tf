########## Azure Application Gateway for M365 Agents Container App
##########

## Public IP for Application Gateway
##
resource "azurerm_public_ip" "main" {
  name                = "pip-appgw-${var.unique_suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.common_tags
}

## Application Gateway
##
resource "azurerm_application_gateway" "main" {
  name                = "appgw-${var.unique_suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.common_tags

  # Temporary workaround: ignore ssl_certificate changes to avoid azurerm provider
  # inconsistency bug when Key Vault certificate versions rotate mid-apply.
  # Remove this lifecycle block once provider bug is resolved and a stable
  # apply succeeds without errors.
  lifecycle {
    ignore_changes = [
      ssl_certificate
    ]
  }

  sku {
    name     = "WAF_v2"
    tier     = "WAF_v2"
    capacity = 1
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [var.user_assigned_identity_id]
  }

  waf_configuration {
    enabled          = true
    firewall_mode    = "Detection"
    rule_set_type    = "OWASP"
    rule_set_version = "3.2"
  }

  gateway_ip_configuration {
    name      = "gateway-ip-config"
    subnet_id = var.subnet_id_app_gateway
  }

  frontend_port {
    name = "http-port"
    port = 80
  }

  frontend_port {
    name = "https-port"
    port = 443
  }

  frontend_ip_configuration {
    name                 = "public-frontend"
    public_ip_address_id = azurerm_public_ip.main.id
  }

  backend_address_pool {
    name  = "container-app-backend"
    fqdns = [var.container_app_fqdn]
  }

  backend_http_settings {
    name                                = "http-settings"
    cookie_based_affinity               = "Disabled"
    port                                = 443
    protocol                            = "Https"
    request_timeout                     = 60
    pick_host_name_from_backend_address = true
    probe_name                          = "health-probe"
  }

  http_listener {
    name                           = "http-listener"
    frontend_ip_configuration_name = "public-frontend"
    frontend_port_name             = "http-port"
    protocol                       = "Http"
  }

  ssl_certificate {
    name                = "kv-cert"
    key_vault_secret_id = var.key_vault_certificate_secret_id
  }

  http_listener {
    name                           = "https-listener"
    frontend_ip_configuration_name = "public-frontend"
    frontend_port_name             = "https-port"
    protocol                       = "Https"
    ssl_certificate_name           = "kv-cert"
  }

  request_routing_rule {
    name                       = "routing-rule"
    rule_type                  = "Basic"
    http_listener_name         = "http-listener"
    backend_address_pool_name  = "container-app-backend"
    backend_http_settings_name = "http-settings"
    priority                   = 100
  }

  request_routing_rule {
    name                       = "routing-rule-https"
    rule_type                  = "Basic"
    http_listener_name         = "https-listener"
    backend_address_pool_name  = "container-app-backend"
    backend_http_settings_name = "http-settings"
    priority                   = 110
  }

  probe {
    name                                      = "health-probe"
    protocol                                  = "Https"
    path                                      = "/healthz"
    interval                                  = 30
    timeout                                   = 30
    unhealthy_threshold                       = 3
    pick_host_name_from_backend_http_settings = true
    # Expect HTTP 200 JSON from /healthz without auth
    match {
      status_code = [200]
    }
  }
}

## Diagnostic Settings for Application Gateway
resource "azurerm_monitor_diagnostic_setting" "app_gateway" {
  count                      = var.enable_diagnostics ? 1 : 0
  name                       = "${azurerm_application_gateway.main.name}-diag"
  target_resource_id         = azurerm_application_gateway.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id
  enabled_log { category_group = "allLogs" }
  enabled_metric { category = "AllMetrics" }
}
