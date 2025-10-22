########## Create Azure Bot Service resources
##########

## Create Azure Bot Service channel registration
## This bot connects to the Container App endpoint
##
resource "azurerm_bot_service_azure_bot" "main" {
  name                    = "bot-aif-${var.unique_suffix}"
  resource_group_name     = var.resource_group_name
  location                = "global" # Bot Service uses global location
  sku                     = var.sku
  microsoft_app_id        = var.microsoft_app_id
  microsoft_app_type      = "SingleTenant"
  microsoft_app_tenant_id = var.tenant_id

  ## Messaging endpoint from configuration
  endpoint = var.bot_messaging_endpoint

  ## Streaming messaging endpoint
  streaming_endpoint_enabled = true

  ## Application Insights integration
  developer_app_insights_application_id = var.application_insights_app_id
  developer_app_insights_key            = var.application_insights_instrumentation_key

  tags = var.common_tags
}

## Create Microsoft Teams channel
## Enables the bot to be accessed through Microsoft Teams
##
resource "azurerm_bot_channel_ms_teams" "main" {
  count               = var.enable_teams ? 1 : 0
  bot_name            = azurerm_bot_service_azure_bot.main.name
  resource_group_name = var.resource_group_name
  location            = azurerm_bot_service_azure_bot.main.location

  ## Calling disabled per requirements
  enable_calling = false

  depends_on = [
    azurerm_bot_service_azure_bot.main
  ]
}

## Create M365 Extensions channel
## Enables the bot to be accessed through M365 applications
##
resource "azurerm_bot_channel_directline" "m365" {
  count               = var.enable_m365 ? 1 : 0
  bot_name            = azurerm_bot_service_azure_bot.main.name
  resource_group_name = var.resource_group_name
  location            = azurerm_bot_service_azure_bot.main.location

  site {
    name    = "M365Extensions"
    enabled = true
  }

  depends_on = [
    azurerm_bot_service_azure_bot.main
  ]
}

## Create Web Chat channel (optional)
## Enables testing the bot through Azure Portal
##
resource "azurerm_bot_channel_web_chat" "main" {
  count               = var.enable_webchat ? 1 : 0
  bot_name            = azurerm_bot_service_azure_bot.main.name
  resource_group_name = var.resource_group_name
  location            = azurerm_bot_service_azure_bot.main.location

  depends_on = [
    azurerm_bot_service_azure_bot.main
  ]
}

## OAuth Connection Settings
## Configures Azure AD v2 authentication for the bot
##
resource "azurerm_bot_connection" "oauth" {
  name                  = "oauth-${var.unique_suffix}"
  bot_name              = azurerm_bot_service_azure_bot.main.name
  resource_group_name   = var.resource_group_name
  location              = azurerm_bot_service_azure_bot.main.location
  service_provider_name = "Aadv2"
  client_id             = var.microsoft_app_id
  client_secret         = var.microsoft_app_password
  scopes                = "User.Read"

  parameters = {
    tenantId         = var.tenant_id
    tokenExchangeUrl = ""
  }

  depends_on = [
    azurerm_bot_service_azure_bot.main
  ]
}

## Diagnostic Settings for Bot Service
##
resource "azurerm_monitor_diagnostic_setting" "bot" {
  count                      = var.enable_diagnostics ? 1 : 0
  name                       = "${azurerm_bot_service_azure_bot.main.name}-diag"
  target_resource_id         = azurerm_bot_service_azure_bot.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "BotRequest"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
