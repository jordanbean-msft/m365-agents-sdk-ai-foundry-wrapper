terraform {
  required_version = ">= 1.8.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.113.0"
    }
  }
}

# Provider configuration is inherited from root; do not declare a local one so that
# the root module can pass the aliased workload_subscription configuration.
