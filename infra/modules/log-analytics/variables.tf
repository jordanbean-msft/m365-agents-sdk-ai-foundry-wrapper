variable "existing_workspace_id" {
  description = "(Optional) Resource ID of an existing Log Analytics workspace. If provided, no new workspace is created."
  type        = string
  default     = null
}

variable "name" {
  description = "Name of the Log Analytics workspace to create (ignored if existing_workspace_id is set)"
  type        = string
}

variable "location" {
  description = "Azure region for the workspace"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group in which to create the workspace"
  type        = string
}

variable "retention_in_days" {
  description = "Retention period for logs"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Tags to apply to the workspace"
  type        = map(string)
  default     = {}
}
