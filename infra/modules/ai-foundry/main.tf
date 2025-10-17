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
    capacity = 1
  }

  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-11-20"
  }
}

## Diagnostic Settings for AI Foundry (Cognitive Services Account)
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
