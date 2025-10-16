# Setup providers
provider "azapi" {
  subscription_id = var.subscription_id_resources
}

provider "azapi" {
  alias           = "workload_subscription"
  subscription_id = var.subscription_id_resources
}

provider "azurerm" {
  subscription_id = var.subscription_id_resources
  features {}
  storage_use_azuread = true
}

provider "azurerm" {
  alias           = "workload_subscription"
  subscription_id = var.subscription_id_resources
  features {}
  storage_use_azuread = true
}
