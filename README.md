# M365 Agents SDK – AI Foundry Wrapper

![architecture](./.img/architecture.png)

This repository provisions a secure, private Azure landing zone (Storage, Cosmos DB, AI Search, AI Foundry, Logic App Standard, Container Apps, ACR) for building agent-powered Microsoft 365 integrations. All resources are deployed with network isolation (private endpoints + VNet integration) and least-privilege identities.

## Disclaimer

**THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.**

## High-Level Deployment Flow

1. **Configure App Registration** - Create and configure Azure AD App Registration for Bot Service authentication.
2. **Prepare DNS and SSL Certificate** - Configure domain, DNS A record, and obtain SSL certificate for Application Gateway.
3. **Deploy Azure Infrastructure with Terraform** - Provision all Azure resources (`infra/` root).
4. **Deploy Logic App workflow** - Register it as an OpenAPI tool in AI Foundry (Python script).
5. **Build & deploy the M365 Agents wrapper** - Push image to ACR and update Terraform.
6. **Deploy Teams App Package** - Configure and upload the Teams manifest to make the agent available in Teams.

Each stage is idempotent; infrastructure changes flow through Terraform only. Application image changes require a new build + Terraform variable update.

---

## 0. Prerequisites: DNS, Domain & SSL Certificate

Before deploying infrastructure, you must prepare the following for the Application Gateway HTTPS endpoint:

### Required Components

1. **Domain Name**: A registered domain (e.g., `yourapp.yourdomain.com`)
2. **SSL Certificate**: A valid PFX certificate for your domain with password
3. **DNS A Record**: Will be created after infrastructure deployment (pointing to Application Gateway public IP)

### Certificate Preparation

Obtain or generate a PFX certificate for your domain.

Place the PFX file in a secure location accessible during Terraform deployment.

### DNS Configuration (Post-Deployment)

After Terraform deploys the Application Gateway, you will need to:

1. Retrieve the public IP address:

   ```bash
   cd infra
   terraform output -raw application_gateway_public_ip
   ```

2. Create a DNS A record in your domain registrar/DNS provider:

   - **Name**: `yourapp` (or subdomain of choice)
   - **Type**: A
   - **Value**: `<Application_Gateway_Public_IP>`
   - **TTL**: 3600 (or as appropriate)

3. Verify DNS propagation:
   ```bash
   nslookup yourapp.yourdomain.com
   dig yourapp.yourdomain.com
   ```

> **Note**: The `bot_messaging_endpoint` variable must match your DNS A record (e.g., `https://yourapp.yourdomain.com/api/messages`)

---

## 0a. Configure App Registration for Bot Service

The Bot Service requires an Azure Active Directory (Entra ID) App Registration to authenticate users and enable OAuth connections. You must create and configure this App Registration before deploying the infrastructure.

### Create the App Registration

1. Go to [Azure Portal](https://portal.azure.com) → **Microsoft Entra ID** → **App registrations**

2. Click **New registration**

3. Configure the registration:

   - **Name**: `m365-agents-bot` (or your preferred name)
   - **Supported account types**:
     - **Accounts in this organizational directory only** (single tenant) - recommended for internal use
   - **Redirect URI**: Leave blank for now (will configure later)

4. Click **Register**

5. Note the following values (needed for Terraform):
   - **Application (client) ID** → `service_connection_client_id`
   - **Directory (tenant) ID** → `tenant_id`

### Create Client Secret

1. In your App Registration, go to **Certificates & secrets**

2. Click **New client secret**

3. Configure the secret:

   - **Description**: `bot-service-secret`
   - **Expires**: Choose appropriate expiration (e.g., 24 months)

4. Click **Add**

5. **Important**: Copy the **Value** immediately (it won't be shown again) → `service_connection_client_secret`

### Configure API Permissions

The bot needs permissions to access Microsoft Graph and other M365 services on behalf of users.

1. In your App Registration, go to **API permissions**

2. Click **Add a permission**

3. Select **Microsoft Graph** → **Delegated permissions**

4. Add the following permissions (minimum recommended):

   - `User.Read` - Sign in and read user profile
   - `openid` - OpenID Connect authentication
   - `profile` - View users' basic profile
   - `offline_access` - Maintain access to data you have given it access to

5. Click **Add permissions**

### Configure Authentication

1. In your App Registration, go to **Authentication**

2. Click **Add a platform** → **Web**

3. Add the following redirect URIs:

   ```
   https://token.botframework.com/.auth/web/redirect
   ```

4. Click **Save**

### Summary of Values for Terraform

After completing the App Registration setup, you should have:

| Terraform Variable                 | Source                                            |
| ---------------------------------- | ------------------------------------------------- |
| `service_connection_client_id`     | Application (client) ID                           |
| `service_connection_client_secret` | Client secret value (from Certificates & secrets) |
| `tenant_id`                        | Directory (tenant) ID                             |

> **Security Best Practice**: Store the client secret securely. Use environment variables or Azure Key Vault in CI/CD pipelines:
>
> ```bash
> export TF_VAR_service_connection_client_secret='<your-secret-value>'
> ```

---

## 1. Deploy Azure Infrastructure (Terraform)

### Prerequisites

| Requirement                                  | Notes                                                                                          |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Terraform >= 1.10.0                          | See `infra/versions.tf` (locked < 2.0.0).                                                      |
| Azure CLI                                    | Login with `az login` (or use managed identity in CI).                                         |
| Azure subscription & existing VNet + subnets | Subnet IDs passed via `terraform.tfvars`.                                                      |
| SSL Certificate (PFX) & Domain               | Required for Application Gateway HTTPS (see Section 0).                                        |
| Bot Service App Registration                 | Client ID and secret for bot authentication (see Section 0a).                                  |
| NSG Resources                                | Pre-existing NSGs for all subnets (agent, endpoints, logic-apps, container-apps, app-gateway). |
| (Optional) Remote state backend              | Uncomment `backend "azurerm" {}` in `infra/versions.tf`.                                       |

### Prepare Variables

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
pfx_certificate_path     = "yourapp.yourdomain.com.pfx" # Path to PFX file (see Section 0)
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

### Commands

Run all commands from `infra/`:

```bash
cd infra
terraform init
terraform validate
terraform plan -out tfplan
terraform apply tfplan
```

### Key Outputs

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

### Verification

- Check resources in Portal: https://portal.azure.com/#view/HubsExtension/BrowseResourceGroup/resourceGroup/<rg>
- Confirm private endpoints + VNet integration are provisioned.
- Ensure no public network access is enabled (Storage, Cosmos DB, AI Search, Logic App, ACR, Container Apps).
- Verify Application Gateway has public IP and HTTPS listener configured.
- **Create DNS A record** pointing your domain to the Application Gateway public IP (see Section 0).
- Test DNS resolution: `nslookup yourapp.yourdomain.com`

---

## 2. Deploy Logic App & AI Foundry Agent

The script `src/default-logic-apps-agent/create_default_logicapp_workflow.py` packages and deploys a minimal Logic App Standard workflow (HTTP trigger) and registers it as an OpenAPI tool + agent in your AI Foundry project.

### Prerequisites

| Requirement             | Notes                                                             |
| ----------------------- | ----------------------------------------------------------------- |
| Infrastructure deployed | Logic App site + AI Foundry project must exist (Step 1).          |
| Python 3.13 + `uv`      | Use provided VS Code tasks or install manually.                   |
| Azure auth              | `az login` or managed identity so `DefaultAzureCredential` works. |

### (Optional) Prepare Python Environment with Tasks

VS Code task chain:

1. Run task: `uv python install 3.13`
2. Run task: `uv venv create`
3. Run task: `uv sync (allow prerelease)`

### Execute Deployment

First export Terraform outputs to shell variables (avoids repeated subshell calls):

```bash
cd infra
SUBSCRIPTION_ID=$(terraform output -raw subscription_id)
RESOURCE_GROUP=$(terraform output -raw resource_group_name)
LOGIC_APP_NAME=$(terraform output -raw logic_app_name)
AI_FOUNDRY_PROJECT_ENDPOINT=$(terraform output -raw ai_foundry_project_endpoint)
AI_MODEL_DEPLOYMENT_NAME=$(terraform output -raw ai_model_deployment_name)
cd ..
```

Run the deployment script and capture JSON output (includes `ai_foundry_agent_id`):

```bash
cd src/default-logic-apps-agent
uv run create_default_logicapp_workflow.py \
  --subscription-id "$SUBSCRIPTION_ID" \
  --resource-group "$RESOURCE_GROUP" \
  --logic-app-name "$LOGIC_APP_NAME" \
  --workflow-name AgentHttpWorkflow \
  --ai-foundry-project-endpoint "$AI_FOUNDRY_PROJECT_ENDPOINT" \
  --ai-model-deployment-name "$AI_MODEL_DEPLOYMENT_NAME" \
  --tool-name logicapp_workflow_tool \
  > workflow_output.json

jq . workflow_output.json
AGENT_ID=$(jq -r '.ai_foundry_agent_id' workflow_output.json)
echo "Agent ID: $AGENT_ID"
```

Script actions:

1. Zip deploys workflow files via Kudu.
2. Retrieves HTTP trigger callback URL (includes SAS signature).
3. Creates a CustomKeys connection in AI Foundry.
4. Registers an agent with OpenAPI tool referencing the workflow.
5. Emits JSON with all required values (including `ai_foundry_agent_id`).

### Verification

- Trigger URL responded with 202/200 using:
  ```bash
  curl -X POST "<callback_url_from_script>" -H 'Content-Type: application/json' -d '{"ping":"ok"}'
  ```
- Agent appears in AI Foundry portal and shows the OpenAPI tool.

---

## 3. Deploy M365 Agents Wrapper (Container Apps)

The wrapper lives in `src/m365-agents-container` and is built into a private ACR image, then referenced by Terraform to update the Container App.

### Container App Environment

Runtime environment variables (project endpoint, model deployment name, agent id) are provisioned via Terraform (`ai_foundry_agent_id` variable and other module outputs). You do **not** need to edit `env.TEMPLATE` for these—only for local development secrets (client id/secret/tenant id).

### Build & Push Image

Build & push using exported variables (bash supports both $VAR and ${VAR}, either is fine; quoting recommended):

```bash
docker build -t "$ACR_LOGIN_SERVER/m365-agents-wrapper:v1" ./src/m365-agents-container
az acr login --name "$ACR_NAME"
docker push "$ACR_LOGIN_SERVER/m365-agents-wrapper:v1"
```

### Update Terraform with Image & Agent ID

Edit `infra/terraform.tfvars` to set the built image and populate `ai_foundry_agent_id` from the script output:

```hcl
container_image       = "acr1309.azurecr.io/m365-agents-wrapper:v1"  # Use your ACR login server
ai_foundry_agent_id   = "asst_ABC123..."  # From workflow_output.json
```

Apply the change:

```bash
cd infra
terraform plan -out tfplan
terraform apply tfplan
```

**Important**: After Container App is updated, verify that the bot messaging endpoint is accessible:

```bash
# Test the bot endpoint (should return 405 Method Not Allowed for GET, which is expected)
curl -v https://yourapp.yourdomain.com/api/messages
```

### Verification

- Container App revision updated: `az containerapp show -n <ca_name> -g <rg> --query properties.latestRevisionName -o tsv`
- Image digest matches pushed digest: `az containerapp show ... --query properties.template.containers[0].image`
- Test bot endpoint accessibility:
  ```bash
  curl -v https://yourapp.yourdomain.com/api/messages
  # Should return 405 Method Not Allowed for GET (POST is required)
  ```
- Verify HTTPS certificate in browser by visiting `https://yourapp.yourdomain.com`
- Test bot in Teams or Web Chat channel (configured via Bot Service in portal)
- Logs streaming (if Log Analytics enabled):
  ```bash
  az monitor log-analytics query \
  	--workspace <workspace_name_or_id> \
  	--analytics-query "ContainerAppConsoleLogs_CL | take 20"
  ```

### Rolling Out New Versions

1. Build/tag/push new image.
2. Update `container_image` in `terraform.tfvars`.
3. `terraform apply` to update revision.

> Avoid manual image edits in the Portal; keep the registry reference declarative in Terraform.

---

## 4. Public Access via Application Gateway

The infrastructure provisions an Azure Application Gateway with WAF v2 to expose the Container App to the internet securely.

### Architecture

```
Internet → DNS A Record → Application Gateway (HTTPS:443) → Container App (Internal)
                              ↓
                         Bot Service
```

### Key Features

- **HTTPS Only**: Application Gateway uses the SSL certificate uploaded to Key Vault
- **WAF Protection**: OWASP 3.2 ruleset in Prevention mode
- **Internal Backend**: Container App has internal-only ingress; only App Gateway is public
- **Bot Integration**: Bot Service messaging endpoint points to Application Gateway FQDN

### DNS Configuration Required

After deploying infrastructure, you **must** configure a DNS A record:

1. Get the Application Gateway public IP:

   ```bash
   terraform output -raw application_gateway_public_ip
   ```

2. In your DNS provider (e.g., Azure DNS, GoDaddy, Cloudflare):

   - Create an A record for your subdomain (e.g., `m365-agents`)
   - Point it to the Application Gateway public IP
   - Wait for DNS propagation (typically 5-60 minutes)

3. Verify DNS resolution:
   ```bash
   nslookup yourapp.yourdomain.com
   dig yourapp.yourdomain.com A
   ```

### Testing HTTPS Endpoint

Once DNS is configured:

```bash
# Test HTTPS (should show valid certificate)
curl -v https://yourapp.yourdomain.com/api/messages

# Test in browser to verify certificate
# Should show your domain with valid SSL
```

### Bot Service Configuration

The Bot Service is configured with:

- **Messaging Endpoint**: `https://yourapp.yourdomain.com/api/messages`
- **OAuth Connection**: Uses the same App Registration (client ID/secret)
- **Channels Enabled**:
  - Web Chat (for testing in Azure Portal)
  - Microsoft Teams
  - M365 Extensions

Test the bot:

1. Go to Azure Portal → Bot Service resource
2. Click "Test in Web Chat"
3. Send a message to verify end-to-end flow

---

## 5. Deploy Teams App Package

To make your agent available in Microsoft Teams, you need to configure and upload the Teams app manifest.

### Prerequisites

| Requirement          | Notes                                          |
| -------------------- | ---------------------------------------------- |
| Bot Service deployed | Must have Bot ID from Terraform output         |
| Teams Admin access   | Required to upload custom apps to Teams        |
| Unique App ID (GUID) | Generate a new GUID for the Teams app manifest |

### Configure the Manifest

The app package is located in `src/m365-agents-container/appPackage/` and contains:

- `manifest.json` - Teams app configuration
- `color.png` - App icon (192x192 px)
- `outline.png` - App outline icon (32x32 px)

1. Get the Bot ID from Terraform:

   ```bash
   cd infra
   BOT_ID=$(terraform output -raw bot_app_id)
   echo "Bot ID: $BOT_ID"
   ```

2. Generate a new GUID for the Teams app (or use an existing one):

   ```bash
   # Linux/macOS
   uuidgen

   # PowerShell
   [guid]::NewGuid()

   # Python
   python3 -c "import uuid; print(uuid.uuid4())"
   ```

3. Edit `src/m365-agents-container/appPackage/manifest.json` and update the following fields:

   ```json
   {
     "id": "<YOUR-NEW-GUID>",
     "developer": {
       "name": "Your Company Name",
       "websiteUrl": "https://yourcompany.com",
       "privacyUrl": "https://yourcompany.com/privacy",
       "termsOfUseUrl": "https://yourcompany.com/terms"
     },
     "name": {
       "short": "Your Agent Name",
       "full": "Your Full Agent Name"
     },
     "description": {
       "short": "Short description (max 80 chars)",
       "full": "Full description of what your agent does"
     },
     "copilotAgents": {
       "customEngineAgents": [
         {
           "type": "bot",
           "id": "<BOT-ID>" // Replace with your Bot ID
         }
       ]
     },
     "bots": [
       {
         "botId": "<BOT-ID>" // Replace with your Bot ID
         // ... rest of config
       }
     ]
   }
   ```

4. (Optional) Replace the default icons in the `appPackage/` folder:
   - `color.png` - 192x192 pixels, full color icon
   - `outline.png` - 32x32 pixels, transparent background with white outline

### Create the App Package

Package the manifest and icons into a zip file:

```bash
cd src/m365-agents-container/appPackage

# Create the zip file (manifest.zip)
zip -r ../manifest.zip manifest.json color.png outline.png

# Verify contents
unzip -l ../manifest.zip
```

The resulting `manifest.zip` file should be in `src/m365-agents-container/`.

### Upload to Teams

#### Option 1: Upload via Teams Admin Center (Recommended for Organizations)

1. Go to [Teams Admin Center](https://admin.teams.microsoft.com/)
2. Navigate to **Teams apps** → **Manage apps**
3. Click **Upload new app** or **Upload**
4. Select the `manifest.zip` file
5. Review permissions and click **Publish**

#### Option 2: Sideload via Teams Client (Development/Testing)

1. Open Microsoft Teams
2. Click **Apps** in the left sidebar
3. Click **Manage your apps** (bottom left)
4. Click **Upload an app** → **Upload a custom app**
5. Select the `manifest.zip` file
6. The app will appear in your personal apps

#### Option 3: Upload via Microsoft 365 Developer Portal

1. Go to [Teams Developer Portal](https://dev.teams.microsoft.com/apps)
2. Click **Import app**
3. Select the `manifest.zip` file
4. Review and configure additional settings if needed
5. Click **Publish** → **Publish to your org**

### Test the Teams App

1. Open Microsoft Teams
2. Search for your agent name in the Apps section
3. Click **Add** to install the app
4. Open the app and send a test message
5. Verify the agent responds correctly

## Links

- Azure Terraform Provider: https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs
- AzAPI Provider: https://registry.terraform.io/providers/Azure/azapi/latest/docs
- AI Foundry (Azure AI Project) SDK: https://learn.microsoft.com/azure/ai
- Container Apps: https://learn.microsoft.com/azure/container-apps/
