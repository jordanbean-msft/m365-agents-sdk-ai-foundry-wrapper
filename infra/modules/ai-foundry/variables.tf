variable "unique_suffix" {
  description = "Unique suffix for resource naming"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name for AI Foundry resources"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "subscription_id" {
  description = "Subscription ID for resources"
  type        = string
}

variable "subnet_id_agent" {
  description = "Subnet ID for agent VNet injection"
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics Workspace resource ID for diagnostics"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to tag-supporting resources in this module"
  type        = map(string)
  default     = {}
}

variable "enable_diagnostics" {
  description = "Enable diagnostic settings creation for AI Foundry resource"
  type        = bool
  default     = true
}
