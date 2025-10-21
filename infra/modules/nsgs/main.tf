########## Managed Security Rules for Existing Network Security Groups ##########

locals {
  nsgs = {
    agent = {
      id   = var.nsg_id_agent
      name = element(reverse(split("/", var.nsg_id_agent)), 0)
    }
    private_endpoints = {
      id   = var.nsg_id_private_endpoints
      name = element(reverse(split("/", var.nsg_id_private_endpoints)), 0)
    }
    logic_apps = {
      id   = var.nsg_id_logic_apps
      name = element(reverse(split("/", var.nsg_id_logic_apps)), 0)
    }
    container_apps = {
      id   = var.nsg_id_container_apps
      name = element(reverse(split("/", var.nsg_id_container_apps)), 0)
    }
    app_gateway = {
      id   = var.nsg_id_app_gateway
      name = element(reverse(split("/", var.nsg_id_app_gateway)), 0)
    }
  }
}

# Allow intra-VNet traffic (broad) so internal service components can communicate.
# resource "azurerm_network_security_rule" "allow_vnet_inbound" {
#   for_each                    = local.nsgs
#   name                        = "allow-vnet-inbound"
#   priority                    = 100
#   direction                   = "Inbound"
#   access                      = "Allow"
#   protocol                    = "*"
#   source_port_range           = "*"
#   destination_port_range      = "*"
#   source_address_prefix       = "VirtualNetwork"
#   destination_address_prefix  = "VirtualNetwork"
#   resource_group_name         = var.resource_group_name
#   network_security_group_name = each.value.name
#   description                 = "Allow all intra-VNet traffic"
# }

# Explicit deny of all other inbound traffic. (Built-in DenyAllInBound exists, but we surface an
# earlier explicit deny so that any future allow rules must be well‑scoped and prioritized <200.)
# resource "azurerm_network_security_rule" "deny_all_inbound" {
#   for_each                    = local.nsgs
#   name                        = "deny-all-inbound"
#   priority                    = 200
#   direction                   = "Inbound"
#   access                      = "Deny"
#   protocol                    = "*"
#   source_port_range           = "*"
#   destination_port_range      = "*"
#   source_address_prefix       = "*"
#   destination_address_prefix  = "*"
#   resource_group_name         = var.resource_group_name
#   network_security_group_name = each.value.name
#   description                 = "Deny all inbound traffic not explicitly allowed"
# }

########## End of Managed Security Rules ##########
