# Streaming Agent

This is a sample of a simple Agent that is hosted on a Python web service. The sample demonstrates how to stream responses, specifically with streamed OpenAI calls.

## Prerequisites

- [Python](https://www.python.org/) version 3.9 or higher
- [dev tunnel](https://learn.microsoft.com/azure/developer/dev-tunnels/get-started?tabs=windows) (for local development)
- You will need an Azure OpenAI, with the preferred model of `gpt-4o-mini`.

## Local Setup

### Configure Azure Bot Service

1. [Create an Azure Bot](https://aka.ms/AgentsSDK-CreateBot)

   - Record the Application ID, the Tenant ID, and the Client Secret for use below

1. Configuring the token connection in the Agent settings

   1. Open the `env.TEMPLATE` file in the root of the sample project, rename it to `.env` and configure the following values:
   1. Set the **CONNECTIONS**SERVICE_CONNECTION**SETTINGS\_\_CLIENTID** to the AppId of the bot identity.
   1. Set the **CONNECTIONS**SERVICE*CONNECTION**SETTINGS\_\_CLIENTSECRET** to the Secret that was created for your identity. \_This is the `Secret Value` shown in the AppRegistration*.
   1. Set the **CONNECTIONS**SERVICE_CONNECTION**SETTINGS\_\_TENANTID** to the Tenant Id where your application is registered.

1. Configure the Azure OpenAI settings in the Agent settings

   1. Set **AZURE_OPENAI_API_VERSION** to an OpenAI API version such as ` 2025-01-01-preview`
   1. Set **AZURE_OPENAI_ENDPOINT** to the endpoint for your Azure OpenAI instance. For example, if using an Azure AI Foundry named `testing`, the endpoint would be `https://endpoint.openai.azure.com/`

1. Run `dev tunnels`. See [Create and host a dev tunnel](https://learn.microsoft.com/azure/developer/dev-tunnels/get-started?tabs=windows) and host the tunnel with anonymous user access command as shown below:

   ```bash
   devtunnel host -p 3978 --allow-anonymous
   ```

1. Take note of the url shown after `Connect via browser:`

1. On the Azure Bot, select **Settings**, then **Configuration**, and update the **Messaging endpoint** to `{tunnel-url}/api/messages`

### Running the Agent

1. Open this folder from your IDE or Terminal of preference
1. (Optional but recommended) Set up virtual environment and activate it.
1. Install dependencies

```sh
pip install -r requirements.txt
```

### Run in localhost, anonymous mode

1. Start the application

```sh
python -m src.main
```

At this point you should see the message

```text
======== Running on http://localhost:3978 ========
```

The agent is ready to accept messages.

## Conversation Management (Reset, Timeout & Adaptive Card)

This container supports conversation lifecycle controls so users in Microsoft
Teams (or other Bot Framework channels) can intentionally or automatically
start fresh.

### Manual Reset

Send one of the reset keywords (case-insensitive, message must ONLY contain
the keyword) to clear the current conversation state:

```
reset, restart, new
```

After a reset an Adaptive Card is returned with a "Restart Conversation"
button (it simply re-sends the first reset keyword so behavior stays uniform).

### Inactivity Timeout

Set `CONVERSATION_TIMEOUT_SECONDS` (env var) to a positive integer to enable
automatic expiration. On the next inbound message AFTER the timeout window:

1. Prior conversation state (agent, thread, tool resources, timestamps) is cleared.
2. An Adaptive Card informs the user the session expired.
3. The current message is processed as the FIRST message of a new session.

Set to `0` (default) to disable.

### Environment Variables

| Variable                       | Purpose                                        | Default             |
| ------------------------------ | ---------------------------------------------- | ------------------- |
| `RESET_COMMAND_KEYWORDS`       | Comma‑separated list of reset trigger keywords | `reset,restart,new` |
| `CONVERSATION_TIMEOUT_SECONDS` | Inactivity seconds before auto-reset           | `0` (off)           |

### Adaptive Card Customization

The JSON payload is constructed in `_build_reset_adaptive_card` (see
`src/agent.py`). Modify that helper to change wording, branding, or add
additional actions (e.g., Help, FAQ).

### Notes

- Conversation state is currently in-memory; use a distributed cache (Redis,
  Cosmos DB, etc.) if you need durability or horizontal scale.
- Timeout evaluation is lazy (performed only when a new message arrives).
- Manual resets and timeouts are per-conversation; other conversations are
  unaffected.

## Health Check Endpoint

The container exposes a lightweight unauthenticated liveness endpoint used by the Azure Application Gateway health probe:

- Path: `/healthz` (alias `/health`)
- Method: `GET`
- Response: `200 OK` with JSON body: `{ "status": "ok", "service": "m365-agents", "time": "<UTC ISO8601>" }`
- Purpose: Quickly indicate the process is running without invoking downstream services.

If you test locally:

```bash
curl -i http://localhost:3978/healthz
```

You should see `HTTP/1.1 200 OK` and the JSON payload.

> This endpoint bypasses JWT auth so the Application Gateway probe can succeed.

## Accessing the Agent

### Using the Agent in WebChat

1. Go to your Azure Bot Service resource in the Azure Portal and select **Test in WebChat**

## Deploying to Azure Container Apps

### 0. (Optional) Set All Common Variables

```bash
# Set a common suffix for all resources
SUFFIX="testlaw"  # Change this to your preferred unique suffix

# Generate names for Azure resources using the suffix
RESOURCE_GROUP="rg-$SUFFIX"
LOCATION="eastus2"  # Change as needed
LOG_ANALYTICS_NAME="log-$SUFFIX"
IDENTITY_NAME="id-$SUFFIX"
ACR_NAME="acr$SUFFIX"  # ACR names must be globally unique and only lowercase letters/numbers
APP_NAME="app-$SUFFIX"
CONTAINERAPPS_ENVIRONMENT="cae-$SUFFIX"
IMAGE_NAME="image-$SUFFIX"
IMAGE_TAG="v1"  # Change as needed

# Set environment variable values as needed
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID=<client-id>
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET=<client-secret>
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID=<tenant-id>
AZURE_AI_PROJECT_ENDPOINT=<project-endpoint>
AZURE_AI_FOUNDRY_AGENT_ID=<agent-id>
AZURE_AI_MODEL_DEPLOYMENT_NAME=<model-deployment-name>
AZURE_AI_RESOURCE_ID=<AZURE_AI_RESOURCE_ID>
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
```

### 1. Create Resource Group

```bash
az group create --name $RESOURCE_GROUP --location $LOCATION
```

### 2. Create Log Analytics Workspace

```bash
az monitor log-analytics workspace create \
   --resource-group $RESOURCE_GROUP \
   --workspace-name $LOG_ANALYTICS_NAME \
   --location $LOCATION

LOG_ANALYTICS_WORKSPACE_ID=$(az monitor log-analytics workspace show \
   --resource-group $RESOURCE_GROUP \
   --workspace-name $LOG_ANALYTICS_NAME \
   --query customerId -o tsv)
LOG_ANALYTICS_WORKSPACE_KEY=$(az monitor log-analytics workspace get-shared-keys \
   --resource-group $RESOURCE_GROUP \
   --workspace-name $LOG_ANALYTICS_NAME \
   --query primarySharedKey -o tsv)
```

### 3. Create User-Assigned Managed Identity

```bash
az identity create \
   --name $IDENTITY_NAME \
   --resource-group $RESOURCE_GROUP \
   --location $LOCATION

IDENTITY_PRINCIPAL_ID=$(az identity show \
   --name $IDENTITY_NAME \
   --resource-group $RESOURCE_GROUP \
   --query 'principalId' -o tsv)
IDENTITY_CLIENT_ID=$(az identity show \
   --name $IDENTITY_NAME \
   --resource-group $RESOURCE_GROUP \
   --query 'clientId' -o tsv)
```

### 4. Create Azure Container Registry (ACR)

```bash
az acr create \
   --resource-group $RESOURCE_GROUP \
   --name $ACR_NAME \
   --sku Basic
```

### 5. Grant Roles to Managed Identity

```bash
# Grant Azure AI User role
az role assignment create \
   --assignee $IDENTITY_PRINCIPAL_ID \
   --role "Azure AI User" \
   --scope $AZURE_AI_RESOURCE_ID

# Grant AcrPull role
ACR_ID=$(az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query id -o tsv)
az role assignment create \
   --assignee $IDENTITY_PRINCIPAL_ID \
   --role "AcrPull" \
   --scope $ACR_ID
```

### 6. Login to ACR

```bash
az acr login --name $ACR_NAME
```

### 7. Create Azure Container Apps Environment

```bash
az containerapp env create \
   --name $CONTAINERAPPS_ENVIRONMENT \
   --resource-group $RESOURCE_GROUP \
   --location $LOCATION \
   --logs-workspace-id $LOG_ANALYTICS_WORKSPACE_ID \
   --logs-workspace-key $LOG_ANALYTICS_WORKSPACE_KEY
```

### 8. Build and Push the Container Image

```bash
az acr build --registry $ACR_NAME --image $IMAGE_NAME:$IMAGE_TAG .
```

### 9. Deploy to Azure Container Apps (with Managed Identity)

```bash
az containerapp create \
   --name $APP_NAME \
   --resource-group $RESOURCE_GROUP \
   --environment $CONTAINERAPPS_ENVIRONMENT \
   --image $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG \
   --target-port 3978 \
   --ingress 'external' \
   --min-replicas 1 \
   --user-assigned /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ManagedIdentity/userAssignedIdentities/$IDENTITY_NAME \
   --registry-server $ACR_NAME.azurecr.io \
   --registry-identity /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.ManagedIdentity/userAssignedIdentities/$IDENTITY_NAME \
   --env-vars \
      CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID=$CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID \
      CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET=$CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET \
      CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID=$CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID \
      AZURE_AI_PROJECT_ENDPOINT=$AZURE_AI_PROJECT_ENDPOINT \
      AZURE_AI_FOUNDRY_AGENT_ID=$AZURE_AI_FOUNDRY_AGENT_ID \
      AZURE_AI_MODEL_DEPLOYMENT_NAME=$AZURE_AI_MODEL_DEPLOYMENT_NAME \
      AZURE_CLIENT_ID=$IDENTITY_CLIENT_ID
```

> **Note:**
>
> - Make sure your Container App has access to the Azure resources it needs (e.g., via a managed identity or network rules).
> - Update the port if your app listens on a different port.

## Further reading

To learn more about building Agents, see our [Microsoft 365 Agents SDK](https://github.com/microsoft/agents) repo.

For more information on logging configuration, see the logging section in the Quickstart Agent sample README.
