variable "unique_suffix" {
  description = "Unique suffix for resource naming"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name for Container Apps resources"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "subnet_id_container_apps" {
  description = "Subnet ID for Container Apps Environment VNet integration"
  type        = string
}

variable "container_image" {
  description = "Container image to deploy (e.g., mcr.microsoft.com/azuredocs/containerapps-helloworld:latest)"
  type        = string
  default     = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
}

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

variable "ai_project_endpoint" {
  description = "AI Foundry project endpoint URL"
  type        = string
}

variable "ai_foundry_agent_id" {
  description = "AI Foundry agent ID"
  type        = string
}

variable "ai_model_deployment_name" {
  description = "AI model deployment name (e.g., gpt-4o)"
  type        = string
  default     = "gpt-4o"
}

variable "azure_client_id" {
  description = "Azure client ID for authentication"
  type        = string
}

variable "registry_server" {
  description = "Container registry server hostname (e.g. myregistry.azurecr.io)"
  type        = string
}

variable "user_assigned_identity_id" {
  description = "Resource ID of the user assigned managed identity used for pulling images"
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Existing Log Analytics Workspace resource ID for diagnostics (optional). If empty, no linkage is configured."
  type        = string
  default     = ""
}

variable "common_tags" {
  description = "Common tags to apply to tag-supporting resources in this module"
  type        = map(string)
  default     = {}
}

variable "enable_diagnostics" {
  description = "Enable diagnostic settings creation for container app resources"
  type        = bool
  default     = true
}

variable "application_insights_connection_string" {
  description = "Application Insights connection string for Container Apps monitoring (optional)"
  type        = string
  default     = null
  sensitive   = true
}
