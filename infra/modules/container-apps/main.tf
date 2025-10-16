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
    }

    min_replicas = 1
    max_replicas = 10
  }

  ## Secret configuration
  secret {
    name  = "service-connection-client-secret"
    value = var.service_connection_client_secret
  }

  ## Ingress configuration (optional - can be disabled if not needed)
  ingress {
    external_enabled = true
    target_port      = 80
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
}

## Diagnostic Settings for Container App Environment
resource "azurerm_monitor_diagnostic_setting" "container_app_env" {
  name                       = "${azurerm_container_app_environment.main.name}-diag"
  target_resource_id         = azurerm_container_app_environment.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id
  enabled_log {
    category_group = "allLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

## Diagnostic Settings for Container App
resource "azurerm_monitor_diagnostic_setting" "container_app" {
  name                       = "${azurerm_container_app.main.name}-diag"
  target_resource_id         = azurerm_container_app.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id
  enabled_log {
    category_group = "allLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
