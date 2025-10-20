# M365 Agents SDK – AI Foundry Wrapper

![architecture](./.img/architecture.png)

This repository provisions a secure, private Azure landing zone (Storage, Cosmos DB, AI Search, AI Foundry, Logic App Standard, Container Apps, ACR) for building agent-powered Microsoft 365 integrations. All resources are deployed with network isolation (private endpoints + VNet integration) and least-privilege identities.

## Disclaimer

**THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.**

## High-Level Deployment Flow

1. Deploy Azure Infrastructure with Terraform (`infra/` root).
2. Deploy Logic App workflow + register it as an OpenAPI tool in AI Foundry (Python script).
3. Build & deploy the M365 Agents wrapper to Azure Container Apps (push image to ACR, update Terraform).

Each stage is idempotent; infrastructure changes flow through Terraform only. Application image changes require a new build + Terraform variable update.

---

## 1. Deploy Azure Infrastructure (Terraform)

### Prerequisites

| Requirement                                  | Notes                                                    |
| -------------------------------------------- | -------------------------------------------------------- |
| Terraform >= 1.10.0                          | See `infra/versions.tf` (locked < 2.0.0).                |
| Azure CLI                                    | Login with `az login` (or use managed identity in CI).   |
| Azure subscription & existing VNet + subnets | Subnet IDs passed via `terraform.tfvars`.                |
| (Optional) Remote state backend              | Uncomment `backend "azurerm" {}` in `infra/versions.tf`. |

### Prepare Variables

Edit `infra/terraform.tfvars` and ensure values reflect your environment. Example (excerpt):

```hcl
resource_group_name_resources = "rg-m365-agents"
location                      = "eastus2"
subscription_id_resources     = "<SUBSCRIPTION_ID>"
subnet_id_agent               = "/subscriptions/<SUB>/resourceGroups/rg-m365-agents/providers/Microsoft.Network/virtualNetworks/vnet-m365-agents/subnets/ai-foundry"
subnet_id_private_endpoint    = "/subscriptions/<SUB>/resourceGroups/rg-m365-agents/providers/Microsoft.Network/virtualNetworks/vnet-m365-agents/subnets/private-endpoints"
subnet_id_logic_apps          = "/subscriptions/<SUB>/resourceGroups/rg-m365-agents/providers/Microsoft.Network/virtualNetworks/vnet-m365-agents/subnets/logic-apps"
subnet_id_container_apps      = "/subscriptions/<SUB>/resourceGroups/rg-m365-agents/providers/Microsoft.Network/virtualNetworks/vnet-m365-agents/subnets/container-apps"
service_connection_client_id  = "<APP_REG_CLIENT_ID>"
service_connection_client_secret = "<APP_REG_CLIENT_SECRET>"
tenant_id                     = "<TENANT_ID>"
container_image               = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest" # will replace later
enable_diagnostics            = false
common_tags = {
	environment = "dev"
	owner       = "platform-team"
	project     = "m365-agents"
}
```

> Security note: keep secrets in secure variable stores in CI/CD; avoid committing plaintext credentials.

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
```

Export ACR outputs for later image build/push:

```bash
ACR_LOGIN_SERVER=$(terraform -chdir=infra output -raw acr_login_server)
ACR_NAME=$(terraform -chdir=infra output -raw acr_name)
echo "Registry: $ACR_LOGIN_SERVER (name: $ACR_NAME)"
```

### Verification

- Check resources in Portal: https://portal.azure.com/#view/HubsExtension/BrowseResourceGroup/resourceGroup/<rg>
- Confirm private endpoints + VNet integration are provisioned.
- Ensure no public network access is enabled (Storage, Cosmos DB, AI Search, Logic App, ACR, Container Apps).

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
  --ai-foundry-project "$AI_FOUNDRY_PROJECT_ENDPOINT" \
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
container_image       = "${acr_login_server}/m365-agents-wrapper:v1"
ai_foundry_agent_id   = "${AGENT_ID}"
```

Apply the change:

```bash
cd infra
terraform plan -out tfplan
terraform apply tfplan
```

### Verification

- Container App revision updated: `az containerapp show -n <ca_name> -g <rg> --query properties.latestRevisionName -o tsv`
- Image digest matches pushed digest: `az containerapp show ... --query properties.template.containers[0].image`
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

## Links

- Azure Terraform Provider: https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs
- AzAPI Provider: https://registry.terraform.io/providers/Azure/azapi/latest/docs
- AI Foundry (Azure AI Project) SDK: https://learn.microsoft.com/azure/ai
- Container Apps: https://learn.microsoft.com/azure/container-apps/
