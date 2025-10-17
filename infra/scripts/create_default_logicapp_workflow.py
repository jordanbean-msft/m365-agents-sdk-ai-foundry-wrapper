#!/usr/bin/env -S uv run
"""
create_default_logicapp_workflow.py

Creates (or updates) a default Logic App Standard workflow with an HTTP request trigger
and a simple echo response so it can be invoked by an AI Foundry Agent Service.

Features:
1. Packages a minimal Logic App Standard artifact (workflow + host.json) in-memory.
2. Uses Azure management REST APIs with DefaultAzureCredential to:
   - Fetch publishing credentials for the Logic App (Standard) site.
   - Perform a Kudu Zip Deploy of the workflow definition.
   - Retrieve the callback URL for the manual (HTTP) trigger.
3. (Optional) Registers an OpenAPI tool for the workflow in an AI Foundry project so an
   AI Foundry Agent can call it directly.

Prerequisites:
- Logic App Standard environment already provisioned (site name, resource group, subscription).
- Python packages: azure-identity, requests, (optional) azure-ai-agents for --register-openapi.
- Your environment must be able to obtain an access token via DefaultAzureCredential.

Examples:
1) Using uv (recommended – resolves deps from local pyproject.toml):
    uv run create_default_logicapp_workflow.py \
      --subscription-id <SUB_ID> \
      --resource-group rg-m365-agents \
      --logic-app-name logic-1234 \
      --workflow-name AgentHttpWorkflow

2) Direct execution (after making file executable):
    chmod +x create_default_logicapp_workflow.py
    ./create_default_logicapp_workflow.py --subscription-id <SUB_ID> ...

Legacy (still works if uv not desired):
python create_default_logicapp_workflow.py \
  --subscription-id <SUB_ID> \
  --resource-group rg-m365-agents \
  --logic-app-name logic-1234 \
  --workflow-name AgentHttpWorkflow \
  --register-openapi \
  --ai-foundry-project myaiproject \
  --tool-name my_logicapp_tool

Notes:
- Re-running will overwrite the workflow definition (idempotent for this simple case).
- You can extend the workflow definition in the build_workflow_definition() function.
- Shebang now uses `uv run` so that executing the script automatically provisions an ephemeral environment based on the local pyproject.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import sys
import time
import zipfile
import traceback
from typing import Tuple

import requests
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import AzureError

# Attempt optional imports for OpenAPI tool registration
try:
    from azure.ai.agents import AgentsClient
    from azure.ai.agents.models import OpenApiTool
    _HAS_AGENTS = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_AGENTS = False

MGMT_BASE = "https://management.azure.com"
MGMT_API_VERSION_WEB = "2023-01-01"  # For publishing credentials
MGMT_API_VERSION_WORKFLOW = "2022-03-01"  # For workflow callback URL (Logic App Standard)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f"[create-workflow] {msg}")


def build_workflow_definition(workflow_name: str) -> dict:
    """Builds the Logic App Standard workflow definition.

    A simple manual HTTP trigger that echoes an input parameter.
    """
    return {
        "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2019-05-01/workflowdefinition.json#",
        "contentVersion": "1.0.0.0",
        "triggers": {
            "manual": {
                "type": "Request",
                "kind": "Http",
                "inputs": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "inputParam": {"type": "string"}
                        },
                        "required": ["inputParam"]
                    }
                }
            }
        },
        "actions": {
            "Respond": {
                "type": "Response",
                "kind": "Http",
                "inputs": {
                    "statusCode": 200,
                    "body": {
                        "echo": "@triggerBody()?['inputParam']",
                        "workflow": workflow_name,
                        "timestamp": "@utcNow()"
                    }
                },
                "runAfter": {}
            }
        },
        "outputs": {}
    }


def build_zip_package(workflow_name: str) -> bytes:
    """Constructs an in-memory ZIP suitable for Logic App Standard (single-tenant) deployment."""
    host_json = {
        "version": "2.0",
        "extensionBundle": {
            "id": "Microsoft.Azure.Functions.ExtensionBundle.Workflows",
            "version": "[1.*, 2.0.0)"
        }
    }

    workflow_content = {
        "definition": build_workflow_definition(workflow_name),
        "kind": "Stateful"
    }

    mem_file = io.BytesIO()
    with zipfile.ZipFile(mem_file, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("host.json", json.dumps(host_json, indent=2))
        # Standard layout: workflows/<name>/workflow.json
        zf.writestr(f"workflows/{workflow_name}/workflow.json", json.dumps(workflow_content, indent=2))
    mem_file.seek(0)
    return mem_file.read()


def get_access_token() -> str:
    credential = DefaultAzureCredential()
    token = credential.get_token("https://management.azure.com/.default").token
    return token


def get_publishing_credentials(subscription_id: str, resource_group: str, site_name: str, token: str) -> Tuple[str, str]:
    url = (
        f"{MGMT_BASE}/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/"
        f"Microsoft.Web/sites/{site_name}/config/publishingcredentials/list?api-version={MGMT_API_VERSION_WEB}"
    )
    resp = requests.post(url, headers={"Authorization": f"Bearer {token}"})
    if resp.status_code >= 300:
        raise RuntimeError(f"Failed to get publishing credentials: {resp.status_code} {resp.text}")
    data = resp.json()
    props = data.get("properties", {})
    user = props.get("publishingUserName")
    pwd = props.get("publishingPassword")
    if not user or not pwd:
        raise RuntimeError("Publishing credentials missing in response")
    return user, pwd


def zip_deploy(site_name: str, user: str, pwd: str, zip_bytes: bytes) -> None:
    deploy_url = f"https://{site_name}.scm.azurewebsites.net/api/zipdeploy"
    auth = base64.b64encode(f"{user}:{pwd}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}
    log("Uploading ZIP package via Kudu Zip Deploy...")
    resp = requests.post(deploy_url, headers=headers, data=zip_bytes, timeout=300)
    if resp.status_code >= 300:
        raise RuntimeError(f"Zip Deploy failed: {resp.status_code} {resp.text}")
    # Poll deployment status
    status_url = f"https://{site_name}.scm.azurewebsites.net/api/deployments/latest"
    for attempt in range(30):  # ~30 * 2s = 60s max
        time.sleep(2)
        st = requests.get(status_url, headers=headers)
        if st.status_code == 200:
            data = st.json()
            complete = data.get("complete")
            status = data.get("status")  # 4 = success
            if complete and status == 4:
                log("Deployment completed successfully.")
                return
        else:
            log(f"Polling attempt {attempt} got {st.status_code}")
    raise RuntimeError("Deployment did not complete in allotted time.")


def get_trigger_callback_url(subscription_id: str, resource_group: str, site_name: str, workflow_name: str, token: str) -> str:
    url = (
        f"{MGMT_BASE}/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/"
        f"Microsoft.Web/sites/{site_name}/hostruntime/runtime/webhooks/workflow/api/management/workflows/"
        f"{workflow_name}/triggers/manual/listCallbackUrl?api-version={MGMT_API_VERSION_WORKFLOW}"
    )
    resp = requests.post(url, headers={"Authorization": f"Bearer {token}"})
    if resp.status_code >= 300:
        raise RuntimeError(f"Failed to list callback URL: {resp.status_code} {resp.text}")
    value = resp.json().get("value")
    if not value:
        raise RuntimeError("Callback URL missing in response")
    return value


def register_openapi_tool(project: str, workflow_name: str, callback_url: str, tool_name: str) -> None:
    if not _HAS_AGENTS:
        raise RuntimeError("azure-ai-agents package not installed; cannot register OpenAPI tool.")
    log("Registering OpenAPI tool in AI Foundry project...")
    credential = DefaultAzureCredential()
    client = AgentsClient(endpoint=f"https://{project}.agents.azure.com", credential=credential)

    base_url = callback_url.split("?")[0]
    openapi_spec = {
        "openapi": "3.0.1",
        "info": {
            "title": f"Logic App Workflow {workflow_name}",
            "version": "1.0.0",
            "description": "Auto-generated OpenAPI spec for Logic App workflow HTTP trigger"
        },
        "servers": [{"url": base_url}],
        "paths": {
            "/": {
                "post": {
                    "operationId": f"invoke_{workflow_name}",
                    "summary": f"Invoke Logic App workflow {workflow_name}",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"inputParam": {"type": "string"}},
                                    "required": ["inputParam"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "sig": {"type": "apiKey", "name": "sig", "in": "query"}
            }
        },
        "security": [{"sig": []}]
    }

    tool = OpenApiTool(name=tool_name, spec=openapi_spec, description=f"Logic App workflow {workflow_name}")
    client.tools.create_or_update(project_name=project, tool=tool)
    log("OpenAPI tool registered successfully.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create / update a default Logic App Standard workflow with HTTP trigger + response.")
    p.add_argument("--subscription-id", required=True)
    p.add_argument("--resource-group", required=True)
    p.add_argument("--logic-app-name", required=True, help="Name of the Logic App Standard site (App Service)")
    p.add_argument("--workflow-name", default="AgentHttpWorkflow")
    p.add_argument("--register-openapi", action="store_true", help="Register workflow as OpenAPI tool in AI Foundry")
    p.add_argument("--ai-foundry-project", help="AI Foundry project name (required if --register-openapi)")
    p.add_argument("--tool-name", default="logicapp_workflow_tool", help="Tool name for OpenAPI registration")
    p.add_argument("--debug", action="store_true", help="Print full traceback on error for troubleshooting")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if args.register_openapi and not args.ai_foundry_project:
        log("--ai-foundry-project is required when --register-openapi is set")
        return 2

    try:
        token = get_access_token()
        log("Acquired management access token.")

        user, pwd = get_publishing_credentials(args.subscription_id, args.resource_group, args.logic_app_name, token)
        log("Retrieved publishing credentials.")

        zip_bytes = build_zip_package(args.workflow_name)
        zip_deploy(args.logic_app_name, user, pwd, zip_bytes)

        callback_url = get_trigger_callback_url(
            args.subscription_id,
            args.resource_group,
            args.logic_app_name,
            args.workflow_name,
            token,
        )
        log(f"Workflow deployed. Manual trigger callback URL:\n{callback_url}")

        if args.register_openapi:
            register_openapi_tool(
                project=args.ai_foundry_project,
                workflow_name=args.workflow_name,
                callback_url=callback_url,
                tool_name=args.tool_name,
            )

        log("Done.")
        return 0
    except AzureError as az_ex:  # Azure Identity or related SDK errors
        log(f"AzureError: {az_ex}")
        if '--debug' in argv:
            traceback.print_exc()
        return 1
    except Exception as ex:  # Catch-all
        log(f"Error: {ex}")
        if '--debug' in argv:
            traceback.print_exc()
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
