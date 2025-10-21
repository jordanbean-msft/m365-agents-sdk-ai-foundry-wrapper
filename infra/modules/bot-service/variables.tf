variable "unique_suffix" {
  description = "Unique suffix for resource naming"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources (Note: Bot Service itself uses 'global' location)"
  type        = string
}

variable "container_app_fqdn" {
  description = "FQDN of the Container App that hosts the bot logic"
  type        = string
}

variable "microsoft_app_id" {
  description = "Microsoft App ID (Client ID) for the bot authentication"
  type        = string
}

variable "microsoft_app_password" {
  description = "Microsoft App Password (Client Secret) for the bot authentication"
  type        = string
  sensitive   = true
}

variable "tenant_id" {
  description = "Azure AD tenant ID for SingleTenant bot"
  type        = string
}

variable "sku" {
  description = "SKU for the Bot Service. Valid values: F0 (Free), S1 (Standard)"
  type        = string
  default     = "F0"
  validation {
    condition     = contains(["F0", "S1"], var.sku)
    error_message = "SKU must be either F0 (Free) or S1 (Standard)"
  }
}

variable "enable_webchat" {
  description = "Enable Web Chat channel for testing through Azure Portal"
  type        = bool
  default     = true
}

variable "enable_teams" {
  description = "Enable Microsoft Teams channel for the bot"
  type        = bool
  default     = true
}

variable "enable_m365" {
  description = "Enable M365 channel for the bot"
  type        = bool
  default     = true
}

variable "application_insights_app_id" {
  description = "Application ID (GUID) of Application Insights for bot monitoring (max 50 characters)"
  type        = string
  default     = null
}

variable "application_insights_instrumentation_key" {
  description = "Application Insights instrumentation key (UUID) for bot monitoring"
  type        = string
  default     = null
  sensitive   = true
}

variable "log_analytics_workspace_id" {
  description = "Resource ID of an existing Log Analytics Workspace for diagnostics"
  type        = string
  default     = null
}

variable "enable_diagnostics" {
  description = "Enable diagnostic settings for the Bot Service"
  type        = bool
  default     = true
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
