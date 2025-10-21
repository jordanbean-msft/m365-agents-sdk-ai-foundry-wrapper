# Key Vault Module

This module provisions an Azure Key Vault for secure storage of secrets used by the M365 Agents infrastructure.

## Features

- **Private Network Access**: Key Vault is configured with public network access disabled and accessible only via private endpoint
- **RBAC Authorization**: Uses Azure RBAC for access control instead of access policies
- **Soft Delete & Purge Protection**: Enabled for data protection and compliance
- **Private Endpoint**: Secure private connectivity via VNet integration
- **Diagnostic Settings**: Optional logging to Log Analytics workspace

## Resources Created

- `azurerm_key_vault`: Key Vault instance with RBAC authorization
- `azurerm_private_endpoint`: Private endpoint for secure VNet access
- `azurerm_monitor_diagnostic_setting`: Optional diagnostic settings for audit logging

## Usage

```hcl
module "key_vault" {
  source = "./modules/key-vault"

  unique_suffix              = "abc123"
  resource_group_name        = "rg-example"
  location                   = "eastus2"
  subnet_id_private_endpoint = azurerm_subnet.private_endpoints.id
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  common_tags                = { Environment = "dev" }
  enable_diagnostics         = true
}
```

## Inputs

| Name                         | Description                            | Type          | Required           |
| ---------------------------- | -------------------------------------- | ------------- | ------------------ |
| `unique_suffix`              | Unique suffix for resource naming      | `string`      | Yes                |
| `resource_group_name`        | Name of the resource group             | `string`      | Yes                |
| `location`                   | Azure region for resources             | `string`      | Yes                |
| `subnet_id_private_endpoint` | Subnet ID for private endpoints        | `string`      | Yes                |
| `tenant_id`                  | Azure AD tenant ID                     | `string`      | Yes                |
| `log_analytics_workspace_id` | Resource ID of Log Analytics Workspace | `string`      | No                 |
| `enable_diagnostics`         | Enable diagnostic settings             | `bool`        | No (default: true) |
| `common_tags`                | Common tags to apply to all resources  | `map(string)` | No                 |

## Outputs

| Name                  | Description                         |
| --------------------- | ----------------------------------- |
| `key_vault_id`        | Resource ID of the Key Vault        |
| `key_vault_name`      | Name of the Key Vault               |
| `key_vault_uri`       | URI of the Key Vault                |
| `private_endpoint_id` | Resource ID of the private endpoint |

## RBAC Requirements

To use this module, the following role assignments are needed:

1. **Terraform Execution Identity**: Requires `Key Vault Administrator` role to create secrets
2. **Managed Identities**: Require `Key Vault Secrets User` role to read secrets

## Security Considerations

- Public network access is disabled
- Access is only available via private endpoint
- RBAC-based authorization enforces least-privilege access
- Soft delete and purge protection prevent accidental data loss
- All access is logged via diagnostic settings

## Dependencies

This module depends on:

- Virtual network with a private endpoint subnet
- Azure AD tenant for identity management
- Optional: Log Analytics workspace for diagnostics

## Integration

This module is designed to work with:

- **Container Apps**: Use Key Vault references in container app secrets
- **Bot Service**: Retrieve secrets from Key Vault for OAuth configuration
- **Managed Identities**: Grant RBAC access for automated secret retrieval
