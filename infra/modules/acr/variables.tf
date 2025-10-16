variable "unique_suffix" {
  description = "Unique suffix for naming (must ensure global uniqueness for ACR)."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "sku" {
  description = "ACR SKU (Basic, Standard, Premium)"
  type        = string
  default     = "Basic"
}

variable "pull_principal_id" {
  description = "Optional principal ID (user-assigned identity) to grant AcrPull role"
  type        = string
  default     = ""
}

variable "subnet_id_private_endpoint" {
  description = "Subnet ID where the private endpoint for ACR will be placed"
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics Workspace resource ID for diagnostics"
  type        = string
}
