########## NSG Module - Main Entry Point ##########
# This module manages Network Security Group rules for all subnets
# Rules are organized in separate files by service/subnet:
# - nsg_container_apps.tf
# - nsg_logic_apps.tf
# - nsg_app_gateway.tf
# - nsg_private_endpoints.tf
# - nsg_agent.tf
#
# Shared resources:
# - locals.tf: NSG name/ID mappings
# - data.tf: Subnet data sources for address prefix lookups
