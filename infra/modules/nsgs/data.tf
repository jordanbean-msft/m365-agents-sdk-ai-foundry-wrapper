########## Data Sources for Subnet Address Prefixes ##########

data "azurerm_subnet" "container_apps" {
  count                = var.subnet_id_container_apps != null ? 1 : 0
  name                 = split("/", var.subnet_id_container_apps)[10]
  virtual_network_name = split("/", var.subnet_id_container_apps)[8]
  resource_group_name  = split("/", var.subnet_id_container_apps)[4]
}

data "azurerm_subnet" "logic_apps" {
  count                = var.subnet_id_logic_apps != null ? 1 : 0
  name                 = split("/", var.subnet_id_logic_apps)[10]
  virtual_network_name = split("/", var.subnet_id_logic_apps)[8]
  resource_group_name  = split("/", var.subnet_id_logic_apps)[4]
}

data "azurerm_subnet" "app_gateway" {
  count                = var.subnet_id_app_gateway != null ? 1 : 0
  name                 = split("/", var.subnet_id_app_gateway)[10]
  virtual_network_name = split("/", var.subnet_id_app_gateway)[8]
  resource_group_name  = split("/", var.subnet_id_app_gateway)[4]
}

data "azurerm_subnet" "agent" {
  count                = var.subnet_id_agent != null ? 1 : 0
  name                 = split("/", var.subnet_id_agent)[10]
  virtual_network_name = split("/", var.subnet_id_agent)[8]
  resource_group_name  = split("/", var.subnet_id_agent)[4]
}
