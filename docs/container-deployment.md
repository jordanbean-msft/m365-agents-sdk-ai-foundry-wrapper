# M365 Agents Wrapper Container Deployment

The wrapper lives in `src/m365-agents-container` and is built into a private ACR image, then referenced by Terraform to update the Container App.

## Container App Environment

Runtime environment variables (project endpoint, model deployment name, agent id) are provisioned via Terraform (`ai_foundry_agent_id` variable and other module outputs). You do **not** need to edit `env.TEMPLATE` for these—only for local development secrets (client id/secret/tenant id).

## Build & Push Image

Build & push using exported variables (bash supports both $VAR and ${VAR}, either is fine; quoting recommended).

> ⚠️ **Platform Requirement (linux/amd64)**: Azure Container Apps currently runs containers on linux/amd64. If you build on an arm64 host (e.g. Apple Silicon) without specifying the platform, the resulting image may not run. Always force builds to `linux/amd64`.

Choose ONE of the following build approaches:

1. BuildX explicit platform:

```bash
docker buildx build --platform linux/amd64 -t "$ACR_LOGIN_SERVER/m365-agents-wrapper:v1" ./src/m365-agents-container
```

2. Single-command env override:

```bash
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker build -t "$ACR_LOGIN_SERVER/m365-agents-wrapper:v1" ./src/m365-agents-container
```

3. Session export (affects subsequent docker builds):

```bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64
docker build -t "$ACR_LOGIN_SERVER/m365-agents-wrapper:v1" ./src/m365-agents-container
```

Then push:

```bash
az acr login --name "$ACR_NAME"
docker push "$ACR_LOGIN_SERVER/m365-agents-wrapper:v1"
```

## Update Terraform with Image & Agent ID

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

## Verification

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

## Rolling Out New Versions

1. Build/tag/push new image.
2. Update `container_image` in `terraform.tfvars`.
3. `terraform apply` to update revision.

> Avoid manual image edits in the Portal; keep the registry reference declarative in Terraform.
