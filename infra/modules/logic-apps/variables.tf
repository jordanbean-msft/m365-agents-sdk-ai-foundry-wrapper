variable "unique_suffix" {
  description = "Unique suffix for resource naming"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name for Logic Apps resources"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "subnet_id_logic_apps" {
  description = "Subnet ID for Logic Apps VNet integration"
  type        = string
}

variable "subnet_id_private_endpoint" {
  description = "Subnet ID for private endpoints"
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
  description = "Enable diagnostic settings creation for Logic Apps resources"
  type        = bool
  default     = true
}

variable "user_assigned_identity_id" {
  description = "Resource ID of the user-assigned managed identity for Logic Apps"
  type        = string
}

variable "user_assigned_identity_principal_id" {
  description = "Principal ID of the user-assigned managed identity (for role assignments)"
  type        = string
}

variable "website_dns_server" {
  description = "DNS server IP address for WEBSITE_DNS_SERVER app setting."
  type        = string
}
