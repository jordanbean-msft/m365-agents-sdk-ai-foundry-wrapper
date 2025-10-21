# Azure Bot Service Module

## Overview

This module deploys an Azure Bot Service (Bot Channel Registration) configured to expose the M365 Agents Container App through Microsoft Teams and optionally Web Chat.

## Resources Created

### 1. Bot Channel Registration (`bot-{suffix}`)

- **SKU**: F0 (Free) by default, or S1 (Standard)
- **Location**: Global (Bot Service uses global location)
- **Endpoint**: Points to Container App FQDN at `/api/messages`
- **Authentication**: Microsoft Entra ID (Microsoft App ID required)

### 2. Microsoft Teams Channel

- **Purpose**: Enables bot interaction through Microsoft Teams
- **Calling Features**: Optional (disabled by default)
- **Calling Webhook**: Configurable endpoint at `/api/calling`

### 3. Web Chat Channel (Optional)

- **Purpose**: Enables bot testing through Azure Portal
- **Default**: Enabled
- **Use Case**: Development and testing without Teams client

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Microsoft Teams / Web Chat                             │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS
                     │
┌────────────────────▼────────────────────────────────────┐
│  Azure Bot Service (Global)                             │
│  - Bot Channel Registration                             │
│  - Microsoft Teams Channel                              │
│  - Web Chat Channel (optional)                          │
│                                                          │
│  Endpoint: https://{container-app-fqdn}/api/messages    │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS
                     │
┌────────────────────▼────────────────────────────────────┐
│  Container App Environment                              │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Container App (M365 Agents)                        │ │
│  │ - Ingress: External (HTTPS)                        │ │
│  │ - Endpoint: /api/messages                          │ │
│  │ - Managed Identity Authentication                  │ │
│  │ - AI Foundry Integration                           │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

### 1. Microsoft App Registration (Entra ID)

Before deploying this module, you must create a Microsoft Entra ID app registration:

**Using Azure Portal:**

1. Navigate to Azure Portal → Microsoft Entra ID → App registrations
2. Click "New registration"
3. Set a name (e.g., "M365 Agents Bot")
4. For "Supported account types", select:
   - **Multi-tenant** if bot will be used across organizations
   - **Single tenant** for internal use only
5. Leave Redirect URI blank
6. Click "Register"
7. Note the **Application (client) ID** - this is your `microsoft_app_id`
8. Navigate to "Certificates & secrets"
9. Click "New client secret"
10. Add a description and select expiration
11. Copy the secret **Value** (not the Secret ID) - this is your `microsoft_app_secret`

**Using Azure CLI:**

```bash
# Create app registration
az ad app create \
  --display-name "M365 Agents Bot" \
  --sign-in-audience AzureADMultipleOrgs

# Get the App ID
APP_ID=$(az ad app list --display-name "M365 Agents Bot" --query "[0].appId" -o tsv)

# Create client secret
az ad app credential reset \
  --id $APP_ID \
  --append \
  --years 2 \
  --display-name "Bot Secret"
```

### 2. Container App Deployment

The Container App must be deployed first with:

- External ingress enabled
- HTTPS endpoint available
- Bot framework middleware configured in the application code

## Configuration Required

### tfvars Configuration

Add the following to `terraform.tfvars`:

```hcl
# Bot Service Configuration
microsoft_app_id     = "12345678-1234-1234-1234-123456789abc"  # From App Registration
microsoft_app_secret = "your-client-secret-value"              # From App Registration
bot_sku              = "F0"                                    # F0 (Free) or S1 (Standard)
enable_bot_calling   = false                                   # Enable Teams calling features
enable_bot_webchat   = true                                    # Enable Web Chat for testing
```

### Container App Environment Variables

Ensure your Container App includes these environment variables:

```hcl
env {
  name  = "MicrosoftAppId"
  value = var.microsoft_app_id
}

env {
  name        = "MicrosoftAppPassword"
  secret_name = "microsoft-app-secret"
}

env {
  name  = "MicrosoftAppType"
  value = "MultiTenant"  # or "SingleTenant"
}

env {
  name  = "MicrosoftAppTenantId"
  value = var.tenant_id  # Required for SingleTenant
}
```

## Inputs

| Name                         | Description                                         | Type   | Required | Default |
| ---------------------------- | --------------------------------------------------- | ------ | -------- | ------- |
| `unique_suffix`              | Unique suffix for resource naming                   | string | Yes      | -       |
| `resource_group_name`        | Name of the resource group                          | string | Yes      | -       |
| `location`                   | Azure region (Bot Service itself uses 'global')     | string | Yes      | -       |
| `container_app_fqdn`         | FQDN of the Container App                           | string | Yes      | -       |
| `microsoft_app_id`           | Microsoft App ID (Client ID) for bot authentication | string | Yes      | -       |
| `sku`                        | SKU for the Bot Service (F0 or S1)                  | string | No       | "F0"    |
| `enable_calling`             | Enable calling features for Teams channel           | bool   | No       | false   |
| `enable_webchat`             | Enable Web Chat channel                             | bool   | No       | true    |
| `log_analytics_workspace_id` | Resource ID of Log Analytics Workspace              | string | No       | null    |
| `enable_diagnostics`         | Enable diagnostic settings                          | bool   | No       | true    |
| `common_tags`                | Common tags to apply to resources                   | map    | No       | {}      |

## Outputs

| Name               | Description                         |
| ------------------ | ----------------------------------- |
| `bot_id`           | ID of the Bot Service               |
| `bot_name`         | Name of the Bot Service             |
| `bot_endpoint`     | Endpoint URL of the Bot Service     |
| `microsoft_app_id` | Microsoft App ID of the Bot Service |

## Security Features

✅ **Microsoft Entra ID Authentication**

- Bot uses Microsoft Entra ID app registration
- Client ID and secret required for authentication

✅ **HTTPS Only**

- All communication over HTTPS
- Bot Service validates SSL certificates

✅ **Managed Identity Support**

- Container App uses managed identity for Azure resource access
- No credentials stored in container

✅ **Secret Management**

- Microsoft App Secret stored as Container App secret
- Not exposed in environment variables

## SKU Comparison

| Feature                   | F0 (Free)           | S1 (Standard)      |
| ------------------------- | ------------------- | ------------------ |
| **Monthly Message Limit** | 10,000 messages     | Unlimited          |
| **Channels**              | All standard        | All standard       |
| **SLA**                   | None                | 99.9%              |
| **Cost**                  | Free                | ~$0.50 per 1K msgs |
| **Best For**              | Development/Testing | Production         |

## Testing the Bot

### 1. Web Chat (Azure Portal)

1. Navigate to Azure Portal → Bot Service
2. Click "Test in Web Chat"
3. Send a message to test the bot

### 2. Microsoft Teams

1. Navigate to Azure Portal → Bot Service → Channels
2. Click on Microsoft Teams channel
3. Click "Open in Teams"
4. Start a conversation with the bot

### 3. Bot Framework Emulator

Download the [Bot Framework Emulator](https://github.com/Microsoft/BotFramework-Emulator/releases)

1. Open the emulator
2. Enter bot endpoint: `https://{container-app-fqdn}/api/messages`
3. Enter Microsoft App ID and Password
4. Click "Connect"

## Common Issues & Solutions

### Issue: "Endpoint cannot be reached"

**Causes:**

- Container App is not running
- Container App ingress is not external
- Container App does not have bot framework middleware

**Solutions:**

- Verify Container App is running: `az containerapp show -n ca-{suffix} -g {rg}`
- Ensure ingress is external: Check Container App ingress settings
- Verify bot endpoint responds: `curl https://{fqdn}/api/messages`

### Issue: "Authentication failed"

**Causes:**

- Incorrect Microsoft App ID or Secret
- App registration not configured correctly
- Secret expired

**Solutions:**

- Verify App ID matches in both Bot Service and Container App
- Check client secret is valid and not expired
- Regenerate secret if needed and update Container App secret

### Issue: "Bot doesn't respond in Teams"

**Causes:**

- Teams channel not configured
- Bot not published to Teams
- Missing bot framework SDK in container

**Solutions:**

- Verify Teams channel is created: Check Bot Service channels
- Ensure bot manifest is configured in Teams
- Check Container App logs for errors

## Monitoring & Diagnostics

### Diagnostic Settings

When `enable_diagnostics` is true, the following logs are collected:

- **BotRequest**: All requests to the bot
- **DependencyRequest**: Calls to dependent services
- **AllMetrics**: Performance metrics

### Key Metrics

- **RequestCount**: Number of bot requests
- **FailedRequests**: Failed request count
- **AverageDuration**: Average request duration
- **ThrottledRequests**: Rate-limited requests

### Log Analytics Queries

**Failed Bot Requests:**

```kusto
AzureDiagnostics
| where ResourceType == "BOTSERVICES"
| where Category == "BotRequest"
| where ResultCode >= 400
| project TimeGenerated, ResultCode, OperationName, Message
```

**Bot Response Times:**

```kusto
AzureDiagnostics
| where ResourceType == "BOTSERVICES"
| where Category == "BotRequest"
| summarize avg(DurationMs), percentiles(DurationMs, 50, 95, 99) by bin(TimeGenerated, 5m)
```

## Cost Considerations

**Bot Service F0 (Free):**

- $0/month
- 10,000 messages/month limit
- No SLA

**Bot Service S1 (Standard):**

- $0.50 per 1,000 messages
- Unlimited messages
- 99.9% SLA

**Example Monthly Costs:**

- 50,000 messages/month: $25
- 100,000 messages/month: $50
- First 10,000 messages included in S1

## Module Dependencies

```
container-apps (provides FQDN)
    │
    └─> bot-service
```

## Next Steps

### 1. Create Microsoft App Registration

Follow the prerequisites section to create the Entra ID app registration.

### 2. Configure Container App

Ensure your Container App:

- Has external ingress enabled
- Implements bot framework middleware
- Exposes `/api/messages` endpoint
- Has MicrosoftAppId and MicrosoftAppPassword configured

### 3. Update tfvars

Add the bot service configuration to `terraform.tfvars`:

```hcl
microsoft_app_id     = "your-app-id"
microsoft_app_secret = "your-app-secret"
bot_sku              = "F0"
```

### 4. Deploy

```bash
cd infra
terraform init
terraform plan
terraform apply
```

### 5. Test

1. Use Web Chat in Azure Portal
2. Add bot to Microsoft Teams
3. Send test messages

## Module Integration Example

```terraform
module "bot_service" {
  source = "./modules/bot-service"

  providers = {
    azurerm = azurerm.workload_subscription
  }

  depends_on = [
    module.container_apps
  ]

  unique_suffix          = module.foundation.unique_suffix
  resource_group_name    = var.resource_group_name_resources
  location               = var.location
  container_app_fqdn     = module.container_apps.container_app_fqdn
  microsoft_app_id       = var.microsoft_app_id
  sku                    = var.bot_sku
  enable_calling         = var.enable_bot_calling
  enable_webchat         = var.enable_bot_webchat
  log_analytics_workspace_id = var.log_analytics_workspace_id
  common_tags            = var.common_tags
  enable_diagnostics     = var.enable_diagnostics
}
```

## Additional Resources

- [Azure Bot Service Documentation](https://docs.microsoft.com/en-us/azure/bot-service/)
- [Bot Framework SDK](https://github.com/Microsoft/botframework-sdk)
- [Teams Bot Development](https://docs.microsoft.com/en-us/microsoftteams/platform/bots/what-are-bots)
- [Bot Framework Emulator](https://github.com/Microsoft/BotFramework-Emulator)
