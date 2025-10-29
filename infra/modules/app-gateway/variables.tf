variable "unique_suffix" {
  description = "Unique suffix for resource naming"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "subnet_id_app_gateway" {
  description = "Resource ID of the subnet for Application Gateway"
  type        = string
}

variable "container_app_fqdn" {
  description = "FQDN of the Container App backend"
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Resource ID of Log Analytics workspace for diagnostics"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "enable_diagnostics" {
  description = "Enable diagnostic settings"
  type        = bool
  default     = true
}

variable "key_vault_certificate_secret_id" {
  description = "Key Vault secret ID for the Application Gateway SSL certificate (e.g., https://kv-xxx.vault.azure.net/secrets/appgw-cert/xxx)."
  type        = string
  sensitive   = true
}

variable "user_assigned_identity_id" {
  description = "Resource ID of the user-assigned managed identity for Application Gateway"
  type        = string
}

variable "user_assigned_identity_principal_id" {
  description = "Principal ID of the user-assigned managed identity for Application Gateway"
  type        = string
}
