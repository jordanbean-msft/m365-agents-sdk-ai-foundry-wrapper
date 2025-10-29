# Azure Container Apps Module

## Overview

This module deploys an Azure Container App Environment with VNet integration using workload profiles, along with a Container App configured with environment variables for AI Foundry integration.

## Resources Created

### 1. Container App Environment (`cae-{suffix}`)

- **VNet Integration**: Connected to dedicated subnet
- **Internal Load Balancer**: Enabled
- **Workload Profile**: Consumption (for VNet integration)

### 2. Container App (`ca-{suffix}`)

- **Revision Mode**: Single
- **Workload Profile**: Consumption
- **Identity**: System-assigned managed identity enabled
- **Scaling**: 0-10 replicas
- **Resources**: 1 vCPU, 2Gi memory (supports private image pulls)

### 3. User Assigned Managed Identity (`uami-containerapps-{suffix}`)

- **Purpose**: Used for authenticating to private Azure Container Registry without admin credentials
- **Attached To**: Container App (alongside system-assigned identity)

### 4. Azure Container Registry (`acr{suffix}`)

- **SKU**: Basic (default, configurable in module)
- **Admin User**: Disabled (best practice)
- **AcrPull Role**: Granted automatically to the User Assigned Managed Identity

## Environment Variables Configuration

The Container App is configured with the following environment variables:

| Variable                                                  | Source                   | Description                        |
| --------------------------------------------------------- | ------------------------ | ---------------------------------- |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID`     | tfvars                   | Service connection client ID       |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET` | tfvars (secret)          | Service connection client secret   |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID`     | tfvars                   | Azure AD tenant ID                 |
| `AZURE_AI_PROJECT_ENDPOINT`                               | AI Foundry module output | AI Foundry project endpoint        |
| `AZURE_AI_FOUNDRY_AGENT_ID`                               | tfvars                   | AI Foundry agent ID                |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME`                          | ai-foundry module output | Model deployment name (dynamic)    |
| `AZURE_CLIENT_ID`                                         | tfvars                   | Azure client ID for authentication |
| `REGISTRY_SERVER`                                         | ACR module output        | Container registry login server    |

## Network Architecture

```
┌─────────────────────────────────────────────────────┐
│  Virtual Network                                     │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │ Container Apps Subnet                          │ │
│  │                                                │ │
│  │  ┌──────────────────────────────────────────┐ │ │
│  │  │ Container App Environment                │ │ │
│  │  │                                          │ │ │
│  │  │  ┌────────────────────────────────────┐ │ │ │
│  │  │  │ Container App                      │ │ │ │
│  │  │  │ - System Managed Identity          │ │ │ │
│  │  │  │ - Environment Variables Configured │ │ │ │
│  │  │  │ - Internal Load Balancer          │ │ │ │
│  │  │  └────────────────────────────────────┘ │ │ │
│  │  └──────────────────────────────────────────┘ │ │
│  │                                                │ │
│  │  Workload Profile: Consumption                 │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Subnet Requirements

### New Subnet Required

You need to create a new subnet in your VNet for Container Apps:

**Subnet Properties:**

- Name: `container-apps` (or your preferred name)
- Address space: Minimum /23 (512 IPs recommended for production)
- Delegation: Not required (Container Apps manages this)
- Service Endpoints: Not required
- Network Policies: Can be enabled

**Important:** Container App Environments require a minimum of /27 subnet, but /23 is recommended for production workloads to allow for scaling.

## Configuration Required

### tfvars Configuration

You must set the following values in `terraform.tfvars`:

```hcl
# Subnet for Container Apps
subnet_id_container_apps = "/subscriptions/{subscription-id}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{vnet}/subnets/container-apps"

# Service Connection Settings
service_connection_client_id     = "your-client-id"
service_connection_client_secret = "your-client-secret"  # Stored as secret
tenant_id                        = "your-tenant-id"

# AI Configuration
ai_foundry_agent_id = "your-agent-id"
azure_client_id     = "your-azure-client-id"

# Container Image (optional - defaults to hello world)
container_image = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
```

## Inputs

| Name                               | Description                              | Type               | Required                |
| ---------------------------------- | ---------------------------------------- | ------------------ | ----------------------- |
| `unique_suffix`                    | Unique suffix for resource naming        | string             | Yes                     |
| `resource_group_name`              | Resource group name                      | string             | Yes                     |
| `location`                         | Azure region                             | string             | Yes                     |
| `subnet_id_container_apps`         | Subnet ID for Container Apps Environment | string             | Yes                     |
| `container_image`                  | Container image to deploy                | string             | No (has default)        |
| `service_connection_client_id`     | Service connection client ID             | string             | Yes                     |
| `service_connection_client_secret` | Service connection client secret         | string (sensitive) | Yes                     |
| `tenant_id`                        | Azure AD tenant ID                       | string             | Yes                     |
| `ai_project_endpoint`              | AI Foundry project endpoint              | string             | Yes (from module)       |
| `ai_foundry_agent_id`              | AI Foundry agent ID                      | string             | Yes                     |
| `ai_model_deployment_name`         | AI model deployment name                 | string             | No (defaults to gpt-4o) |
| `azure_client_id`                  | Azure client ID                          | string             | Yes                     |

## Outputs

| Name                             | Description                                    |
| -------------------------------- | ---------------------------------------------- |
| `container_app_environment_id`   | ID of the Container App Environment            |
| `container_app_environment_name` | Name of the Container App Environment          |
| `container_app_id`               | ID of the Container App                        |
| `container_app_name`             | Name of the Container App                      |
| `container_app_principal_id`     | Principal ID of the managed identity           |
| `container_app_fqdn`             | FQDN of the Container App (if ingress enabled) |

## Security Features

✅ **VNet Integration**

- Dedicated subnet for Container App Environment
- Internal load balancer enabled
- Workload profile for secure networking

✅ **Managed Identity**

- Dual identity: System-assigned + User Assigned
- User Assigned identity granted AcrPull on ACR
- No registry admin credentials required

✅ **Secret Management**

- Client secret stored as Container App secret
- Not exposed in environment variables

✅ **Private Image Pulls**

- Azure Container Registry integrated using user-assigned identity
- `registry` block configured with identity-based auth (no secrets)

## Ingress Configuration

By default, ingress is configured as:

- **External Access**: Disabled (internal only)
- **Target Port**: 80
- **Traffic**: 100% to latest revision

You can modify the ingress settings in the module if needed, or disable it completely if the Container App doesn't need to receive HTTP requests.

## Scaling

The Container App is configured with:

- **Min Replicas**: 0 (can scale to zero)
- **Max Replicas**: 10

This allows the app to scale down to zero when not in use (saving costs) and scale up to 10 replicas based on demand.

## Next Steps

### 1. Create the Container Apps Subnet

Create a subnet in your VNet:

- Minimum /27, recommended /23
- No delegation required
- Ensure sufficient IP address space

### 2. Configure Variables

Update `terraform.tfvars` with:

- Service connection credentials
- Tenant ID
- AI Foundry agent ID
- Azure client ID
- Container image (optional)

### 3. Deploy

```bash
terraform init
terraform plan
terraform apply
```

### 4. Grant Permissions

After deployment, grant the Container App's managed identity access to:

- AI Foundry resources
- Any other Azure resources it needs to access

## Cost Considerations

**Container App Environment**: ~$0 (no charge for environment itself)
**Container Apps**: Pay-per-use consumption model

- vCPU: ~$0.000024/vCPU-second
- Memory: ~$0.000002/GiB-second
- Scales to zero when not in use

**Total Estimated Monthly Cost**: Often <$5 at low/idle usage (Container App + ACR Basic). Image storage & network egress extra.

## Module Interaction Overview

```
┌──────────────────────────────────────────────────────────┐
│ foundation (random suffix)                              │
└───────────────┬──────────────────────────────────────────┘
		│ unique_suffix
	┌───────▼────────┐          ┌───────────────────────┐
	│ identity       │          │ acr                  │
	│ uami-container │          │ acr{suffix}          │
	└───────┬────────┘          └───────────┬──────────┘
		│ principal_id (AcrPull)         │ login_server
		└──────────────┬────────────────┘
			       │
			┌──────▼─────────────────────────────┐
			│ container-apps module              │
			│ - Environment (VNet)               │
			│ - Container App (identities)       │
			│ - Registry block (identity auth)   │
			└────────────────────────────────────┘
```

## Using a Private Image

Set in `terraform.tfvars` (example):

```hcl
container_image = "${module.acr.acr_login_server}/myrepo/agent-app:1.0.0"
```

Ensure the repository exists or push after ACR creation:

```bash
az acr login --name acr<suffix>
docker build -t acr<suffix>.azurecr.io/myrepo/agent-app:1.0.0 .
docker push acr<suffix>.azurecr.io/myrepo/agent-app:1.0.0
```

The Container App will pull using the user-assigned identity—no username/password needed.
