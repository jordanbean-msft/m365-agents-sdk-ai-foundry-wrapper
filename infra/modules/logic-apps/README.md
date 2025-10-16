# Logic Apps Standard Module - Network Isolation Setup

## Overview

This module deploys a fully network-isolated Logic Apps Standard (WS1 SKU) instance with private endpoints and VNet integration.

## Resources Created

### 1. Storage Account (`logicapps{suffix}st`)

- **Purpose**: Backend storage for Logic Apps Standard
- **SKU**: Standard LRS
- **Network**: Deny public access, Azure Services bypass enabled
- **Access**: Shared access keys enabled (required for Logic Apps)

### 2. App Service Plan (`asp-logicapps-{suffix}`)

- **SKU**: WS1 (Workflow Standard 1)
- **OS**: Windows
- **Purpose**: Hosting plan for Logic Apps Standard

### 3. Logic App Standard (`logic-{suffix}`)

- **Runtime**: Node.js ~18
- **Identity**: System-assigned managed identity enabled
- **VNet Integration**: Connected to dedicated Logic Apps subnet
- **Public Access**: Disabled
- **Route All**: Enabled (all outbound traffic goes through VNet)

### 4. Private Endpoints

- **Storage Account PE**: For blob subresource
- **Logic App PE**: For sites subresource

## Network Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Virtual Network                                         │
│                                                          │
│  ┌────────────────────┐      ┌──────────────────────┐  │
│  │ Logic Apps Subnet  │      │ Private Endpoints    │  │
│  │                    │      │ Subnet               │  │
│  │  ┌──────────────┐  │      │                      │  │
│  │  │ Logic App    │  │      │  ┌────────────────┐  │  │
│  │  │ (VNet Integ) │  │      │  │ Logic App PE   │  │  │
│  │  └──────────────┘  │      │  └────────────────┘  │  │
│  │                    │      │  ┌────────────────┐  │  │
│  │  Outbound: ✓       │      │  │ Storage PE     │  │  │
│  └────────────────────┘      │  └────────────────┘  │  │
│                               │                      │  │
│                               │  Inbound: ✓          │  │
│                               └──────────────────────┘  │
│                                                          │
│  Public Access: ✗                                       │
└─────────────────────────────────────────────────────────┘
```

## Configuration Requirements

### New Subnet Required

You need to create a new subnet in your VNet for Logic Apps VNet integration:

**Subnet Properties:**

- Name: `logic-apps` (or your preferred name)
- Delegation: `Microsoft.Web/serverFarms` (for App Service/Logic Apps)
- Service Endpoints: Not required but recommended for storage
- Network Policies: Enable for private endpoints

### Example Subnet Configuration

```terraform
# You'll need to add this subnet to your VNet
subnet_id_logic_apps = "/subscriptions/{subscription-id}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{vnet}/subnets/logic-apps"
```

## Variables Added

### `terraform.tfvars`

```hcl
subnet_id_logic_apps = "/subscriptions/0ec6c427-01d3-4462-ae56-fd9656157157/resourceGroups/rg-m365-agents/providers/Microsoft.Network/virtualNetworks/vnet-m365-agents/subnets/logic-apps"
```

### `variables.tf`

```hcl
variable "subnet_id_logic_apps" {
  description = "The resource id of the subnet that will be used for Logic Apps VNet integration"
  type        = string
}
```

## Security Features

✅ **No Public Network Access**

- Public network access is disabled
- All access must go through private endpoints

✅ **VNet Integration**

- All outbound traffic routed through VNet
- Can access private resources without exposing to internet

✅ **Private Endpoints**

- Logic App accessible via private IP only
- Storage account accessible via private IP only

✅ **Managed Identity**

- System-assigned managed identity for secure authentication
- Can be granted access to other Azure resources

✅ **TLS 1.2 Minimum**

- Both Logic App and Storage enforce minimum TLS 1.2

## Outputs Available

The module exposes these outputs for use in other modules:

- `logic_app_id` - Resource ID of the Logic App
- `logic_app_name` - Name of the Logic App
- `logic_app_principal_id` - Managed identity principal ID
- `logic_app_default_hostname` - Default hostname (for reference)
- `storage_account_id` - Storage account resource ID
- `storage_account_name` - Storage account name
- `app_service_plan_id` - App Service Plan resource ID

## Next Steps

### 1. Create the Logic Apps Subnet

Before deploying, create the subnet in your VNet:

- Delegate to `Microsoft.Web/serverFarms`
- Ensure sufficient IP address space
- No NSG rules blocking outbound traffic

### 2. Update tfvars

Already done! The subnet ID has been added to `terraform.tfvars`

### 3. Deploy

Run:

```bash
terraform init
terraform plan
terraform apply
```

### 4. Configure DNS (Optional)

If you have Private DNS Zones configured, uncomment the `private_dns_zone_group` blocks in the module to automatically register the private endpoints with DNS.

Required DNS Zones:

- `privatelink.blob.core.windows.net` (for storage)
- `privatelink.azurewebsites.net` (for Logic App)

## Workflow Development

After deployment, you can develop Logic Apps workflows:

- Use Azure Portal (through private access)
- Use VS Code with Azure Logic Apps extension
- Deploy via CI/CD pipelines
- Access via private endpoint from your network

## Cost Considerations

**WS1 SKU**: ~$200-300/month (varies by region)

- Includes 1 vCPU, 3.5 GB RAM
- Suitable for production workloads
- Can scale based on demand

**Storage**: Standard LRS pricing applies
**Private Endpoints**: ~$7.50/month per endpoint (2 endpoints)
