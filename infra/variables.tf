variable "resource_group_name_resources" {
  description = "The name of the existing resource group to deploy the resources into"
  type        = string
}

variable "subnet_id_agent" {
  description = "The resource id of the subnet that has been delegated to Microsoft.Apps/environments"
  type        = string
}

variable "subnet_id_private_endpoint" {
  description = "The resource id of the subnet that will be used to deploy Private Endpoints to"
  type        = string
}

variable "subnet_id_logic_apps" {
  description = "The resource id of the subnet that will be used for Logic Apps VNet integration"
  type        = string
}

variable "subnet_id_container_apps" {
  description = "The resource id of the subnet that will be used for Container Apps Environment VNet integration"
  type        = string
}

variable "subnet_id_app_gateway" {
  description = "The resource id of the subnet that will be used for Application Gateway deployment"
  type        = string
}

variable "subscription_id_resources" {
  description = "The subscription id where the resources will be deployed"
  type        = string
}

variable "location" {
  description = "The name of the location to provision the resources to"
  type        = string
}

## Container Apps specific variables
variable "service_connection_client_id" {
  description = "Client ID for service connection"
  type        = string
}

variable "service_connection_client_secret" {
  description = "Client secret for service connection"
  type        = string
  sensitive   = true
}

variable "tenant_id" {
  description = "Azure AD tenant ID"
  type        = string
}

variable "ai_foundry_agent_id" {
  description = "AI Foundry agent ID"
  type        = string
}


variable "container_image" {
  description = "Container image to deploy"
  type        = string
  default     = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
}

variable "log_analytics_workspace_id" {
  description = "Resource ID of an existing Log Analytics Workspace to attach supported services to (e.g. /subscriptions/xxxx/resourceGroups/rg/providers/Microsoft.OperationalInsights/workspaces/my-law)"
  type        = string
}

variable "application_insights_id" {
  description = "Resource ID of an existing Application Insights resource to create connections to (optional). Connection string will be fetched automatically. Example: /subscriptions/xxxx/resourceGroups/rg/providers/Microsoft.Insights/components/appinsights"
  type        = string
  default     = null
}

variable "common_tags" {
  description = "A map of tags to apply to all Azure resources (where supported). Provider default tags cover azurerm resources; critical azapi resources are tagged explicitly."
  type        = map(string)
  default     = {}
}

variable "enable_diagnostics" {
  description = "Toggle creation of diagnostic settings across all modules. Set to false to skip until resources exist or categories confirmed."
  type        = bool
  default     = true
}

## Existing NSG resource IDs (module nsgs now references existing NSGs by ID)
variable "nsg_id_agent" {
  description = "Resource ID of existing Network Security Group for agent subnet"
  type        = string
}

variable "nsg_id_private_endpoints" {
  description = "Resource ID of existing Network Security Group for private endpoints subnet"
  type        = string
}

variable "nsg_id_logic_apps" {
  description = "Resource ID of existing Network Security Group for logic apps subnet"
  type        = string
}

variable "nsg_id_container_apps" {
  description = "Resource ID of existing Network Security Group for container apps subnet"
  type        = string
}

variable "nsg_id_app_gateway" {
  description = "Resource ID of existing Network Security Group for application gateway subnet"
  type        = string
}

## Optional Logic Apps settings
variable "logic_apps_website_dns_server" {
  description = "DNS server IP address to set as WEBSITE_DNS_SERVER for the Logic App"
  type        = string
}

## Bot Service variables
variable "bot_messaging_endpoint" {
  description = "Messaging endpoint URL for the bot (e.g., https://example.com/api/messages)"
  type        = string
}

variable "bot_sku" {
  description = "SKU for the Bot Service. Valid values: F0 (Free), S1 (Standard)"
  type        = string
  default     = "F0"
}

variable "enable_bot_webchat" {
  description = "Enable Web Chat channel for testing through Azure Portal"
  type        = bool
  default     = true
}

variable "enable_bot_teams" {
  description = "Enable Microsoft Teams channel for the bot"
  type        = bool
  default     = true
}

variable "enable_bot_m365" {
  description = "Enable M365 channel for the bot"
  type        = bool
  default     = true
}

## Application Gateway certificate variables
variable "pfx_certificate_path" {
  description = "Filesystem path to PFX certificate for uploading to Key Vault. Required to enable HTTPS on Application Gateway."
  type        = string
}

variable "pfx_certificate_password" {
  description = "Password for the PFX certificate at pfx_certificate_path."
  type        = string
  sensitive   = true
}

variable "appgw_certificate_name" {
  description = "Name for the Application Gateway certificate in Key Vault"
  type        = string
  default     = "appgw-cert"
}

## Logging configuration
variable "log_level" {
  description = "Global log level passed to runtime components (e.g. INFO, DEBUG, WARNING)."
  type        = string
  default     = "INFO"
}

variable "reset_command_keywords" {
  description = "Comma-separated list of keywords that trigger conversation reset"
  type        = string
  default     = "reset,restart,new"
}

variable "enable_response_metadata_card" {
  description = "Feature flag to enable the metadata adaptive card with timing/token info (default false)"
  type        = bool
  default     = false
}
