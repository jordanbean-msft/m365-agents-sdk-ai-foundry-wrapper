########## Logic Apps Subnet NSG Rules ##########
# Reference: https://learn.microsoft.com/en-us/azure/logic-apps/secure-single-tenant-workflow-virtual-network-private-endpoint

# Outbound: Allow storage access (for backend storage)
resource "azurerm_network_security_rule" "logic_apps_allow_storage_outbound" {
  name                        = "allow-storage-outbound"
  priority                    = 100
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_ranges     = ["443", "445"]
  source_address_prefix       = var.subnet_id_logic_apps != null ? data.azurerm_subnet.logic_apps[0].address_prefixes[0] : "*"
  destination_address_prefix  = "Storage"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.logic_apps.name
  description                 = "Allow HTTPS and SMB file share access to storage account"
}

# Outbound: Allow communication to managed connector IPs (for Azure-hosted managed connectors)
resource "azurerm_network_security_rule" "logic_apps_allow_connectors_outbound" {
  name                        = "allow-managed-connectors-outbound"
  priority                    = 110
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  source_address_prefix       = var.subnet_id_logic_apps != null ? data.azurerm_subnet.logic_apps[0].address_prefixes[0] : "*"
  destination_address_prefix  = "AzureConnectors"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.logic_apps.name
  description                 = "Allow access to Azure-managed connector IP addresses"
}

# Outbound: Allow VNet communication
resource "azurerm_network_security_rule" "logic_apps_allow_vnet_outbound" {
  name                        = "allow-vnet-outbound"
  priority                    = 120
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = var.subnet_id_logic_apps != null ? data.azurerm_subnet.logic_apps[0].address_prefixes[0] : "*"
  destination_address_prefix  = "VirtualNetwork"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.logic_apps.name
  description                 = "Allow VNet communication for accessing private endpoints"
}

# Inbound: Deny all other traffic
resource "azurerm_network_security_rule" "logic_apps_deny_all_inbound" {
  name                        = "deny-all-inbound"
  priority                    = 4096
  direction                   = "Inbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.logic_apps.name
  description                 = "Deny all inbound traffic not explicitly allowed"
}

# Outbound: Deny all other traffic
resource "azurerm_network_security_rule" "logic_apps_deny_all_outbound" {
  name                        = "deny-all-outbound"
  priority                    = 4096
  direction                   = "Outbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.logic_apps.name
  description                 = "Deny all outbound traffic not explicitly allowed"
}
