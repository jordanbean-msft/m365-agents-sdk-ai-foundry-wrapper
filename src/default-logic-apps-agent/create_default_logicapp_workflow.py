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
import traceback
import zipfile
from pathlib import Path
from typing import Tuple

import requests
from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential

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


def load_workflow_template() -> dict:
    """Load the workflow definition from the external JSON file."""
    script_dir = Path(__file__).parent
    workflow_file = script_dir / "workflow_definition.json"

    if not workflow_file.exists():
        raise FileNotFoundError(f"Workflow definition file not found: {workflow_file}")

    with open(workflow_file, 'r') as f:
        return json.load(f)


def build_workflow_definition(workflow_name: str) -> dict:
    """Builds the Logic App Standard workflow definition.

    Loads from external JSON template and customizes with workflow name.
    """
    template = load_workflow_template()

    # Customize the response body to include the workflow name
    if "definition" in template and "actions" in template["definition"]:
        if "Respond" in template["definition"]["actions"]:
            template["definition"]["actions"]["Respond"]["inputs"]["body"]["workflow"] = workflow_name

    return template["definition"]


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
        zf.writestr(f"workflows/{workflow_name}/workflow.json",
                    json.dumps(workflow_content, indent=2))
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


def load_openapi_template() -> dict:
    """Load the OpenAPI spec template from the external JSON file."""
    script_dir = Path(__file__).parent
    openapi_file = script_dir / "openapi_spec_template.json"

    if not openapi_file.exists():
        raise FileNotFoundError(
            f"OpenAPI spec template file not found: {openapi_file}"
        )

    with open(openapi_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_openapi_spec(workflow_name: str, callback_url: str) -> dict:
    """Build the OpenAPI spec by customizing the template.

    Args:
        workflow_name: Name of the Logic App workflow
        callback_url: Full callback URL including signature

    Returns:
        Customized OpenAPI specification
    """
    spec = load_openapi_template()
    base_url = callback_url.split("?")[0]

    # Customize the spec with actual values
    spec["info"]["title"] = f"Logic App Workflow {workflow_name}"
    spec["servers"][0]["url"] = base_url
    spec["paths"]["/"]["post"]["operationId"] = f"invoke_{workflow_name}"
    spec["paths"]["/"]["post"]["summary"] = (
        f"Invoke Logic App workflow {workflow_name}"
    )

    return spec


def register_openapi_tool(
    project: str, workflow_name: str, callback_url: str, tool_name: str
) -> None:
    if not _HAS_AGENTS:
        raise RuntimeError(
            "azure-ai-agents package not installed; "
            "cannot register OpenAPI tool."
        )
    log("Creating custom connection with managed identity in AI Foundry...")

    # The project parameter should be a connection string in the format:
    # "region.api.azureml.ms;subscription_id;resource_group;workspace_name"
    # Or just the project/workspace endpoint URL

    credential = DefaultAzureCredential()

    # Parse project endpoint - expected format:
    # https://<account>.services.ai.azure.com/api/projects/<project-name>
    if not project.startswith("https://"):
        raise ValueError(
            f"Invalid project endpoint format: {project}. "
            "Expected: https://<account>.services.ai.azure.com/api/projects/<project-name>"
        )

    endpoint = project
    log(f"Using AI Foundry project endpoint: {endpoint}")

    # Use AIProjectClient to access agents
    from azure.ai.projects import AIProjectClient

    project_client = AIProjectClient(
        credential=credential,
        endpoint=endpoint
    )

    # Get the agents client from the project client
    client = project_client.agents
    openapi_spec = build_openapi_spec(workflow_name, callback_url)

    # Import required models for managed identity auth
    from azure.ai.agents.models import (OpenApiFunctionDefinition,
                                        OpenApiManagedAuthDetails,
                                        OpenApiManagedSecurityScheme,
                                        OpenApiToolDefinition)

    # Create managed identity auth details
    # The security scheme defines the audience for the managed identity token
    base_url = callback_url.split("?")[0]
    security_scheme = OpenApiManagedSecurityScheme(
        audience=base_url
    )

    managed_auth = OpenApiManagedAuthDetails(
        security_scheme=security_scheme
    )

    # Create the OpenAPI function definition with managed identity auth
    openapi_function = OpenApiFunctionDefinition(
        name=tool_name,
        description=f"Logic App workflow {workflow_name}",
        spec=openapi_spec,
        auth=managed_auth
    )

    # Create the tool definition wrapper
    tool_definition = OpenApiToolDefinition(
        openapi=openapi_function
    )

    log(f"Creating/updating agent with OpenAPI tool: {tool_name}")

    # Create or update an agent that uses this tool
    # First, try to find an existing agent
    agents = client.list_agents()
    agent_name = f"LogicApp-{workflow_name}-Agent"
    existing_agent = None

    for agent in agents:
        if agent.name == agent_name:
            existing_agent = agent
            break

    if existing_agent:
        log(f"Updating existing agent: {existing_agent.id}")
        client.update_agent(
            agent_id=existing_agent.id,
            name=agent_name,
            description=f"Agent with access to Logic App workflow {workflow_name}",
            instructions=f"You have access to a Logic App workflow called {workflow_name}. Use it when needed.",
            tools=[tool_definition],
            model="gpt-4o"
        )
        log(f"Agent updated: {existing_agent.id}")
    else:
        log(f"Creating new agent: {agent_name}")
        agent = client.create_agent(
            model="gpt-4o",
            name=agent_name,
            description=f"Agent with access to Logic App workflow {workflow_name}",
            instructions=f"You have access to a Logic App workflow called {workflow_name}. Use it when needed.",
            tools=[tool_definition]
        )
        log(f"Agent created: {agent.id}")

    log("OpenAPI tool with managed identity registered successfully.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Create / update a default Logic App Standard workflow with HTTP trigger + response.")
    p.add_argument("--subscription-id", required=True)
    p.add_argument("--resource-group", required=True)
    p.add_argument("--logic-app-name", required=True,
                   help="Name of the Logic App Standard site (App Service)")
    p.add_argument("--workflow-name", default="AgentHttpWorkflow")
    p.add_argument("--register-openapi", action="store_true",
                   help="Register workflow as OpenAPI tool in AI Foundry")
    p.add_argument("--ai-foundry-project",
                   help="AI Foundry project connection string or endpoint "
                   "(e.g., 'eastus.api.azureml.ms;12345678-1234-5678-1234-567812345678;my-rg;my-ws') "
                   "(required if --register-openapi)")
    p.add_argument("--tool-name", default="logicapp_workflow_tool",
                   help="Tool name for OpenAPI registration")
    p.add_argument("--debug", action="store_true",
                   help="Print full traceback on error for troubleshooting")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if args.register_openapi and not args.ai_foundry_project:
        log("--ai-foundry-project is required when --register-openapi is set")
        return 2

    try:
        token = get_access_token()
        log("Acquired management access token.")

        user, pwd = get_publishing_credentials(
            args.subscription_id, args.resource_group, args.logic_app_name, token)
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
