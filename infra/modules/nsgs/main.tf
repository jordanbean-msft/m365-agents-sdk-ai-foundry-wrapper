########## Associate Existing Network Security Groups (by ID) to Subnets ##########

## NOTE: This module now requires full NSG resource IDs. It does not look up by name.
## Example NSG ID pattern:
## /subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Network/networkSecurityGroups/<nsgName>

resource "azurerm_subnet_network_security_group_association" "agent" {
  subnet_id                 = var.subnet_id_agent
  network_security_group_id = var.nsg_id_agent
}

resource "azurerm_subnet_network_security_group_association" "private_endpoints" {
  subnet_id                 = var.subnet_id_private_endpoint
  network_security_group_id = var.nsg_id_private_endpoints
}

resource "azurerm_subnet_network_security_group_association" "logic_apps" {
  subnet_id                 = var.subnet_id_logic_apps
  network_security_group_id = var.nsg_id_logic_apps
}

resource "azurerm_subnet_network_security_group_association" "container_apps" {
  subnet_id                 = var.subnet_id_container_apps
  network_security_group_id = var.nsg_id_container_apps
}

## Placeholder for future managed rules (add azurerm_network_security_rule resources referencing the same IDs)
