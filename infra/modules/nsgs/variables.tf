variable "unique_suffix" {
  description = "Unique suffix used for naming resources"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group where NSGs will be created"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "subnet_id_agent" {
  description = "Existing subnet ID for AI Foundry agent subnet"
  type        = string
}

variable "subnet_id_private_endpoint" {
  description = "Existing subnet ID for Private Endpoints"
  type        = string
}

variable "subnet_id_logic_apps" {
  description = "Existing subnet ID for Logic Apps VNet Integration"
  type        = string
}

variable "subnet_id_container_apps" {
  description = "Existing subnet ID for Container Apps Environment"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to NSG resources"
  type        = map(string)
  default     = {}
}

## Existing NSG resource IDs (module references existing NSGs by full resource ID)
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
