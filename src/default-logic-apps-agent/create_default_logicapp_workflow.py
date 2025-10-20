#!/usr/bin/env -S uv run
"""Deploy a simple Logic App workflow and register it as an OpenAPI tool.

Workflow: HTTP trigger + echo style response.

Core steps:
1. Build minimal Logic App artifact (host.json + workflow.json).
2. Use management APIs for publishing creds + Kudu zip deploy.
3. Fetch manual trigger callback URL (includes SAS sig).
4. Create CustomKeys connection (stores sig) + register OpenAPI tool.

Prereqs:
* Existing Logic App Standard site (name, RG, subscription).
* Packages: azure-identity, requests, azure-ai-agents.
* DefaultAzureCredential must work (login or managed identity).

Example (uv):
    uv run create_default_logicapp_workflow.py \
        --subscription-id <SUB> \
        --resource-group <RG> \
        --logic-app-name <SITE> \
        --workflow-name AgentHttpWorkflow \
        --ai-foundry-project <project_url> \
        --ai-model-deployment-name gpt-4o
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import re
import sys
import time
import traceback
import zipfile
from pathlib import Path
from typing import Tuple

import requests
from azure.ai.agents.models import (OpenApiConnectionAuthDetails,
                                    OpenApiConnectionSecurityScheme,
                                    OpenApiFunctionDefinition,
                                    OpenApiToolDefinition)
from azure.ai.projects import AIProjectClient
from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MGMT_BASE = "https://management.azure.com"
MGMT_API_VERSION_WEB = "2023-01-01"       # publishing credentials
MGMT_API_VERSION_WORKFLOW = "2022-03-01"  # callback URL

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def log(msg: str) -> None:
    print(f"[create-workflow] {msg}")


def load_workflow_template() -> dict:
    script_dir = Path(__file__).parent
    workflow_file = script_dir / "workflow_definition.json"
    if not workflow_file.exists():
        raise FileNotFoundError(f"Workflow definition file not found: {workflow_file}")
    with open(workflow_file, "r", encoding="utf-8") as f:
        return json.load(f)


def build_workflow_definition(workflow_name: str) -> dict:
    template = load_workflow_template()
    definition = template.get("definition", {})
    try:
        body = definition["actions"]["Respond"]["inputs"]["body"]
        if isinstance(body, dict):
            body["workflowName"] = workflow_name
    except KeyError:
        pass
    return definition


def build_zip_package(workflow_name: str) -> bytes:
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
        zf.writestr(f"{workflow_name}/workflow.json", json.dumps(workflow_content, indent=2))
    mem_file.seek(0)
    return mem_file.read()


def get_access_token() -> str:
    credential = DefaultAzureCredential()
    return credential.get_token("https://management.azure.com/.default").token


def get_publishing_credentials(
    subscription_id: str,
    resource_group: str,
    site_name: str,
    token: str,
) -> Tuple[str, str]:
    url = (
        f"{MGMT_BASE}/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/"
        f"Microsoft.Web/sites/{site_name}/config/publishingcredentials/list?api-version={MGMT_API_VERSION_WEB}"
    )
    resp = requests.post(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if resp.status_code >= 300:
        raise RuntimeError(f"Failed publishing credentials: {resp.status_code} {resp.text}")
    props = resp.json().get("properties", {})
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
    status_url = f"https://{site_name}.scm.azurewebsites.net/api/deployments/latest"
    for attempt in range(30):
        time.sleep(2)
        st = requests.get(status_url, headers=headers, timeout=15)
        if st.status_code == 200:
            data = st.json()
            if data.get("complete") and data.get("status") == 4:
                log("Deployment completed successfully.")
                return
        else:
            log(f"Polling attempt {attempt} got {st.status_code}")
    raise RuntimeError("Deployment did not complete in allotted time.")


def get_trigger_callback_url(
    subscription_id: str,
    resource_group: str,
    site_name: str,
    workflow_name: str,
    token: str,
) -> str:
    url = (
        f"{MGMT_BASE}/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/"
        f"Microsoft.Web/sites/{site_name}/hostruntime/runtime/webhooks/workflow/api/management/workflows/"
        f"{workflow_name}/triggers/When_an_HTTP_request_is_received/listCallbackUrl?api-version={MGMT_API_VERSION_WORKFLOW}"
    )
    resp = requests.post(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if resp.status_code >= 300:
        raise RuntimeError(f"Failed listing callback URL: {resp.status_code} {resp.text}")
    value = resp.json().get("value")
    if not value:
        raise RuntimeError("Callback URL missing in response")
    return value


def load_openapi_template() -> dict:
    script_dir = Path(__file__).parent
    openapi_file = script_dir / "openapi_spec_template.json"
    if not openapi_file.exists():
        raise FileNotFoundError(f"OpenAPI spec template file not found: {openapi_file}")
    with open(openapi_file, "r", encoding="utf-8") as f:
        return json.load(f)


def build_openapi_spec(workflow_name: str, callback_url: str) -> tuple[dict, dict]:
    from urllib.parse import parse_qs, quote, urlparse
    spec = load_openapi_template()
    parsed = urlparse(callback_url)
    query_params = parse_qs(parsed.query)
    api_version = query_params.get("api-version", ["2016-10-01"])[0] or "2016-10-01"
    sv = query_params.get("sv", ["1.0"])[0]
    sp_raw = query_params.get("sp", [""])[0]
    sig = query_params.get("sig", [""])[0]
    if not sig:
        raise ValueError("No 'sig' parameter found in callback URL")
    sp = quote(sp_raw, safe="") if sp_raw else quote(
        "/triggers/When_an_HTTP_request_is_received/run", safe="")
    # Build server base URL without :443 port and without trailing /invoke segment.
    clean_netloc = parsed.netloc.replace(":443", "")
    path_no_invoke = parsed.path[:-7] if parsed.path.endswith("/invoke") else parsed.path
    base_url = f"{parsed.scheme}://{clean_netloc}{path_no_invoke}"
    post_op = spec["paths"]["/invoke"]["post"]
    post_op["operationId"] = "When_an_HTTP_request_is_received-invoke"
    post_op["summary"] = f"Invoke Logic App workflow {workflow_name}"
    post_op["description"] = f"Invoke Logic App workflow {workflow_name}"
    spec["info"]["title"] = f"Logic App Workflow {workflow_name}"
    spec["servers"][0]["url"] = base_url
    for param in post_op["parameters"]:
        if param["name"] == "api-version":
            param["schema"]["default"] = api_version
        elif param["name"] == "sv":
            param["schema"]["default"] = sv
        elif param["name"] == "sp":
            param["schema"]["default"] = sp
    return spec, {"sig": sig}


def parse_project_endpoint(project_endpoint: str) -> tuple[str, str]:
    from urllib.parse import urlparse
    parsed = urlparse(project_endpoint)
    host = parsed.hostname or ""
    account_name = host.split(".")[0] if host else ""
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2 or parts[-2] != "projects":
        raise ValueError(f"Unexpected project endpoint format: {project_endpoint}.")
    project_name = parts[-1]
    if not account_name or not project_name:
        raise ValueError("Missing account or project name in endpoint")
    return account_name, project_name


def create_or_update_custom_key_connection(
    subscription_id: str,
    resource_group: str,
    account_name: str,
    project_name: str,
    connection_name: str,
    sig: str,
    management_token: str,
) -> None:
    url = (
        "https://management.azure.com/subscriptions/"
        f"{subscription_id}/resourceGroups/{resource_group}/providers/"
        "Microsoft.CognitiveServices/accounts/"
        f"{account_name}/projects/{project_name}/connections/{connection_name}?api-version=2025-04-01-preview"
    )
    payload = {
        "properties": {
            "authType": "CustomKeys",
            "category": "CustomKeys",
            "target": "_",
            "isSharedToAll": False,
            "credentials": {"keys": {"sig": sig}},
            "metadata": {},
        }
    }
    headers = {"Authorization": f"Bearer {management_token}", "Content-Type": "application/json"}
    log(f"Creating/updating CustomKeys connection '{connection_name}'...")
    resp = requests.put(url, headers=headers, json=payload, timeout=60)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Conn {connection_name} failed: {resp.status_code} {resp.text}")
    log(f"Connection '{connection_name}' ready (status {resp.status_code}).")


def register_openapi_tool(
    project: str,
    workflow_name: str,
    callback_url: str,
    tool_name: str,
    model_deployment_name: str,
    subscription_id: str,
    resource_group: str,
) -> None:
    log("Registering OpenAPI tool in AI Foundry...")
    credential = DefaultAzureCredential()
    if not project.startswith("https://"):
        raise ValueError("Invalid project endpoint format")
    endpoint = project
    log(f"Using AI Foundry project endpoint: {endpoint}")
    project_client = AIProjectClient(credential=credential, endpoint=endpoint)
    client = project_client.agents
    openapi_spec, params = build_openapi_spec(workflow_name, callback_url)
    management_token = get_access_token()
    account_name, project_name = parse_project_endpoint(project)
    connection_name = f"{tool_name}_connection"
    create_or_update_custom_key_connection(
        subscription_id,
        resource_group,
        account_name,
        project_name,
        connection_name,
        params["sig"],
        management_token,
    )
    connection_id = (
        f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/"
        f"Microsoft.CognitiveServices/accounts/{account_name}/projects/{project_name}/connections/{connection_name}"
    )
    connection_auth = OpenApiConnectionAuthDetails(
        security_scheme=OpenApiConnectionSecurityScheme(connection_id=connection_id)
    )
    # Extract default params & functions list from template (logic2.json pattern)
    default_params = openapi_spec.get("default_params", ["api-version", "sp", "sv"])
    functions = openapi_spec.get("functions", [])
    # Use first function entry for name/description; fall back if missing.
    fn0 = functions[0] if functions else {}
    raw_fn_name = fn0.get("name") or f"{tool_name}_Tool_When_an_HTTP_request_is_received_invoke"
    raw_fn_desc = fn0.get("description") or f"Logic App workflow {workflow_name}"
    fn_name = raw_fn_name.replace("PLACEHOLDER", workflow_name)
    fn_desc = raw_fn_desc.replace("PLACEHOLDER", workflow_name)
    # Sanitize tool function name to pattern ^[a-zA-Z0-9_]+$
    fn_name = re.sub(r"[^a-zA-Z0-9_]", "_", fn_name)
    # Collapse multiple consecutive underscores
    fn_name = re.sub(r"_+", "_", fn_name).strip("_") or "logicapp_tool"
    # Ensure doesn't start with digit
    if fn_name and fn_name[0].isdigit():
        fn_name = f"_{fn_name}"

    openapi_function = OpenApiFunctionDefinition(
        name=fn_name,
        description=fn_desc,
        spec=openapi_spec,
        auth=connection_auth,
        default_params=default_params,
    )
    tool_definition = OpenApiToolDefinition(openapi=openapi_function)
    log(f"Creating/updating agent with OpenAPI tool: {tool_name}")
    agents = client.list_agents()
    agent_name = f"LogicApp-{workflow_name}-Agent"
    existing_agent = next((a for a in agents if a.name == agent_name), None)
    if existing_agent:
        log(f"Updating existing agent: {existing_agent.id}")
        client.update_agent(
            agent_id=existing_agent.id,
            name=agent_name,
            description=f"Agent with access to Logic App workflow {workflow_name}",
            instructions=f"Invoke workflow {workflow_name} via the registered tool.",
            tools=[tool_definition],
            model=model_deployment_name,
        )
        log(f"Agent updated: {existing_agent.id}")
    else:
        log(f"Creating new agent: {agent_name}")
        agent = client.create_agent(
            model=model_deployment_name,
            name=agent_name,
            description=f"Agent with access to Logic App workflow {workflow_name}",
            instructions=f"Invoke workflow {workflow_name} via the registered tool.",
            tools=[tool_definition],
        )
        log(f"Agent created: {agent.id}")
    log("OpenAPI tool registered successfully.")


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Deploy Logic App workflow and register OpenAPI tool.")
    p.add_argument("--subscription-id", required=True)
    p.add_argument("--resource-group", required=True)
    p.add_argument("--logic-app-name", required=True,
                   help="Name of the Logic App Standard site (App Service)")
    p.add_argument("--workflow-name", default="AgentHttpWorkflow")
    p.add_argument("--ai-foundry-project", required=True, help="Project endpoint base URL")
    p.add_argument("--ai-model-deployment-name", required=True,
                   help="Model deployment name (e.g. gpt-4o)")
    p.add_argument("--tool-name", default="logicapp_workflow_tool",
                   help="Tool name for OpenAPI registration")
    p.add_argument("--debug", action="store_true",
                   help="Print full traceback on error for troubleshooting")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        token = get_access_token()
        log("Acquired management access token.")
        user, pwd = get_publishing_credentials(
            args.subscription_id,
            args.resource_group,
            args.logic_app_name,
            token,
        )
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
        register_openapi_tool(
            project=args.ai_foundry_project,
            workflow_name=args.workflow_name,
            callback_url=callback_url,
            tool_name=args.tool_name,
            model_deployment_name=args.ai_model_deployment_name,
            subscription_id=args.subscription_id,
            resource_group=args.resource_group,
        )
        log("Done.")
        return 0
    except AzureError as az_ex:
        log(f"AzureError: {az_ex}")
        if args.debug:
            traceback.print_exc()
        return 1
    except (RuntimeError, ValueError, AzureError, requests.RequestException) as ex:
        log(f"Error: {ex}")
        if args.debug:
            traceback.print_exc()
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
