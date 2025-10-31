# Public Access via Application Gateway

The infrastructure provisions an Azure Application Gateway with WAF v2 to expose the Container App to the internet securely.

## Architecture

```
Internet → DNS A Record → Application Gateway (HTTPS:443) → Container App (Internal)
                              ↓
                         Bot Service
```

## Key Features

- **HTTPS Only**: Application Gateway uses the SSL certificate uploaded to Key Vault
- **WAF Protection**: OWASP 3.2 ruleset in Prevention mode
- **Internal Backend**: Container App has internal-only ingress; only App Gateway is public
- **Bot Integration**: Bot Service messaging endpoint points to Application Gateway FQDN

## DNS Configuration Required

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

## Testing HTTPS Endpoint

Once DNS is configured:

```bash
# Test HTTPS (should show valid certificate)
curl -v https://yourapp.yourdomain.com/api/messages

# Test in browser to verify certificate
# Should show your domain with valid SSL
```

## Bot Service Configuration

The Bot Service is configured with:

- **Messaging Endpoint**: `https://yourapp.yourdomain.com/api/messages`
- **OAuth Connection**: Uses the same App Registration (client ID/secret)
- **Channels Enabled**:
  - Web Chat (for testing in Azure Portal)
  - Microsoft Teams
  - M365 Extensions

## Testing the Bot

1. Go to Azure Portal → Bot Service resource
2. Click "Test in Web Chat"
3. Send a message to verify end-to-end flow
