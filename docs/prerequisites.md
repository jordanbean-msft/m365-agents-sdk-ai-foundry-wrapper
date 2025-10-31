# Prerequisites

## DNS, Domain & SSL Certificate

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

## Configure App Registration for Bot Service

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
