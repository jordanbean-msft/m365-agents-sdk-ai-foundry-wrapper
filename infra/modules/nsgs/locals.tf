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
