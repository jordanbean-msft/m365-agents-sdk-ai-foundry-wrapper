# M365 Agents Container - Azure AI Foundry Wrapper

This container wraps Azure AI Foundry agents for use with the Microsoft 365 Agents SDK. It provides a Bot Framework-compatible endpoint that routes messages to AI Foundry agents, with support for streaming responses, conversation management, and adaptive cards.

## What This Does

This application:

- **Wraps Azure AI Foundry agents** in the Microsoft 365 Agents SDK framework
- **Provides a Bot Framework endpoint** (`/api/messages`) compatible with Azure Bot Service
- **Streams responses** from AI Foundry agents back to users via adaptive cards
- **Manages conversation state** with automatic thread creation and reset capabilities
- **Uses managed identity authentication** for secure access to Azure AI Foundry resources
- **Supports tool calls** including code_interpreter, file_search, azure_ai_search, bing_grounding, and OpenAPI tools
- **Provides health check endpoints** for Azure Application Gateway probes
- **Works across channels** including Microsoft Teams and M365 Copilot Chat

## Prerequisites

- [Python](https://www.python.org/) version 3.13 or higher
- [uv](https://docs.astral.sh/uv/) for dependency management (recommended)
- [dev tunnel](https://learn.microsoft.com/azure/developer/dev-tunnels/get-started?tabs=windows) (for local development)
- Azure AI Foundry project with a deployed agent
- Azure Bot Service registration

## Local Setup

### 1. Configure Azure Bot Service

1. [Create an Azure Bot](https://aka.ms/AgentsSDK-CreateBot)
   - Record the **Application ID** (Client ID)
   - Record the **Tenant ID**
   - Create and record a **Client Secret**

### 2. Create Azure AI Foundry Agent

1. Create an [Azure AI Foundry project](https://ai.azure.com)
2. Deploy a model (e.g., gpt-4o)
3. Create an agent in the Agents playground
4. Record the **Agent ID** and **Project Endpoint**

### 3. Configure Environment Variables

Copy `env.TEMPLATE` to `.env` and configure:

```bash
# Bot Service Configuration
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID=<your-bot-app-id>
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET=<your-bot-client-secret>
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID=<your-tenant-id>

# Azure AI Foundry Configuration
AZURE_AI_PROJECT_ENDPOINT=<your-ai-foundry-project-endpoint>
AZURE_AI_FOUNDRY_AGENT_ID=<your-agent-id>
AZURE_AI_MODEL_DEPLOYMENT_NAME=<model-deployment-name>

# Managed Identity (for Azure deployment only)
AZURE_CLIENT_ID=<user-assigned-managed-identity-client-id>

# Optional: Application Logging
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1

# Optional: Conversation Reset Keywords (comma-separated)
RESET_COMMAND_KEYWORDS=reset,restart,new

# Optional: Application Insights
# APPLICATIONINSIGHTS_CONNECTION_STRING=<connection-string>
```

### 4. Set Up Dev Tunnel (for local development)

1. Create and host a dev tunnel:

   ```bash
   devtunnel host -p 3978 --allow-anonymous
   ```

2. Note the URL shown after `Connect via browser:`

3. Update Azure Bot messaging endpoint:
   - Go to Azure Portal → Your Bot Resource → Settings → Configuration
   - Set **Messaging endpoint** to `{tunnel-url}/api/messages`

## Running Locally

### Option 1: Using uv (Recommended)

```bash
# Install dependencies
uv sync --extra dev --prerelease=allow

# Run the application
uv run python -m src.main
```

### Option 2: Using pip

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Run the application
python -m src.main
```

You should see output similar to:

```
======== Running on http://0.0.0.0:3978 ========
(Press CTRL+C to quit)
```

The agent is ready to accept messages at `http://localhost:3978/api/messages`.

## Features

### Conversation Management

**Manual Reset**: Users can reset their conversation by sending any of the reset keywords:

```
reset, restart, new
```

These keywords are configurable via the `RESET_COMMAND_KEYWORDS` environment variable.

**Thread Persistence**: The application maintains conversation threads in memory, allowing multi-turn conversations with context retention.

**Fresh Credentials**: Each request creates fresh Azure credentials to avoid token expiration issues during long conversations.

### Response Formatting

Responses are delivered as **Adaptive Cards** with:

- Formatted agent response text
- Metadata footer showing:
  - Response time
  - Thread ID
  - Agent ID
  - Run ID
  - Token usage (total, prompt, completion)
  - Tool calls made (if any)

### Tool Support

The application automatically passes through the following tool types from AI Foundry agents:

- `code_interpreter` - Code execution
- `file_search` - File/document search
- `azure_ai_search` - Azure AI Search integration
- `bing_grounding` - Bing grounding
- `bing_custom_search` - Bing custom search
- `mcp` - Model Context Protocol
- `openapi` - OpenAPI/REST API calls

**Note**: Function tools defined in AI Foundry are currently logged but not locally implemented.

### Architecture

```
┌─────────────────┐
│  Teams/WebChat  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│   Azure Bot Service     │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Container App/Server   │
│  (This Application)     │
│                         │
│  ┌──────────────────┐   │
│  │ Bot Framework    │   │
│  │ Adapter          │   │
│  └────────┬─────────┘   │
│           │             │
│           ▼             │
│  ┌──────────────────┐   │
│  │ Agent Handlers   │   │
│  └────────┬─────────┘   │
│           │             │
│           ▼             │
│  ┌──────────────────┐   │
│  │ Azure AI Foundry │   │
│  │ Agent Client     │   │
│  └────────┬─────────┘   │
└───────────┼─────────────┘
            │
            ▼
    ┌───────────────────┐
    │ Azure AI Foundry  │
    │ Project/Agent     │
    └───────────────────┘
```

## Endpoints

### Bot Framework Endpoint

- **Path**: `/api/messages`
- **Method**: `POST`
- **Purpose**: Receives messages from Azure Bot Service
- **Authentication**: Bot Framework JWT validation

### Health Check Endpoints

The container exposes lightweight unauthenticated liveness endpoints for Azure Application Gateway health probes:

- **Paths**: `/healthz` or `/health`
- **Method**: `GET`
- **Response**: `200 OK` with JSON:
  ```json
  {
    "status": "ok",
    "service": "m365-agents",
    "time": "2025-10-29T12:34:56.789Z"
  }
  ```

Test locally:

```bash
curl -i http://localhost:3978/healthz
```

> These endpoints bypass authentication for health probe compatibility.

## Testing

### Using WebChat

1. Go to your Azure Bot Service resource in the Azure Portal
2. Select **Test in WebChat**
3. Send a message to interact with your AI Foundry agent

### Using Teams or M365 Copilot

1. **Teams**: Add your bot to Microsoft Teams via the Teams admin center, then start a chat
2. **M365 Copilot**: Enable the M365 Extensions channel in Azure Bot Service to use in Copilot Chat
3. Messages are routed through Azure Bot Service to your container

> **Note**: This bot does not send welcome messages on connection. Users can start interacting immediately by sending any message.

## Deploying to Azure

### Recommended: Using Terraform

This repository includes complete Terraform infrastructure in `infra/` that provisions:

- Azure Container Registry (ACR)
- Azure Container Apps with VNet integration
- User-assigned managed identity with proper RBAC
- Private endpoints and network security groups
- Key Vault for secrets
- Application Gateway for ingress
- AI Foundry project resources

**See the [infrastructure README](../../infra/README.md) for complete deployment instructions.**

### Quick Terraform Deployment

1. **Navigate to infrastructure directory**:

   ```bash
   cd infra
   ```

2. **Configure variables** in `terraform.tfvars`:

   ```hcl
   # See terraform.tfvars.example for all required values
   container_image = "acr<suffix>.azurecr.io/m365-agents:latest"
   ```

3. **Deploy**:

   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

4. **Build and push container image**:

   ```bash
   # From this directory (src/m365-agents-container)
   ACR_NAME=$(terraform -chdir=../../infra output -raw acr_login_server)

   # Build for linux/amd64 (required for Azure Container Apps)
   docker buildx build --platform linux/amd64 \
     -t $ACR_NAME/m365-agents:latest \
     --push .
   ```

5. **Update Container App** with the new image:
   ```bash
   cd ../../infra
   terraform apply -var="container_image=$ACR_NAME/m365-agents:latest"
   ```

### Manual Azure CLI Deployment

If not using Terraform, you can deploy manually. See the [Container Apps module README](../../infra/modules/container-apps/README.md) for step-by-step Azure CLI instructions.

### Container Image Architecture

**IMPORTANT**: Azure Container Apps runs on `linux/amd64` architecture. If you're building on an ARM-based machine (Apple Silicon, ARM laptops), you MUST specify the platform:

```bash
# Using buildx (recommended)
docker buildx build --platform linux/amd64 -t <image-name> .

# Or set default platform
export DOCKER_DEFAULT_PLATFORM=linux/amd64
docker build -t <image-name> .
```

Failure to build for the correct architecture will result in container startup failures.

## Configuration Reference

### Environment Variables

| Variable                                                  | Required | Description                                                  | Default             |
| --------------------------------------------------------- | -------- | ------------------------------------------------------------ | ------------------- |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID`     | Yes      | Azure Bot Service application (client) ID                    | -                   |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET` | Yes      | Azure Bot Service client secret                              | -                   |
| `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID`     | Yes      | Azure AD tenant ID                                           | -                   |
| `AZURE_AI_PROJECT_ENDPOINT`                               | Yes      | Azure AI Foundry project endpoint URL                        | -                   |
| `AZURE_AI_FOUNDRY_AGENT_ID`                               | Yes      | AI Foundry agent ID to use                                   | -                   |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME`                          | Yes      | Model deployment name (e.g., gpt-4o)                         | -                   |
| `AZURE_CLIENT_ID`                                         | Yes\*    | User-assigned managed identity client ID (\*Azure only)      | -                   |
| `LOG_LEVEL`                                               | No       | Python logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | `INFO`              |
| `PYTHONUNBUFFERED`                                        | No       | Disable Python output buffering                              | `1`                 |
| `RESET_COMMAND_KEYWORDS`                                  | No       | Comma-separated list of keywords to reset conversation       | `reset,restart,new` |
| `ENABLE_RESPONSE_METADATA_CARD`                           | No       | Display metadata card with timing, tokens, thread/run info   | `false`             |
| `APPLICATIONINSIGHTS_CONNECTION_STRING`                   | No       | Application Insights connection string for telemetry         | -                   |

### Project Structure

```
src/
├── main.py                 # Legacy entry point (delegates to app.bootstrap)
├── agents/
│   ├── factory.py          # AI Foundry agent creation logic
│   └── state.py            # Conversation state management
├── api/
│   ├── handlers.py         # Bot Framework message handlers
│   ├── cards.py            # Adaptive card builders
│   └── streaming.py        # Streaming response utilities
└── app/
    ├── bootstrap.py        # Application initialization
    ├── config.py           # Environment configuration
    ├── logging.py          # Logging setup
    └── server.py           # aiohttp server setup
```

## Troubleshooting

### Authentication Issues

**Problem**: `Failed to get token` or `401 Unauthorized` errors

**Solutions**:

- Verify `AZURE_CLIENT_ID` matches the user-assigned managed identity
- Ensure managed identity has "Azure AI User" role on the AI Foundry project
- Check that credentials are being refreshed (application creates fresh credentials per request)

### Agent Not Found

**Problem**: `Failed fetch Foundry agent` warnings

**Solutions**:

- Verify `AZURE_AI_FOUNDRY_AGENT_ID` is correct
- Ensure `AZURE_AI_PROJECT_ENDPOINT` matches your AI Foundry project
- Check that the agent exists in the AI Foundry portal

### Container Startup Failures

**Problem**: Container app revision fails to start

**Solutions**:

- Verify image was built for `linux/amd64` architecture
- Check environment variables are set correctly in Container App configuration
- Review container logs in Azure Portal → Container App → Revision Management → Logs

### No Response from Agent

**Problem**: Messages sent but no response received

**Solutions**:

- Check bot messaging endpoint is configured correctly in Azure Bot Service
- Verify dev tunnel is running (for local development)
- Review application logs for errors
- Test health endpoint: `curl http://localhost:3978/healthz`

## Further Reading

- [Microsoft 365 Agents SDK](https://github.com/microsoft/agents)
- [Azure AI Foundry Documentation](https://learn.microsoft.com/azure/ai-studio/)
- [Azure Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [Azure Bot Service Documentation](https://learn.microsoft.com/azure/bot-service/)
- [Adaptive Cards Documentation](https://adaptivecards.io/)
