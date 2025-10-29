########## Application Gateway Subnet NSG Rules ##########
# Reference: https://learn.microsoft.com/en-us/azure/application-gateway/configuration-infrastructure

# Inbound: Allow Gateway Manager (infrastructure communication)
resource "azurerm_network_security_rule" "app_gateway_allow_gateway_manager_inbound" {
  name                        = "allow-gateway-manager-inbound"
  priority                    = 120
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "65200-65535"
  source_address_prefix       = "GatewayManager"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.app_gateway.name
  description                 = "Allow Gateway Manager service for backend health status (v2 SKU: 65200-65535)"
}

# Inbound: Allow Azure Bot Service
resource "azurerm_network_security_rule" "app_gateway_allow_bot_service_inbound" {
  name                        = "allow-bot-service-inbound"
  priority                    = 130
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_ranges     = ["80", "443"]
  source_address_prefix       = "AzureBotService"
  destination_address_prefix  = var.subnet_id_app_gateway != null ? data.azurerm_subnet.app_gateway[0].address_prefixes[0] : "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.app_gateway.name
  description                 = "Allow inbound traffic from Azure Bot Service"
}

# Inbound: Allow Azure Load Balancer
resource "azurerm_network_security_rule" "app_gateway_allow_azure_load_balancer_inbound" {
  name                        = "allow-azure-load-balancer-inbound"
  priority                    = 140
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "AzureLoadBalancer"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.app_gateway.name
  description                 = "Allow Azure Load Balancer probes (default rule - do not override)"
}

# Outbound: Allow Internet (required for Application Gateway)
resource "azurerm_network_security_rule" "app_gateway_allow_internet_outbound" {
  name                        = "allow-internet-outbound"
  priority                    = 100
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "Internet"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.app_gateway.name
  description                 = "Allow outbound to Internet (default rule - do not override)"
}

# Outbound: Allow VNet communication (to reach backend Container App)
resource "azurerm_network_security_rule" "app_gateway_allow_vnet_outbound" {
  name                        = "allow-vnet-outbound"
  priority                    = 110
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = var.subnet_id_app_gateway != null ? data.azurerm_subnet.app_gateway[0].address_prefixes[0] : "*"
  destination_address_prefix  = "VirtualNetwork"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.app_gateway.name
  description                 = "Allow communication to VNet resources (backend pools)"
}

# Inbound: Deny all other traffic
resource "azurerm_network_security_rule" "app_gateway_deny_all_inbound" {
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
  network_security_group_name = local.nsgs.app_gateway.name
  description                 = "Deny all inbound traffic not explicitly allowed"
}

# NOTE: Application Gateway v2 SKU requires outbound Internet access
# The "allow-internet-outbound" rule at priority 100 satisfies this requirement
# Do NOT add a deny-all-outbound rule as it will cause deployment failures
