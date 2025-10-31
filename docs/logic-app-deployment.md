# Logic App & AI Foundry Agent Deployment

The script `src/default-logic-apps-agent/create_default_logicapp_workflow.py` packages and deploys a minimal Logic App Standard workflow (HTTP trigger) and registers it as an OpenAPI tool + agent in your AI Foundry project.

## Prerequisites

| Requirement             | Notes                                                             |
| ----------------------- | ----------------------------------------------------------------- |
| Infrastructure deployed | Logic App site + AI Foundry project must exist.                   |
| Python 3.13 + `uv`      | Use provided VS Code tasks or install manually.                   |
| Azure auth              | `az login` or managed identity so `DefaultAzureCredential` works. |

## (Optional) Prepare Python Environment with Tasks

VS Code task chain:

1. Run task: `uv python install 3.13`
2. Run task: `uv venv create`
3. Run task: `uv sync (allow prerelease)`

## Execute Deployment

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

## What the Script Does

1. Zip deploys workflow files via Kudu.
2. Retrieves HTTP trigger callback URL (includes SAS signature).
3. Creates a CustomKeys connection in AI Foundry.
4. Registers an agent with OpenAPI tool referencing the workflow.
5. Emits JSON with all required values (including `ai_foundry_agent_id`).

## Verification

- Trigger URL responded with 202/200 using:
  ```bash
  curl -X POST "<callback_url_from_script>" -H 'Content-Type: application/json' -d '{"ping":"ok"}'
  ```
- Agent appears in AI Foundry portal and shows the OpenAPI tool.
