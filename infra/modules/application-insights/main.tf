resource "azurerm_application_insights" "main" {
  count               = var.existing_application_insights_id == null ? 1 : 0
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
  application_type    = var.application_type
  workspace_id        = var.workspace_id
  tags                = var.tags
}

data "azurerm_application_insights" "existing" {
  count               = var.existing_application_insights_id != null ? 1 : 0
  name                = split("/", var.existing_application_insights_id)[8]
  resource_group_name = split("/", var.existing_application_insights_id)[4]
}
