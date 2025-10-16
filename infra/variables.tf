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
