#!/usr/bin/env -S uv run
"""Deploy a simple Logic App workflow and register it as an OpenAPI tool.

Outputs a JSON document to stdout containing:
  - ai_foundry_agent_id
  - callback_url
  - logic_app_name, workflow_name, tool_name
  - ai_foundry_project_endpoint, ai_model_deployment_name

Use shell redirection to capture the JSON and extract fields with `jq`.

Prereqs:
* Existing Logic App Standard site (name, RG, subscription).
* Packages: azure-identity, requests, azure-ai-agents.
* DefaultAzureCredential must work (login or managed identity).

Example:
    uv run create_default_logicapp_workflow.py \
        --subscription-id <SUB> \
        --resource-group <RG> \
        --logic-app-name <SITE> \
        --workflow-name AgentHttpWorkflow \
        --ai-foundry-project-endpoint <project_url> \
        --ai-model-deployment-name gpt-4o
"""
# flake8: max-line-length=120
from __future__ import annotations

import argparse
import base64
import io
import json
import logging
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
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def load_workflow_template() -> dict:
    script_dir = Path(__file__).parent
    workflow_file = script_dir / "workflow_definition.json"
    if not workflow_file.exists():
        raise FileNotFoundError(
            f"Workflow definition file not found: {workflow_file}"
        )
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
    with zipfile.ZipFile(
        mem_file, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as zf:
        zf.writestr(
            "host.json", json.dumps(host_json, indent=2)
        )
        zf.writestr(
            f"{workflow_name}/workflow.json",
            json.dumps(workflow_content, indent=2),
        )
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
        f"{MGMT_BASE}/subscriptions/{subscription_id}/resourceGroups/"
        f"{resource_group}/providers/Microsoft.Web/sites/{site_name}/config/"
        "publishingcredentials/list"
        f"?api-version={MGMT_API_VERSION_WEB}"
    )
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if resp.status_code >= 300:
        raise RuntimeError(
            f"Failed publishing credentials: {resp.status_code} {resp.text}"
        )
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
    logger.info("Uploading ZIP package via Kudu Zip Deploy...")
    resp = requests.post(
        deploy_url, headers=headers, data=zip_bytes, timeout=300
    )
    if resp.status_code >= 300:
        raise RuntimeError(
            f"Zip Deploy failed: {resp.status_code} {resp.text}"
        )
    status_url = (
        f"https://{site_name}.scm.azurewebsites.net/api/deployments/latest"
    )
    for attempt in range(30):
        time.sleep(2)
        st = requests.get(status_url, headers=headers, timeout=15)
        if st.status_code == 200:
            data = st.json()
            if data.get("complete") and data.get("status") == 4:
                logger.info("Deployment completed successfully.")
                return
        else:
            logger.debug(f"Polling attempt {attempt} got {st.status_code}")
    raise RuntimeError("Deployment did not complete in allotted time.")


def get_trigger_callback_url(
    subscription_id: str,
    resource_group: str,
    site_name: str,
    workflow_name: str,
    token: str,
) -> str:
    url = (
        f"{MGMT_BASE}/subscriptions/{subscription_id}/resourceGroups/"
        f"{resource_group}/providers/Microsoft.Web/sites/{site_name}/"
        "hostruntime/runtime/webhooks/workflow/api/management/workflows/"
        f"{workflow_name}/triggers/When_an_HTTP_request_is_received/"
        "listCallbackUrl"
        f"?api-version={MGMT_API_VERSION_WORKFLOW}"
    )
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if resp.status_code >= 300:
        raise RuntimeError(
            f"Failed listing callback URL: {resp.status_code} {resp.text}"
        )
    value = resp.json().get("value")
    if not value:
        raise RuntimeError("Callback URL missing in response")
    return value


def load_openapi_template() -> dict:
    script_dir = Path(__file__).parent
    openapi_file = script_dir / "openapi_spec_template.json"
    if not openapi_file.exists():
        raise FileNotFoundError(
            f"OpenAPI spec template file not found: {openapi_file}"
        )
    with open(openapi_file, "r", encoding="utf-8") as f:
        return json.load(f)


def build_openapi_spec(
    workflow_name: str, callback_url: str
) -> tuple[dict, dict]:
    from urllib.parse import parse_qs, quote, urlparse
    spec = load_openapi_template()
    parsed = urlparse(callback_url)
    query_params = parse_qs(parsed.query)
    api_version = (
        query_params.get("api-version", ["2016-10-01"])[0] or "2016-10-01"
    )
    sv = query_params.get("sv", ["1.0"])[0]
    sp_raw = query_params.get("sp", [""])[0]
    sig = query_params.get("sig", [""])[0]
    if not sig:
        raise ValueError("No 'sig' parameter found in callback URL")
    sp = quote(sp_raw, safe="") if sp_raw else quote(
        "/triggers/When_an_HTTP_request_is_received/run", safe="")
    # Build server base URL without :443 and without trailing /invoke.
    clean_netloc = parsed.netloc.replace(":443", "")
    path_no_invoke = (
        parsed.path[:-7] if parsed.path.endswith("/invoke") else parsed.path
    )
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
        raise ValueError(
            f"Unexpected project endpoint format: {project_endpoint}."
        )
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
        f"{account_name}/projects/{project_name}/connections/{connection_name}"
        "?api-version=2025-04-01-preview"
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
    headers = {
        "Authorization": f"Bearer {management_token}",
        "Content-Type": "application/json",
    }
    logger.info(
        f"Creating/updating CustomKeys connection '{connection_name}'..."
    )
    resp = requests.put(url, headers=headers, json=payload, timeout=60)
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Conn {connection_name} failed: {resp.status_code} {resp.text}"
        )
    logger.info(
        f"Connection '{connection_name}' ready "
        f"(status {resp.status_code})."
    )


def register_openapi_tool(
    project: str,
    workflow_name: str,
    callback_url: str,
    tool_name: str,
    model_deployment_name: str,
    subscription_id: str,
    resource_group: str,
) -> str:
    """Register (or update) an agent with an OpenAPI tool; return agent id."""
    logger.info("Registering OpenAPI tool in AI Foundry...")
    credential = DefaultAzureCredential()
    if not project.startswith("https://"):
        raise ValueError("Invalid project endpoint format")
    endpoint = project
    logger.info(f"Using AI Foundry project endpoint: {endpoint}")
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
        f"/subscriptions/{subscription_id}/resourceGroups/"
        f"{resource_group}/providers/Microsoft.CognitiveServices/accounts/"
        f"{account_name}/projects/{project_name}/connections/{connection_name}"
    )
    connection_auth = OpenApiConnectionAuthDetails(
        security_scheme=OpenApiConnectionSecurityScheme(
            connection_id=connection_id
        )
    )
    default_params = openapi_spec.get(
        "default_params",
        ["api-version", "sp", "sv"],
    )
    functions = openapi_spec.get("functions", [])
    fn0 = functions[0] if functions else {}
    raw_fn_name = (
        fn0.get("name")
        or f"{tool_name}_Tool_When_an_HTTP_request_is_received_invoke"
    )
    raw_fn_desc = (
        fn0.get("description")
        or f"Logic App workflow {workflow_name}"
    )
    fn_name = raw_fn_name.replace("PLACEHOLDER", workflow_name)
    fn_desc = raw_fn_desc.replace("PLACEHOLDER", workflow_name)
    fn_name = re.sub(r"[^a-zA-Z0-9_]", "_", fn_name)
    fn_name = re.sub(r"_+", "_", fn_name).strip("_") or "logicapp_tool"
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
    logger.info(f"Creating/updating agent with OpenAPI tool: {tool_name}")
    agents = client.list_agents()
    agent_name = f"LogicApp-{workflow_name}-Agent"
    existing_agent = next((a for a in agents if a.name == agent_name), None)
    if existing_agent:
        logger.info(f"Updating existing agent: {existing_agent.id}")
        client.update_agent(
            agent_id=existing_agent.id,
            name=agent_name,
            description=(
                f"Agent with access to Logic App workflow {workflow_name}"
            ),
            instructions=(
                f"Invoke workflow {workflow_name} via the registered tool."
            ),
            tools=[tool_definition],
            model=model_deployment_name,
        )
        logger.info(f"Agent updated: {existing_agent.id}")
        agent_id = existing_agent.id
    else:
        logger.info(f"Creating new agent: {agent_name}")
        agent = client.create_agent(
            model=model_deployment_name,
            name=agent_name,
            description=(
                f"Agent with access to Logic App workflow {workflow_name}"
            ),
            instructions=(
                f"Invoke workflow {workflow_name} via the registered tool."
            ),
            tools=[tool_definition],
        )
        logger.info(f"Agent created: {agent.id}")
        agent_id = agent.id
    logger.info("OpenAPI tool registered successfully.")
    return agent_id


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Deploy Logic App workflow and register OpenAPI tool. "
            "Print a JSON payload with agent and workflow metadata."
        )
    )
    # Required args
    p.add_argument("--subscription-id", required=True, dest="subscription_id")
    p.add_argument("--resource-group", required=True, dest="resource_group")
    p.add_argument(
        "--logic-app-name",
        required=True,
        dest="logic_app_name",
        help="Logic App Standard site name",
    )
    p.add_argument(
        "--ai-foundry-project-endpoint",
        required=True,
        dest="ai_foundry_project",
        help=(
            "AI Foundry project endpoint URL "
            "(e.g., https://account.services.ai.azure.com/api/"
            "projects/projectname)"
        ),
    )
    p.add_argument(
        "--ai-model-deployment-name",
        required=True,
        dest="ai_model_deployment_name",
        help="Model deployment name (e.g. gpt-4o)",
    )
    # Optional / defaults
    p.add_argument("--workflow-name", default="AgentHttpWorkflow")
    p.add_argument(
        "--tool-name",
        default="logicapp_workflow_tool",
        help="Tool name for OpenAPI registration",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="Print full traceback on error for troubleshooting",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    # Configure logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    subscription_id = args.subscription_id
    resource_group = args.resource_group
    logic_app_name = args.logic_app_name
    ai_foundry_project = args.ai_foundry_project
    ai_model_deployment_name = args.ai_model_deployment_name
    workflow_name = args.workflow_name
    tool_name = args.tool_name

    try:
        # Cast to str to ensure correct types for downstream function calls
        subscription_id = str(subscription_id)
        resource_group = str(resource_group)
        logic_app_name = str(logic_app_name)
        ai_foundry_project = str(ai_foundry_project)
        ai_model_deployment_name = str(ai_model_deployment_name)
        token = get_access_token()
        logger.info("Acquired management access token.")
        user, pwd = get_publishing_credentials(
            subscription_id,
            resource_group,
            logic_app_name,
            token,
        )
        logger.info("Retrieved publishing credentials.")
        zip_bytes = build_zip_package(workflow_name)
        zip_deploy(logic_app_name, user, pwd, zip_bytes)
        callback_url = get_trigger_callback_url(
            subscription_id,
            resource_group,
            logic_app_name,
            workflow_name,
            token,
        )
        logger.info(
            "Workflow deployed. Manual trigger callback URL:\n"
            f"{callback_url}"
        )
        # Register tool & capture agent id
        agent_id = register_openapi_tool(
            project=ai_foundry_project,
            workflow_name=workflow_name,
            callback_url=callback_url,
            tool_name=tool_name,
            model_deployment_name=ai_model_deployment_name,
            subscription_id=subscription_id,
            resource_group=resource_group,
        )
        output_payload = {
            "ai_foundry_project_endpoint": ai_foundry_project,
            "ai_model_deployment_name": ai_model_deployment_name,
            "ai_foundry_agent_id": agent_id,
            "logic_app_name": logic_app_name,
            "workflow_name": workflow_name,
            "tool_name": tool_name,
            "callback_url": callback_url,
        }
        logger.info("Emitting deployment output JSON")
        print(json.dumps(output_payload, indent=2))
        return 0
    except AzureError as az_ex:
        logger.error(f"AzureError: {az_ex}")
        if args.debug:
            traceback.print_exc()
        return 1
    except (
        RuntimeError,
        ValueError,
        AzureError,
        requests.RequestException,
    ) as ex:
        logger.error(f"Error: {ex}")
        if args.debug:
            traceback.print_exc()
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
