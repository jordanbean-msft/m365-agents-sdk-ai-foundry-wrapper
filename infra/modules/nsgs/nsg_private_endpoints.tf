########## Private Endpoints Subnet NSG Rules ##########
# Private endpoints generally don't require specific NSG rules, but we allow VNet traffic

# Inbound: Allow VNet traffic to private endpoints
resource "azurerm_network_security_rule" "private_endpoints_allow_vnet_inbound" {
  name                        = "allow-vnet-inbound"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "VirtualNetwork"
  destination_address_prefix  = "VirtualNetwork"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.private_endpoints.name
  description                 = "Allow VNet traffic to access private endpoints"
}

# Outbound: Allow VNet traffic from private endpoints
resource "azurerm_network_security_rule" "private_endpoints_allow_vnet_outbound" {
  name                        = "allow-vnet-outbound"
  priority                    = 100
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "VirtualNetwork"
  destination_address_prefix  = "VirtualNetwork"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.private_endpoints.name
  description                 = "Allow outbound VNet traffic from private endpoints"
}

# Inbound: Deny all other traffic
resource "azurerm_network_security_rule" "private_endpoints_deny_all_inbound" {
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
  network_security_group_name = local.nsgs.private_endpoints.name
  description                 = "Deny all inbound traffic not explicitly allowed"
}

# Outbound: Deny all other traffic
resource "azurerm_network_security_rule" "private_endpoints_deny_all_outbound" {
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
  network_security_group_name = local.nsgs.private_endpoints.name
  description                 = "Deny all outbound traffic not explicitly allowed"
}
