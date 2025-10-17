########## Main Terraform Configuration
##########

## Foundation module - Creates random string for unique resource naming
##
module "foundation" {
  source = "./modules/foundation"
}

## NSGs module - Attaches Network Security Groups to existing subnets
##
module "nsgs" {
  source = "./modules/nsgs"

  providers = {
    azurerm = azurerm.workload_subscription
  }

  unique_suffix              = module.foundation.unique_suffix
  resource_group_name        = var.resource_group_name_resources
  location                   = var.location
  subnet_id_agent            = var.subnet_id_agent
  subnet_id_private_endpoint = var.subnet_id_private_endpoint
  subnet_id_logic_apps       = var.subnet_id_logic_apps
  subnet_id_container_apps   = var.subnet_id_container_apps
  nsg_id_agent               = var.nsg_id_agent
  nsg_id_private_endpoints   = var.nsg_id_private_endpoints
  nsg_id_logic_apps          = var.nsg_id_logic_apps
  nsg_id_container_apps      = var.nsg_id_container_apps
}

## Storage module - Creates storage resources for agent data
##
module "storage" {
  source = "./modules/storage"

  providers = {
    azapi = azapi.workload_subscription
  }

  unique_suffix              = module.foundation.unique_suffix
  resource_group_name        = var.resource_group_name_resources
  location                   = var.location
  subscription_id            = var.subscription_id_resources
  log_analytics_workspace_id = var.log_analytics_workspace_id
  common_tags                = var.common_tags
  enable_diagnostics         = var.enable_diagnostics
}

## AI Foundry module - Creates AI Foundry resource and deployments
##
module "ai_foundry" {
  source = "./modules/ai-foundry"

  providers = {
    azapi   = azapi.workload_subscription
    azurerm = azurerm.workload_subscription
  }

  unique_suffix              = module.foundation.unique_suffix
  resource_group_name        = var.resource_group_name_resources
  location                   = var.location
  subscription_id            = var.subscription_id_resources
  subnet_id_agent            = var.subnet_id_agent
  log_analytics_workspace_id = var.log_analytics_workspace_id
  common_tags                = var.common_tags
  enable_diagnostics         = var.enable_diagnostics
}

## Networking module - Creates private endpoints
##
module "networking" {
  source = "./modules/networking"

  providers = {
    azurerm = azurerm.workload_subscription
  }

  depends_on = [
    module.storage,
    module.ai_foundry
  ]

  resource_group_name        = var.resource_group_name_resources
  location                   = var.location
  subnet_id_private_endpoint = var.subnet_id_private_endpoint

  storage_account_id   = module.storage.storage_account_id
  storage_account_name = module.storage.storage_account_name
  cosmosdb_id          = module.storage.cosmosdb_id
  cosmosdb_name        = module.storage.cosmosdb_name
  ai_search_id         = module.storage.ai_search_id
  ai_search_name       = module.storage.ai_search_name
  ai_foundry_id        = module.ai_foundry.ai_foundry_id
  ai_foundry_name      = module.ai_foundry.ai_foundry_name
  common_tags          = var.common_tags
}

## Project module - Creates AI Foundry project, connections, and role assignments
##
module "project" {
  source = "./modules/project"

  providers = {
    azapi   = azapi.workload_subscription
    azurerm = azurerm.workload_subscription
  }

  depends_on = [
    module.networking
  ]

  unique_suffix                         = module.foundation.unique_suffix
  resource_group_name                   = var.resource_group_name_resources
  location                              = var.location
  ai_foundry_id                         = module.ai_foundry.ai_foundry_id
  storage_account_id                    = module.storage.storage_account_id
  storage_account_name                  = module.storage.storage_account_name
  storage_account_primary_blob_endpoint = module.storage.storage_account_primary_blob_endpoint
  cosmosdb_id                           = module.storage.cosmosdb_id
  cosmosdb_name                         = module.storage.cosmosdb_name
  cosmosdb_endpoint                     = module.storage.cosmosdb_endpoint
  ai_search_id                          = module.storage.ai_search_id
  ai_search_name                        = module.storage.ai_search_name
  pe_storage_id                         = module.networking.pe_storage_id
  pe_cosmosdb_id                        = module.networking.pe_cosmosdb_id
  pe_aisearch_id                        = module.networking.pe_aisearch_id
  pe_aifoundry_id                       = module.networking.pe_aifoundry_id
  common_tags                           = var.common_tags
}

## Logic Apps module - Creates Logic Apps Standard with private endpoints and VNet integration
##
module "logic_apps" {
  source = "./modules/logic-apps"

  providers = {
    azurerm = azurerm.workload_subscription
  }

  depends_on = [
    module.identity
  ]

  unique_suffix                       = module.foundation.unique_suffix
  resource_group_name                 = var.resource_group_name_resources
  location                            = var.location
  subnet_id_logic_apps                = var.subnet_id_logic_apps
  subnet_id_private_endpoint          = var.subnet_id_private_endpoint
  user_assigned_identity_id           = module.identity.user_assigned_identity_id
  user_assigned_identity_principal_id = module.identity.user_assigned_identity_principal_id
  website_dns_server                  = var.logic_apps_website_dns_server
  log_analytics_workspace_id          = var.log_analytics_workspace_id
  common_tags                         = var.common_tags
  enable_diagnostics                  = var.enable_diagnostics
}

## Identity module - User Assigned Managed Identity for Container Apps
##
module "identity" {
  source = "./modules/identity"

  providers = {
    azurerm = azurerm.workload_subscription
  }

  unique_suffix       = module.foundation.unique_suffix
  resource_group_name = var.resource_group_name_resources
  location            = var.location
  common_tags         = var.common_tags
}

## ACR module - Azure Container Registry for private images
##
module "acr" {
  source = "./modules/acr"

  providers = {
    azurerm = azurerm.workload_subscription
  }

  unique_suffix              = module.foundation.unique_suffix
  resource_group_name        = var.resource_group_name_resources
  location                   = var.location
  sku                        = "Premium"
  pull_principal_id          = module.identity.user_assigned_identity_principal_id
  subnet_id_private_endpoint = var.subnet_id_private_endpoint
  log_analytics_workspace_id = var.log_analytics_workspace_id
  common_tags                = var.common_tags
  enable_diagnostics         = var.enable_diagnostics
}

## Container Apps module - Creates Container App Environment and Container App with VNet integration
##
module "container_apps" {
  source = "./modules/container-apps"

  providers = {
    azurerm = azurerm.workload_subscription
  }

  depends_on = [
    module.ai_foundry,
    module.project,
    module.acr,
    module.identity
  ]

  unique_suffix                    = module.foundation.unique_suffix
  resource_group_name              = var.resource_group_name_resources
  location                         = var.location
  subnet_id_container_apps         = var.subnet_id_container_apps
  container_image                  = var.container_image
  service_connection_client_id     = var.service_connection_client_id
  service_connection_client_secret = var.service_connection_client_secret
  tenant_id                        = var.tenant_id
  ai_project_endpoint              = module.ai_foundry.ai_foundry_endpoint
  ai_foundry_agent_id              = var.ai_foundry_agent_id
  ai_model_deployment_name         = module.ai_foundry.ai_model_deployment_name
  azure_client_id                  = module.identity.user_assigned_identity_client_id
  registry_server                  = module.acr.acr_login_server
  user_assigned_identity_id        = module.identity.user_assigned_identity_id
  log_analytics_workspace_id       = var.log_analytics_workspace_id
  common_tags                      = var.common_tags
  enable_diagnostics               = var.enable_diagnostics
}


## RBAC: Grant Cognitive Services User (Azure AI User) to the user-assigned identity on AI Foundry scope
resource "azurerm_role_assignment" "uami_ai_foundry_user" {
  scope                = module.ai_foundry.ai_foundry_id
  role_definition_name = "Cognitive Services User"
  principal_id         = module.identity.user_assigned_identity_principal_id
  depends_on = [
    module.ai_foundry,
    module.identity
  ]
  provider = azurerm.workload_subscription
}
