########## Create AI Foundry resource
##########

## Create the AI Foundry resource
##
resource "azapi_resource" "ai_foundry" {
  type                      = "Microsoft.CognitiveServices/accounts@2025-06-01"
  name                      = "aifoundry${var.unique_suffix}"
  parent_id                 = "/subscriptions/${var.subscription_id}/resourceGroups/${var.resource_group_name}"
  location                  = var.location
  schema_validation_enabled = false
  tags                      = var.common_tags

  body = {
    kind = "AIServices",
    sku = {
      name = "S0"
    }
    identity = {
      type = "SystemAssigned"
    }

    properties = {
      # Support both Entra ID and API Key authentication for underlining Cognitive Services account
      disableLocalAuth = false

      # Specifies that this is an AI Foundry resource
      allowProjectManagement = true

      # Set custom subdomain name for DNS names created for this Foundry resource
      customSubDomainName = "aifoundry${var.unique_suffix}"

      # Network-related controls
      # Disable public access but allow Trusted Azure Services exception
      publicNetworkAccess = "Disabled"
      networkAcls = {
        defaultAction = "Allow"
      }

      # Enable VNet injection for Standard Agents
      networkInjections = [
        {
          scenario                   = "agent"
          subnetArmId                = var.subnet_id_agent
          useMicrosoftManagedNetwork = false
        }
      ]
    }
  }
}

## Create a deployment for OpenAI's GPT-4o in the AI Foundry resource
##
resource "azurerm_cognitive_deployment" "aifoundry_deployment_gpt_4o" {
  depends_on = [
    azapi_resource.ai_foundry
  ]

  name                 = "gpt-4o"
  cognitive_account_id = azapi_resource.ai_foundry.id

  sku {
    name     = "GlobalStandard"
    capacity = 100
  }

  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-11-20"
  }
}

## Create the AI Foundry account-level connection to Application Insights (if provided)
## Note: Resource always created but skipped internally if application_insights_id is null
##
resource "azapi_resource" "conn_app_insights" {
  count                     = var.application_insights_id != null && var.application_insights_id != "" ? 1 : 0
  type                      = "Microsoft.CognitiveServices/accounts/connections@2025-06-01"
  name                      = element(split("/", var.application_insights_id), length(split("/", var.application_insights_id)) - 1)
  parent_id                 = azapi_resource.ai_foundry.id
  schema_validation_enabled = false

  depends_on = [
    azapi_resource.ai_foundry
  ]

  body = {
    name = element(split("/", var.application_insights_id), length(split("/", var.application_insights_id)) - 1)
    properties = {
      category = "AppInsights"
      target   = var.application_insights_id
      authType = "ApiKey"
      credentials = {
        key = var.application_insights_connection_string
      }
      metadata = {
        ResourceId = var.application_insights_id
        location   = var.location
      }
    }
  }
}

## Diagnostic Settings for AI Foundry (Cognitive Services Account)
## Note: Diagnostic settings send logs to Log Analytics/Application Insights.
## Application Insights connections (above) are separate and integrate AI Foundry with App Insights for tracing.
resource "azurerm_monitor_diagnostic_setting" "ai_foundry" {
  count                      = var.enable_diagnostics ? 1 : 0
  name                       = "${azapi_resource.ai_foundry.name}-diag"
  target_resource_id         = azapi_resource.ai_foundry.id
  log_analytics_workspace_id = var.log_analytics_workspace_id
  enabled_log {
    category_group = "allLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
