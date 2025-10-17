variable "unique_suffix" {
  description = "Unique suffix for naming consistency"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group where the identity will be created"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to tag-supporting resources in this module"
  type        = map(string)
  default     = {}
}
