########## Container Apps Subnet NSG Rules ##########
# Reference: https://learn.microsoft.com/en-us/azure/container-apps/firewall-integration

# Inbound: Allow Azure Load Balancer health probes
resource "azurerm_network_security_rule" "container_apps_allow_azure_load_balancer_inbound" {
  name                        = "allow-azure-load-balancer-inbound"
  priority                    = 100
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "30000-32767"
  source_address_prefix       = "AzureLoadBalancer"
  destination_address_prefix  = var.subnet_id_container_apps != null ? data.azurerm_subnet.container_apps[0].address_prefixes[0] : "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.container_apps.name
  description                 = "Allow Azure Load Balancer to probe backend pools"
}

# Inbound: Allow internal VNet communication (for Envoy sidecar)
resource "azurerm_network_security_rule" "container_apps_allow_vnet_inbound" {
  name                        = "allow-vnet-inbound"
  priority                    = 110
  direction                   = "Inbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "VirtualNetwork"
  destination_address_prefix  = "VirtualNetwork"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.container_apps.name
  description                 = "Allow intra-VNet traffic for Container Apps Envoy sidecar communication"
}

# Outbound: Allow Microsoft Container Registry
resource "azurerm_network_security_rule" "container_apps_allow_mcr_outbound" {
  name                        = "allow-mcr-outbound"
  priority                    = 100
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  source_address_prefix       = var.subnet_id_container_apps != null ? data.azurerm_subnet.container_apps[0].address_prefixes[0] : "*"
  destination_address_prefix  = "MicrosoftContainerRegistry"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.container_apps.name
  description                 = "Allow access to Microsoft Container Registry for system containers"
}

# Outbound: Allow Azure Front Door (dependency for MCR)
resource "azurerm_network_security_rule" "container_apps_allow_afd_outbound" {
  name                        = "allow-azure-front-door-outbound"
  priority                    = 110
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  source_address_prefix       = var.subnet_id_container_apps != null ? data.azurerm_subnet.container_apps[0].address_prefixes[0] : "*"
  destination_address_prefix  = "AzureFrontDoor.FirstParty"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.container_apps.name
  description                 = "Dependency of MicrosoftContainerRegistry service tag"
}

# Outbound: Allow Azure Active Directory (for managed identity)
resource "azurerm_network_security_rule" "container_apps_allow_aad_outbound" {
  name                        = "allow-azure-ad-outbound"
  priority                    = 120
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  source_address_prefix       = var.subnet_id_container_apps != null ? data.azurerm_subnet.container_apps[0].address_prefixes[0] : "*"
  destination_address_prefix  = "AzureActiveDirectory"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.container_apps.name
  description                 = "Required for managed identity authentication"
}

# Outbound: Allow Azure Monitor
resource "azurerm_network_security_rule" "container_apps_allow_monitor_outbound" {
  name                        = "allow-azure-monitor-outbound"
  priority                    = 130
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  source_address_prefix       = var.subnet_id_container_apps != null ? data.azurerm_subnet.container_apps[0].address_prefixes[0] : "*"
  destination_address_prefix  = "AzureMonitor"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.container_apps.name
  description                 = "Allow outbound calls to Azure Monitor"
}

# Outbound: Allow DNS resolution (Azure DNS)
resource "azurerm_network_security_rule" "container_apps_allow_dns_outbound" {
  name                        = "allow-azure-dns-outbound"
  priority                    = 140
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "53"
  source_address_prefix       = var.subnet_id_container_apps != null ? data.azurerm_subnet.container_apps[0].address_prefixes[0] : "*"
  destination_address_prefix  = "168.63.129.16"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.container_apps.name
  description                 = "Allow DNS resolution to Azure DNS"
}

# Outbound: Allow VNet communication
resource "azurerm_network_security_rule" "container_apps_allow_vnet_outbound" {
  name                        = "allow-vnet-outbound"
  priority                    = 150
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = var.subnet_id_container_apps != null ? data.azurerm_subnet.container_apps[0].address_prefixes[0] : "*"
  destination_address_prefix  = "VirtualNetwork"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.container_apps.name
  description                 = "Allow communication between IPs in the VNet"
}

# Outbound: Allow HTTPS to Internet for JWT/JWKS validation
# Required for Bot Framework authentication: login.microsoftonline.com, login.botframework.com
# Reference: https://learn.microsoft.com/en-us/azure/bot-service/rest-api/bot-framework-rest-connector-authentication
resource "azurerm_network_security_rule" "container_apps_allow_internet_https_outbound" {
  name                        = "allow-internet-https-outbound"
  priority                    = 160
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "Tcp"
  source_port_range           = "*"
  destination_port_range      = "443"
  source_address_prefix       = var.subnet_id_container_apps != null ? data.azurerm_subnet.container_apps[0].address_prefixes[0] : "*"
  destination_address_prefix  = "Internet"
  resource_group_name         = var.resource_group_name
  network_security_group_name = local.nsgs.container_apps.name
  description                 = "Allow HTTPS to Internet for JWT/JWKS token validation (login.microsoftonline.com, login.botframework.com)"
}

# Inbound: Deny all other traffic
resource "azurerm_network_security_rule" "container_apps_deny_all_inbound" {
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
  network_security_group_name = local.nsgs.container_apps.name
  description                 = "Deny all inbound traffic not explicitly allowed"
}

# Outbound: Deny all other traffic
resource "azurerm_network_security_rule" "container_apps_deny_all_outbound" {
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
  network_security_group_name = local.nsgs.container_apps.name
  description                 = "Deny all outbound traffic not explicitly allowed"
}
