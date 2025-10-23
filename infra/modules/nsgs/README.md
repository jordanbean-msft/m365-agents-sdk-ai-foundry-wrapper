# Network Security Groups Module

## Overview

This module manages Network Security Group (NSG) rules for all subnets in the Azure infrastructure. Each subnet has specific inbound and outbound rules based on the services deployed and their networking requirements.

## NSG Rules Summary

### 1. Container Apps Subnet (`container_apps`)

**Purpose**: Hosts Azure Container Apps Environment with VNet integration

**Inbound Rules**:

- **Priority 100**: Allow Azure Load Balancer health probes (TCP 30000-32767)
- **Priority 110**: Allow VNet traffic (all protocols, all ports)

**Outbound Rules**:

- **Priority 100**: Microsoft Container Registry (TCP 443 to `MicrosoftContainerRegistry`)
- **Priority 110**: Azure Front Door (TCP 443 to `AzureFrontDoor.FirstParty`) - MCR dependency
- **Priority 120**: Azure Active Directory (TCP 443 to `AzureActiveDirectory`) - managed identity
- **Priority 130**: Azure Monitor (TCP 443 to `AzureMonitor`)
- **Priority 140**: Azure DNS (TCP/UDP 53 to 168.63.129.16)
- **Priority 150**: VNet communication (all protocols, all ports to `VirtualNetwork`)

**References**:

- [Securing a virtual network with Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/firewall-integration)
- [Container Apps networking](https://learn.microsoft.com/en-us/azure/container-apps/networking)

---

### 2. Logic Apps Subnet (`logic_apps`)

**Purpose**: Hosts Logic Apps Standard with VNet integration for outbound traffic

**Inbound Rules**:

- No specific inbound rules required (uses private endpoints for inbound access)

**Outbound Rules**:

- **Priority 100**: Storage access (TCP 443, 445 to `Storage`) - backend storage and file shares
- **Priority 110**: Managed Connectors (TCP 443 to `AzureConnectors`) - Azure-hosted connectors
- **Priority 120**: VNet communication (all protocols, all ports to `VirtualNetwork`)

**References**:

- [Secure Logic Apps with virtual networks](https://learn.microsoft.com/en-us/azure/logic-apps/secure-single-tenant-workflow-virtual-network-private-endpoint)
- [Logic Apps VNet integration considerations](https://learn.microsoft.com/en-us/azure/logic-apps/secure-single-tenant-workflow-virtual-network-private-endpoint#set-up-outbound-traffic-using-virtual-network-integration)

---

### 3. Application Gateway Subnet (`app_gateway`)

**Purpose**: Hosts Azure Application Gateway v2 (WAF_v2 SKU) for public internet access

**Inbound Rules**:

- **Priority 100**: HTTP traffic (TCP 80 from `Internet`)
- **Priority 110**: HTTPS traffic (TCP 443 from `Internet`)
- **Priority 120**: Gateway Manager (TCP 65200-65535 from `GatewayManager`) - infrastructure
- **Priority 130**: Azure Load Balancer (all protocols, all ports from `AzureLoadBalancer`)

**Outbound Rules**:

- **Priority 100**: Internet access (all protocols, all ports to `Internet`) - required for App Gateway
- **Priority 110**: VNet communication (all protocols, all ports to `VirtualNetwork`) - backend pools

**References**:

- [Application Gateway infrastructure configuration](https://learn.microsoft.com/en-us/azure/application-gateway/configuration-infrastructure)
- [Application Gateway NSG requirements](https://learn.microsoft.com/en-us/azure/application-gateway/configuration-infrastructure#network-security-groups)

---

### 4. Private Endpoints Subnet (`private_endpoints`)

**Purpose**: Hosts private endpoints for Storage, Cosmos DB, AI Search, AI Foundry, Key Vault, ACR, Logic Apps

**Inbound Rules**:

- **Priority 100**: VNet traffic (all protocols, all ports from `VirtualNetwork`)

**Outbound Rules**:

- **Priority 100**: VNet traffic (all protocols, all ports to `VirtualNetwork`)

**Notes**:

- Private endpoints don't require specific port rules
- NSG support for private endpoints allows VNet traffic filtering
- Effective routes and security rules are NOT displayed for private endpoint NICs in Azure Portal

**References**:

- [Private endpoint overview](https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-overview)
- [NSG limitations with private endpoints](https://learn.microsoft.com/en-us/azure/private-link/private-endpoint-overview#limitations)

---

### 5. AI Foundry Agent Subnet (`agent`)

**Purpose**: Hosts AI Foundry agent workloads with private networking

**Inbound Rules**:

- **Priority 100**: VNet traffic (all protocols, all ports from `VirtualNetwork`)

**Outbound Rules**:

- **Priority 100**: VNet communication (all protocols, all ports to `VirtualNetwork`)
- **Priority 110**: Azure Active Directory (TCP 443 to `AzureActiveDirectory`) - authentication
- **Priority 120**: Azure Monitor (TCP 443 to `AzureMonitor`) - telemetry

**Notes**:

- AI Foundry supports NSG configuration on agent subnets
- Network isolation is achieved through private endpoints and VNet integration

**References**:

- [Azure AI Foundry security baseline](https://learn.microsoft.com/en-us/security/benchmark/azure/baselines/azure-ai-foundry-security-baseline)
- [AI Foundry network security](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/configure-private-link)

---

## Service Tag Reference

The following Azure service tags are used in the NSG rules:

| Service Tag                  | Description                                                         | Used By                     |
| ---------------------------- | ------------------------------------------------------------------- | --------------------------- |
| `VirtualNetwork`             | All VNet address spaces, connected on-premises spaces, peered VNets | All subnets                 |
| `AzureLoadBalancer`          | Azure infrastructure load balancer                                  | Container Apps, App Gateway |
| `MicrosoftContainerRegistry` | Microsoft-managed container registry                                | Container Apps              |
| `AzureFrontDoor.FirstParty`  | Azure Front Door first-party services                               | Container Apps              |
| `AzureActiveDirectory`       | Microsoft Entra ID (Azure AD)                                       | Container Apps, Agent       |
| `AzureMonitor`               | Azure Monitor service endpoints                                     | Container Apps, Agent       |
| `Storage`                    | Azure Storage service endpoints                                     | Logic Apps                  |
| `AzureConnectors`            | Azure Logic Apps managed connector IPs                              | Logic Apps                  |
| `GatewayManager`             | Azure infrastructure for Application Gateway                        | App Gateway                 |
| `Internet`                   | Public internet address space                                       | App Gateway                 |

## Port Requirements Summary

### Container Apps

- **Inbound**: 30000-32767 (Load Balancer probes)
- **Outbound**: 443 (HTTPS), 53 (DNS)

### Logic Apps

- **Outbound**: 443 (HTTPS), 445 (SMB for file shares)

### Application Gateway

- **Inbound**: 80 (HTTP), 443 (HTTPS), 65200-65535 (Gateway Manager)
- **Outbound**: All (Internet access required)

### Private Endpoints

- **All traffic within VNet** (no specific ports)

### AI Foundry Agent

- **Outbound**: 443 (HTTPS for Azure services)

## Design Principles

1. **Least Privilege**: Only necessary traffic is allowed; default deny for all other traffic
2. **Service-Specific**: Each subnet has rules tailored to the specific Azure service requirements
3. **Service Tags**: Leverages Azure service tags for dynamic IP range management
4. **VNet Communication**: All subnets allow VNet-to-VNet communication for private connectivity
5. **Documentation**: Each rule includes a description explaining its purpose

## Important Notes

### Do NOT Override Default Rules

- **AzureLoadBalancer** inbound rule (App Gateway, Container Apps)
- **Internet** outbound rule (App Gateway)

Overriding these with deny rules will break Azure platform functionality.

### DNS Resolution

- Address `168.63.129.16` is Azure DNS and must NOT be explicitly denied
- Container Apps uses this for hostname resolution

### Application Gateway

- Requires outbound Internet access for management and health monitoring
- Cannot use UDRs that block Internet access (will cause unknown backend health status)

### Private Endpoints

- NSG flow logs are NOT available for inbound traffic to private endpoints
- Effective routes/security rules are NOT displayed in Azure Portal for PE NICs

## Subnet Dependencies

```
Internet → App Gateway Subnet → Container Apps Subnet
                              ↓
                         Private Endpoints Subnet
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
            Logic Apps Subnet    Agent Subnet
```

All private communication flows through the Private Endpoints subnet, which hosts private endpoints for:

- Storage (blob, file, queue, table)
- Cosmos DB
- AI Search
- AI Foundry
- Key Vault
- Container Registry
- Logic Apps

## Variables

| Name                         | Description                                     | Required |
| ---------------------------- | ----------------------------------------------- | -------- |
| `resource_group_name`        | Resource group containing the NSGs              | Yes      |
| `nsg_id_agent`               | Resource ID of the agent subnet NSG             | Yes      |
| `nsg_id_private_endpoints`   | Resource ID of the private endpoints subnet NSG | Yes      |
| `nsg_id_logic_apps`          | Resource ID of the Logic Apps subnet NSG        | Yes      |
| `nsg_id_container_apps`      | Resource ID of the Container Apps subnet NSG    | Yes      |
| `nsg_id_app_gateway`         | Resource ID of the App Gateway subnet NSG       | Yes      |
| `subnet_id_agent`            | Resource ID of the agent subnet                 | Yes      |
| `subnet_id_private_endpoint` | Resource ID of the private endpoints subnet     | Yes      |
| `subnet_id_logic_apps`       | Resource ID of the Logic Apps subnet            | Yes      |
| `subnet_id_container_apps`   | Resource ID of the Container Apps subnet        | Yes      |
| `subnet_id_app_gateway`      | Resource ID of the App Gateway subnet           | Yes      |

## Outputs

This module does not produce outputs.

## Example Usage

```hcl
module "nsgs" {
  source = "./modules/nsgs"

  resource_group_name        = "rg-m365-agents"
  nsg_id_agent               = "/subscriptions/.../networkSecurityGroups/nsg-agent"
  nsg_id_private_endpoints   = "/subscriptions/.../networkSecurityGroups/nsg-pe"
  nsg_id_logic_apps          = "/subscriptions/.../networkSecurityGroups/nsg-logic"
  nsg_id_container_apps      = "/subscriptions/.../networkSecurityGroups/nsg-ca"
  nsg_id_app_gateway         = "/subscriptions/.../networkSecurityGroups/nsg-appgw"

  subnet_id_agent            = "/subscriptions/.../subnets/agent"
  subnet_id_private_endpoint = "/subscriptions/.../subnets/private-endpoints"
  subnet_id_logic_apps       = "/subscriptions/.../subnets/logic-apps"
  subnet_id_container_apps   = "/subscriptions/.../subnets/container-apps"
  subnet_id_app_gateway      = "/subscriptions/.../subnets/app-gateway"
}
```

## Maintenance

When updating NSG rules:

1. Review the official Microsoft documentation for the service (links provided above)
2. Test changes in a non-production environment first
3. Update both the Terraform code and this README
4. Verify service functionality after applying changes
5. Monitor Azure Monitor/Application Insights for connectivity issues

## Troubleshooting

### Container Apps not starting

- Verify outbound access to `MicrosoftContainerRegistry` and `AzureFrontDoor.FirstParty`
- Check DNS resolution (168.63.129.16 on port 53)

### Logic Apps workflows failing

- Verify outbound access to `Storage` on ports 443 and 445
- Check `AzureConnectors` service tag accessibility for managed connectors

### Application Gateway backend health unknown

- Verify `GatewayManager` inbound rule (65200-65535)
- Ensure Internet outbound is not blocked
- Check `AzureLoadBalancer` inbound rule is not denied

### Private endpoints not accessible

- Verify VNet-to-VNet communication is allowed
- Check private DNS zone configuration
- Ensure no explicit deny rules blocking VNet traffic
