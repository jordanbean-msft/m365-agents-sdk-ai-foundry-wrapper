variable "existing_application_insights_id" {
  description = "(Optional) Resource ID of an existing Application Insights component. If provided, no new component is created."
  type        = string
  default     = null
}

variable "name" {
  description = "Name of the Application Insights component to create (ignored if existing_application_insights_id is set)"
  type        = string
}

variable "location" {
  description = "Azure region for the component"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group in which to create the component"
  type        = string
}

variable "workspace_id" {
  description = "(Optional) Log Analytics workspace ID for linking. May be null if not linking."
  type        = string
  default     = null
}

variable "application_type" {
  description = "Type of the application (web, other)"
  type        = string
  default     = "web"
}

variable "tags" {
  description = "Tags to apply to the component"
  type        = map(string)
  default     = {}
}
