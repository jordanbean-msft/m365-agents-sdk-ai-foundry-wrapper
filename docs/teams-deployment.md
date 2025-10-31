# Teams App Package Deployment

To make your agent available in Microsoft Teams, you need to configure and upload the Teams app manifest.

## Prerequisites

| Requirement          | Notes                                          |
| -------------------- | ---------------------------------------------- |
| Bot Service deployed | Must have Bot ID from Terraform output         |
| Teams Admin access   | Required to upload custom apps to Teams        |
| Unique App ID (GUID) | Generate a new GUID for the Teams app manifest |

## Configure the Manifest

The app package is located in `src/m365-agents-container/appPackage/` and contains:

- `manifest.json` - Teams app configuration
- `color.png` - App icon (192x192 px)
- `outline.png` - App outline icon (32x32 px)

### Steps

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

## Create the App Package

Package the manifest and icons into a zip file:

```bash
cd src/m365-agents-container/appPackage

# Create the zip file (manifest.zip)
zip -r ../manifest.zip manifest.json color.png outline.png

# Verify contents
unzip -l ../manifest.zip
```

The resulting `manifest.zip` file should be in `src/m365-agents-container/`.

## Upload to Teams

### Option 1: Upload via Teams Admin Center (Recommended for Organizations)

1. Go to [Teams Admin Center](https://admin.teams.microsoft.com/)
2. Navigate to **Teams apps** → **Manage apps**
3. Click **Upload new app** or **Upload**
4. Select the `manifest.zip` file
5. Review permissions and click **Publish**

### Option 2: Sideload via Teams Client (Development/Testing)

1. Open Microsoft Teams
2. Click **Apps** in the left sidebar
3. Click **Manage your apps** (bottom left)
4. Click **Upload an app** → **Upload a custom app**
5. Select the `manifest.zip` file
6. The app will appear in your personal apps

### Option 3: Upload via Microsoft 365 Developer Portal

1. Go to [Teams Developer Portal](https://dev.teams.microsoft.com/apps)
2. Click **Import app**
3. Select the `manifest.zip` file
4. Review and configure additional settings if needed
5. Click **Publish** → **Publish to your org**

## Test the Teams App

1. Open Microsoft Teams
2. Search for your agent name in the Apps section
3. Click **Add** to install the app
4. Open the app and send a test message
5. Verify the agent responds correctly
