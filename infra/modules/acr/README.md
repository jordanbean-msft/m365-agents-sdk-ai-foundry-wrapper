# Azure Container Registry Module

## Overview

This module provisions an Azure Container Registry (ACR) with private networking, private endpoints, and an optional agent pool for executing ACR Tasks from within a VNet.

## Features

- **Premium SKU**: Required for agent pool support and enhanced features
- **Private networking**: Public network access disabled, private endpoint for registry access
- **Network rule bypass for tasks**: Enables ACR Tasks to pull base images and push built images
- **Agent pool with VNet integration**: Allows ACR Tasks to run within your private network
- **RBAC**: Grants AcrPull role to specified managed identity
- **Diagnostic settings**: Optional integration with Log Analytics

## Resources Created

- `azurerm_container_registry` - Premium ACR instance
- `azapi_update_resource` - Network bypass configuration for tasks
- `azurerm_role_assignment` - AcrPull role assignment
- `azurerm_private_endpoint` - Private endpoint for registry access
- `azurerm_container_registry_agent_pool` (optional) - VNet-integrated agent pool for ACR Tasks
- `azurerm_monitor_diagnostic_setting` (optional) - Diagnostic settings

## Required Variables

| Variable                     | Type   | Description                                      |
| ---------------------------- | ------ | ------------------------------------------------ |
| `unique_suffix`              | string | Unique suffix for global naming (e.g., ACR name) |
| `resource_group_name`        | string | Resource group name                              |
| `location`                   | string | Azure region                                     |
| `subnet_id_private_endpoint` | string | Subnet ID for ACR private endpoint               |
| `log_analytics_workspace_id` | string | Log Analytics workspace ID for diagnostics       |

## Optional Variables

| Variable               | Type        | Default   | Description                                  |
| ---------------------- | ----------- | --------- | -------------------------------------------- |
| `sku`                  | string      | `"Basic"` | ACR SKU (Premium required for agent pool)    |
| `pull_principal_id`    | string      | `""`      | Principal ID to grant AcrPull role           |
| `enable_diagnostics`   | bool        | `true`    | Enable diagnostic settings                   |
| `enable_agent_pool`    | bool        | `false`   | Create ACR agent pool (requires Premium SKU) |
| `agent_pool_subnet_id` | string      | `""`      | Subnet ID for agent pool VNet integration    |
| `common_tags`          | map(string) | `{}`      | Common tags for all resources                |

## Outputs

| Output                    | Description                                   |
| ------------------------- | --------------------------------------------- |
| `acr_id`                  | ACR resource ID                               |
| `acr_name`                | ACR name                                      |
| `acr_login_server`        | ACR login server (FQDN)                       |
| `acr_private_endpoint_id` | Private endpoint resource ID                  |
| `acr_agent_pool_name`     | Agent pool name (empty if not created)        |
| `acr_agent_pool_id`       | Agent pool resource ID (empty if not created) |

## Agent Pool Usage

The agent pool allows ACR Tasks to execute within your VNet, enabling access to private resources while building and pushing images.

### Prerequisites

- ACR SKU must be set to `Premium`
- `enable_agent_pool` must be `true`
- `agent_pool_subnet_id` must point to a valid subnet (typically the private endpoints subnet)

### Using the Agent Pool with `az acr` Commands

Once created, reference the agent pool in `az acr build` or `az acr task` commands:

```bash
# Get agent pool name from Terraform output
AGENT_POOL_NAME=$(terraform output -raw acr_agent_pool_name)
ACR_NAME=$(terraform output -raw acr_name)

# Build image using agent pool
az acr build \
  --registry $ACR_NAME \
  --agent-pool $AGENT_POOL_NAME \
  --image myapp:v1 \
  .

# Run task using agent pool
az acr task run \
  --registry $ACR_NAME \
  --agent-pool $AGENT_POOL_NAME \
  --name mytask
```

### Agent Pool Configuration

- **Instance count**: 1 (can be increased for parallel builds)
- **Tier**: S1 (adjust based on build requirements)
- **VNet integration**: Uses `agent_pool_subnet_id` for private network access

## Dependencies

- Foundation module (for `unique_suffix`)
- Networking (subnet must exist before module execution)

## Example Usage

```hcl
module "acr" {
  source = "./modules/acr"

  unique_suffix              = module.foundation.unique_suffix
  resource_group_name        = var.resource_group_name
  location                   = var.location
  sku                        = "Premium"
  pull_principal_id          = module.identity.user_assigned_identity_principal_id
  subnet_id_private_endpoint = var.subnet_id_private_endpoint
  agent_pool_subnet_id       = var.subnet_id_private_endpoint
  enable_agent_pool          = true
  log_analytics_workspace_id = var.log_analytics_workspace_id
  common_tags                = var.common_tags
  enable_diagnostics         = true
}
```

## Notes

- **Network bypass**: Automatically configured to allow ACR Tasks to bypass network restrictions for image operations
- **Private access only**: Public network access is disabled; use private endpoint or agent pool
- **Global uniqueness**: ACR name must be globally unique (handled via `unique_suffix`)
- **Agent pool subnet**: Can be the same as the private endpoint subnet or a dedicated subnet depending on your network design
