# Infrastructure Deployment (Terraform)

## Prerequisites

| Requirement                                  | Notes                                                                                          |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Terraform >= 1.10.0                          | See `infra/versions.tf` (locked < 2.0.0).                                                      |
| Azure CLI                                    | Login with `az login` (or use managed identity in CI).                                         |
| Azure subscription & existing VNet + subnets | Subnet IDs passed via `terraform.tfvars`.                                                      |
| SSL Certificate (PFX) & Domain               | Required for Application Gateway HTTPS (see [Prerequisites](prerequisites.md)).                |
| Bot Service App Registration                 | Client ID and secret for bot authentication (see [Prerequisites](prerequisites.md)).           |
| NSG Resources                                | Pre-existing NSGs for all subnets (agent, endpoints, logic-apps, container-apps, app-gateway). |
| (Optional) Remote state backend              | Uncomment `backend "azurerm" {}` in `infra/versions.tf`.                                       |

## Prepare Variables

Edit `infra/terraform.tfvars` and ensure values reflect your environment. Example (excerpt):

```hcl
resource_group_name_resources = "rg-m365-agents"
location                      = "eastus2"
subscription_id_resources     = "<SUBSCRIPTION_ID>"

# VNet Subnets (all required)
subnet_id_agent               = "/subscriptions/<SUB>/resourceGroups/rg-m365-agents/providers/Microsoft.Network/virtualNetworks/vnet-m365-agents/subnets/ai-foundry"
subnet_id_private_endpoint    = "/subscriptions/<SUB>/resourceGroups/rg-m365-agents/providers/Microsoft.Network/virtualNetworks/vnet-m365-agents/subnets/private-endpoints"
subnet_id_logic_apps          = "/subscriptions/<SUB>/resourceGroups/rg-m365-agents/providers/Microsoft.Network/virtualNetworks/vnet-m365-agents/subnets/logic-apps"
subnet_id_container_apps      = "/subscriptions/<SUB>/resourceGroups/rg-m365-agents/providers/Microsoft.Network/virtualNetworks/vnet-m365-agents/subnets/container-apps"
subnet_id_app_gateway         = "/subscriptions/<SUB>/resourceGroups/rg-m365-agents/providers/Microsoft.Network/virtualNetworks/vnet-m365-agents/subnets/application-gateway"

# Pre-existing NSGs (all required)
nsg_id_agent             = "/subscriptions/<SUB>/resourceGroups/rg-m365-agents/providers/Microsoft.Network/networkSecurityGroups/nsg-agent"
nsg_id_private_endpoints = "/subscriptions/<SUB>/resourceGroups/rg-m365-agents/providers/Microsoft.Network/networkSecurityGroups/nsg-private-endpoints"
nsg_id_logic_apps        = "/subscriptions/<SUB>/resourceGroups/rg-m365-agents/providers/Microsoft.Network/networkSecurityGroups/nsg-logic-apps"
nsg_id_container_apps    = "/subscriptions/<SUB>/resourceGroups/rg-m365-agents/providers/Microsoft.Network/networkSecurityGroups/nsg-container-apps"
nsg_id_app_gateway       = "/subscriptions/<SUB>/resourceGroups/rg-m365-agents/providers/Microsoft.Network/networkSecurityGroups/nsg-app-gateway"

# Bot Service Configuration
service_connection_client_id     = "<APP_REG_CLIENT_ID>"
service_connection_client_secret = "<APP_REG_CLIENT_SECRET>"
tenant_id                        = "<TENANT_ID>"
bot_messaging_endpoint           = "https://yourapp.yourdomain.com/api/messages" # Must match DNS A record
bot_sku                          = "S1"                                           # F0 (Free) or S1 (Standard)
enable_bot_webchat               = true
enable_bot_teams                 = true
enable_bot_m365                  = true

# Application Gateway HTTPS Certificate
pfx_certificate_path     = "yourapp.yourdomain.com.pfx" # Path to PFX file
pfx_certificate_password = "<CERTIFICATE_PASSWORD>"     # Use env var: export TF_VAR_pfx_certificate_password='...'
appgw_certificate_name   = "appgw-cert"

# Container Image (placeholder; will update after build)
container_image = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"

# Existing Monitoring Resources
log_analytics_workspace_id = "/subscriptions/<SUB>/resourceGroups/rg-m365-agents/providers/Microsoft.OperationalInsights/workspaces/law-m365-agents"
application_insights_id    = "/subscriptions/<SUB>/resourceGroups/rg-m365-agents/providers/microsoft.insights/components/appi-m365-agents"

# Optional Settings
enable_diagnostics               = true
logic_apps_website_dns_server    = "10.255.1.4" # Custom DNS if needed
log_level                        = "INFO"
conversation_timeout_seconds     = 60
reset_command_keywords           = "reset,restart,new"

common_tags = {
	environment = "dev"
	owner       = "platform-team"
	project     = "m365-agents"
}
```

> **Security note**: Keep secrets in secure variable stores in CI/CD; avoid committing plaintext credentials. Use environment variables for sensitive values:
>
> ```bash
> export TF_VAR_service_connection_client_secret='<secret>'
> export TF_VAR_pfx_certificate_password='<password>'
> ```

## Deploy

Run all commands from `infra/`:

```bash
cd infra
terraform init
terraform validate
terraform plan -out tfplan
terraform apply tfplan
```

## Key Outputs

After apply:

```bash
terraform output -json | jq
terraform output -raw ai_foundry_project_endpoint
terraform output -raw logic_app_name
terraform output -raw ai_model_deployment_name
terraform output -raw application_gateway_public_ip  # Use this for DNS A record
terraform output -raw bot_app_id
```

Export key outputs for later steps:

```bash
# ACR outputs for image build/push
ACR_LOGIN_SERVER=$(terraform -chdir=infra output -raw acr_login_server)
ACR_NAME=$(terraform -chdir=infra output -raw acr_name)
echo "Registry: $ACR_LOGIN_SERVER (name: $ACR_NAME)"

# Application Gateway public IP for DNS configuration
APP_GATEWAY_IP=$(terraform -chdir=infra output -raw application_gateway_public_ip)
echo "Configure DNS A record to point to: $APP_GATEWAY_IP"
```

## Verification

- Check resources in Portal: https://portal.azure.com/#view/HubsExtension/BrowseResourceGroup/resourceGroup/<rg>
- Confirm private endpoints + VNet integration are provisioned.
- Ensure no public network access is enabled (Storage, Cosmos DB, AI Search, Logic App, ACR, Container Apps).
- Verify Application Gateway has public IP and HTTPS listener configured.
- **Create DNS A record** pointing your domain to the Application Gateway public IP (see [Prerequisites](prerequisites.md)).
- Test DNS resolution: `nslookup yourapp.yourdomain.com`
