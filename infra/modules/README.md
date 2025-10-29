# Terraform Modules

This directory contains the modularized Terraform configuration for the AI Foundry infrastructure.

## Module Structure

The infrastructure is broken down into the following logical modules:

### 1. Foundation Module (`foundation/`)

Creates foundational resources needed across all other modules:

- Random string generation for unique resource naming

**Outputs:**

- `unique_suffix` - Unique suffix used for naming resources

---

### 2. Storage Module (`storage/`)

Creates all storage-related resources for agent data:

- Azure Storage Account (for blob storage)
- Azure Cosmos DB (for thread storage)
- Azure AI Search (for vector embeddings)

**Inputs:**

- `unique_suffix` - From foundation module
- `resource_group_name` - Target resource group
- `location` - Azure region
- `subscription_id` - Azure subscription ID

**Outputs:**

- Storage account details (ID, name, endpoint)
- Cosmos DB details (ID, name, endpoint)
- AI Search details (ID, name)

---

### 3. AI Foundry Module (`ai-foundry/`)

Creates the AI Foundry cognitive services account and model deployments:

- AI Foundry resource
- GPT-4o model deployment

**Inputs:**

- `unique_suffix` - From foundation module
- `resource_group_name` - Target resource group
- `location` - Azure region
- `subscription_id` - Azure subscription ID
- `subnet_id_agent` - Subnet for VNet injection

**Outputs:**

- AI Foundry resource ID and name

---

### 4. Networking Module (`networking/`)

Creates private endpoints for all resources:

- Storage Account private endpoint
- Cosmos DB private endpoint
- AI Search private endpoint
- AI Foundry private endpoint

**Inputs:**

- Resource IDs and names from storage and ai-foundry modules
- `resource_group_name` - Target resource group
- `location` - Azure region
- `subnet_id_private_endpoint` - Subnet for private endpoints

**Outputs:**

- Private endpoint IDs for all resources

---

### 5. Project Module (`project/`)

Creates the AI Foundry project and all related configurations:

- AI Foundry project
- Project connections (Storage, Cosmos DB, AI Search)
- Role assignments (control plane and data plane)
- Capability host for agents

**Inputs:**

- All outputs from storage, ai-foundry, and networking modules
- `unique_suffix` - From foundation module
- `resource_group_name` - Target resource group
- `location` - Azure region

**Outputs:**

- AI Foundry project details (ID, name, principal ID, internal ID)

---

### 6. Logic Apps Module (`logic-apps/`)

Creates Logic Apps Standard with full network isolation:

- App Service Plan (WS1 SKU)
- Logic Apps Standard (Workflow)
- Storage Account for Logic Apps
- Private endpoints for both Logic App and Storage Account
- VNet integration for outbound traffic
- System-assigned managed identity

**Inputs:**

- `unique_suffix` - From foundation module
- `resource_group_name` - Target resource group
- `location` - Azure region
- `subnet_id_logic_apps` - Subnet for Logic Apps VNet integration
- `subnet_id_private_endpoint` - Subnet for private endpoints

**Outputs:**

- Logic App details (ID, name, principal ID, hostname)
- Storage account details (ID, name)
- App Service Plan ID

**Network Configuration:**

- Public network access: Disabled
- Inbound access: Via private endpoint only
- Outbound access: Via VNet integration (route all traffic through VNet)

---

### 7. Identity Module (`identity/`)

Creates user-assigned managed identities for compute resources:

- User-assigned managed identity for Container Apps

**Inputs:**

- `unique_suffix` - From foundation module
- `resource_group_name` - Target resource group
- `location` - Azure region

**Outputs:**

- User-assigned identity details (ID, principal ID, client ID)

---

### 8. ACR Module (`acr/`)

Creates Azure Container Registry with private endpoint:

- Azure Container Registry (Premium SKU)
- Private endpoint for secure access
- AcrPull role assignment to user-assigned identity

**Inputs:**

- `unique_suffix` - From foundation module
- `resource_group_name` - Target resource group
- `location` - Azure region
- `subnet_id_private_endpoint` - Subnet for private endpoint
- `pull_principal_id` - Principal ID to grant AcrPull role

**Outputs:**

- ACR details (ID, name, login server)

---

### 9. Container Apps Module (`container-apps/`)

Creates Container App Environment and Container App with VNet integration:

- Container App Environment with workload profiles
- Container App with managed identity and AI Foundry integration
- VNet integration for secure networking
- Private registry authentication

**Inputs:**

- `unique_suffix` - From foundation module
- `resource_group_name` - Target resource group
- `location` - Azure region
- `subnet_id_container_apps` - Subnet for Container Apps
- `container_image` - Container image to deploy
- Service connection credentials
- AI Foundry configuration
- `user_assigned_identity_id` - User-assigned identity for ACR pull

**Outputs:**

- Container App Environment details (ID, name)
- Container App details (ID, name, FQDN, principal ID)

---

### 10. Bot Service Module (`bot-service/`)

Creates Azure Bot Service for exposing the M365 Agents Container App:

- Bot Channel Registration with Microsoft Entra ID authentication
- Microsoft Teams channel integration
- Optional Web Chat channel for testing
- Diagnostic settings for monitoring

**Inputs:**

- `unique_suffix` - From foundation module
- `resource_group_name` - Target resource group
- `location` - Azure region
- `container_app_fqdn` - FQDN from Container Apps module
- `microsoft_app_id` - Microsoft App ID from Entra ID app registration
- `sku` - Bot Service SKU (F0 or S1)
- `enable_calling` - Enable Teams calling features
- `enable_webchat` - Enable Web Chat channel

**Outputs:**

- Bot Service details (ID, name, endpoint, Microsoft App ID)

**Prerequisites:**

- Microsoft Entra ID app registration required before deployment
- Container App must have external ingress enabled
- Container App must implement bot framework middleware

---

### 11. NSGs Module (`nsgs/`)

Attaches existing Network Security Groups to subnets:

- Associates pre-existing NSGs with subnets
- Supports agent, private endpoints, logic-apps, and container-apps subnets
- No NSG creation (references existing by resource ID)

**Inputs:**

- Existing subnet IDs
- Existing NSG resource IDs

**Outputs:**

- NSG association IDs

---

## Module Dependencies

```
foundation
    ├── storage
    │       └── networking
    ├── ai-foundry ┘
    │           └── project
    ├── identity
    │       └── acr
    │           └── container-apps
    │                   └── bot-service
    ├── logic_apps
    └── nsgs (independent - secures existing subnets)
```

## Usage

The modules are consumed in the root `main.tf` file. Example:

```terraform
module "foundation" {
  source = "./modules/foundation"
}

module "storage" {
  source              = "./modules/storage"
  unique_suffix       = module.foundation.unique_suffix
  resource_group_name = var.resource_group_name_resources
  location            = var.location
  subscription_id     = var.subscription_id_resources
}

# ... additional modules
```

## Benefits of Modular Structure

1. **Separation of Concerns**: Each module handles a specific set of related resources
2. **Reusability**: Modules can be reused across different environments
3. **Maintainability**: Changes to one component don't affect others
4. **Testability**: Individual modules can be tested independently
5. **Clarity**: Easier to understand the infrastructure layout
6. **Security**: Dedicated NSGs attached per subnet allowing future rule hardening without impacting other network segments
