########## Create Azure Container Apps resources
##########

## Create Container App Environment with VNet integration
##
resource "azurerm_container_app_environment" "main" {
  name                = "cae-${var.unique_suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  # Link to existing Log Analytics workspace when provided
  log_analytics_workspace_id = var.log_analytics_workspace_id

  ## VNet integration using workload profile
  infrastructure_subnet_id       = var.subnet_id_container_apps
  internal_load_balancer_enabled = true

  ## Workload profile for VNet integration
  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
  tags = var.common_tags

  lifecycle {
    ignore_changes = [
      infrastructure_resource_group_name
    ]
  }
}

## Create Container App with managed identity
##
resource "azurerm_container_app" "main" {
  name                         = "ca-${var.unique_suffix}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  ## Use workload profile
  workload_profile_name = "Consumption"

  ## User-assigned managed identity only (system-assigned removed per requirement)
  identity {
    type         = "UserAssigned"
    identity_ids = [var.user_assigned_identity_id]
  }

  ## Container template
  template {
    container {
      name  = "main"
      image = var.container_image
      # Updated per request: allocate 1 vCPU. Adjust memory to a valid pairing for 1 vCPU.
      cpu    = 1.0
      memory = "2Gi"

      ## Environment variables
      env {
        name  = "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID"
        value = var.service_connection_client_id
      }

      env {
        name        = "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET"
        secret_name = "service-connection-client-secret"
      }

      env {
        name  = "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID"
        value = var.tenant_id
      }

      env {
        name  = "AZURE_AI_PROJECT_ENDPOINT"
        value = var.ai_project_endpoint
      }

      env {
        name  = "AZURE_AI_FOUNDRY_AGENT_ID"
        value = var.ai_foundry_agent_id
      }

      env {
        name  = "AZURE_AI_MODEL_DEPLOYMENT_NAME"
        value = var.ai_model_deployment_name
      }

      env {
        name  = "AZURE_CLIENT_ID"
        value = var.azure_client_id
      }

      ## Logging & runtime controls
      env {
        name  = "LOG_LEVEL"
        value = var.log_level
      }

      env {
        name  = "PYTHONUNBUFFERED"
        value = "1"
      }

      env {
        name  = "CONVERSATION_TIMEOUT_SECONDS"
        value = tostring(var.conversation_timeout_seconds)
      }

      env {
        name  = "RESET_COMMAND_KEYWORDS"
        value = var.reset_command_keywords
      }

      dynamic "env" {
        for_each = var.application_insights_connection_string != null ? [1] : []
        content {
          name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
          value = var.application_insights_connection_string
        }
      }
    }

    min_replicas = 1
    max_replicas = 10
  }

  ## Secret configuration - Reference Key Vault secret
  secret {
    name                = "service-connection-client-secret"
    key_vault_secret_id = "${var.key_vault_uri}secrets/service-connection-client-secret"
    identity            = var.user_assigned_identity_id
  }

  ## Ingress configuration - Internal only, exposed via Application Gateway
  ingress {
    external_enabled = true
    target_port      = 3978
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  ## Private registry configuration using user assigned identity
  registry {
    server   = var.registry_server
    identity = var.user_assigned_identity_id
  }
  tags = var.common_tags
}

## Diagnostic Settings for Container App (console & system logs)
# resource "azurerm_monitor_diagnostic_setting" "container_app_logs" {
#   count                      = var.enable_diagnostics ? 1 : 0
#   name                       = "${azurerm_container_app.main.name}-logs"
#   target_resource_id         = azurerm_container_app.main.id
#   log_analytics_workspace_id = var.log_analytics_workspace_id

#   enabled_log { category = "ContainerAppConsoleLogs" }
#   enabled_log { category = "ContainerAppSystemLogs" }
#   enabled_metric { category = "AllMetrics" }
# }

## Diagnostic Settings for Container App Environment
resource "azurerm_monitor_diagnostic_setting" "container_app_env" {
  count                      = var.enable_diagnostics ? 1 : 0
  name                       = "${azurerm_container_app_environment.main.name}-diag"
  target_resource_id         = azurerm_container_app_environment.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id
  enabled_log { category_group = "allLogs" }
  enabled_metric { category = "AllMetrics" }
}

## Private Endpoint for Container App Environment
resource "azurerm_private_endpoint" "container_app_env" {
  name                = "pe-cae-${var.unique_suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id_private_endpoint

  private_service_connection {
    name                           = "pe-connection-cae-${var.unique_suffix}"
    private_connection_resource_id = azurerm_container_app_environment.main.id
    is_manual_connection           = false
    subresource_names              = ["managedEnvironments"]
  }

  lifecycle {
    ignore_changes = [
      private_dns_zone_group
    ]
  }

  tags = var.common_tags
}
