########## User Assigned Managed Identity Module ##########

resource "azurerm_user_assigned_identity" "container_app" {
  name                = "uami-containerapps-${var.unique_suffix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.common_tags
}
