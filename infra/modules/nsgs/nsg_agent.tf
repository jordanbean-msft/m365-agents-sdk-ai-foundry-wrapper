########## AI Foundry Agent Subnet NSG Rules ##########
# No specific requirements found beyond VNet communication

# Inbound: Allow VNet traffic
resource "azurerm_network_security_rule" "agent_allow_vnet_inbound" {
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
  network_security_group_name = local.nsgs.agent.name
  description                 = "Allow VNet inbound traffic for AI Foundry agent communication"
}

# Outbound: Allow VNet traffic
resource "azurerm_network_security_rule" "agent_allow_vnet_outbound" {
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
  network_security_group_name = local.nsgs.agent.name
  description                 = "Allow VNet outbound traffic for AI Foundry agent communication"
}

# Outbound: Allow Azure Active Directory (for authentication)
resource "azurerm_network_security_rule" "agent_allow_aad_outbound" {
  name                        = "allow-azure-ad-outbound"
  priority                    = 110
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  source_address_prefix       = var.subnet_id_agent != null ? data.azurerm_subnet.agent[0].address_prefixes[0] : "*"
  destination_address_prefix  = "AzureActiveDirectory"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.agent.name
  description                 = "Allow Azure AD for authentication"
}

# Outbound: Allow Azure Monitor
resource "azurerm_network_security_rule" "agent_allow_monitor_outbound" {
  name                        = "allow-azure-monitor-outbound"
  priority                    = 120
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  source_address_prefix       = var.subnet_id_agent != null ? data.azurerm_subnet.agent[0].address_prefixes[0] : "*"
  destination_address_prefix  = "AzureMonitor"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.agent.name
  description                 = "Allow Azure Monitor for telemetry"
}

# Inbound: Deny all other traffic
resource "azurerm_network_security_rule" "agent_deny_all_inbound" {
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
  network_security_group_name = local.nsgs.agent.name
  description                 = "Deny all inbound traffic not explicitly allowed"
}

# Outbound: Deny all other traffic
resource "azurerm_network_security_rule" "agent_deny_all_outbound" {
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
  network_security_group_name = local.nsgs.agent.name
  description                 = "Deny all outbound traffic not explicitly allowed"
}
