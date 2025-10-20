#!/usr/bin/env -S uv run
"""
create_connection.py

Helper script to create a Custom Key connection in AI Foundry for Logic Apps.
This connection stores the 'sig' parameter from the Logic Apps callback URL.

Usage:
    uv run create_connection.py \
      --project-endpoint "https://<account>.services.ai.azure.com/api/projects/<project-name>" \
      --connection-name "my_connection" \
      --sig "your-sig-value"
"""
from __future__ import annotations

import argparse
import json
import sys

import requests
from azure.identity import DefaultAzureCredential


def log(msg: str) -> None:
    print(f"[create-connection] {msg}")


def create_custom_key_connection(
    project_endpoint: str, connection_name: str, sig: str
) -> None:
    """Create a Custom Key connection in AI Foundry using the REST API.

    Args:
        project_endpoint: AI Foundry project endpoint
        connection_name: Name for the connection
        sig: The signature value from Logic Apps callback URL
    """
    credential = DefaultAzureCredential()

    # Get access token for AI services
    token = credential.get_token("https://ml.azure.com/.default").token

    # Parse project endpoint to get connection API endpoint
    # Expected format: https://<account>.services.ai.azure.com/api/projects/<project-name>
    base_url = project_endpoint.replace("/api/projects/", "/api/")
    connection_url = f"{base_url}/connections/{connection_name}"

    log(f"Creating connection at: {connection_url}")

    # Connection payload
    connection_data = {
        "name": connection_name,
        "type": "CustomKeys",
        "properties": {
            "category": "CustomKeys",
            "authType": "CustomKeys",
            "credentials": {
                "keys": {
                    "sig": sig
                }
            },
            "target": "https://logic-app-endpoint"  # Placeholder, not used
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Try to create the connection
    response = requests.put(
        connection_url,
        headers=headers,
        json=connection_data,
        params={"api-version": "2024-07-01-preview"},
        timeout=30
    )

    if response.status_code in (200, 201):
        log(f"✅ Connection '{connection_name}' created successfully")
        log(f"Connection ID: {connection_name}")
        return
    elif response.status_code == 409:
        log(f"⚠️  Connection '{connection_name}' already exists")
        # Try to update it
        response = requests.patch(
            connection_url,
            headers=headers,
            json={"properties": connection_data["properties"]},
            params={"api-version": "2024-07-01-preview"},
            timeout=30
        )
        if response.status_code in (200, 201):
            log(f"✅ Connection '{connection_name}' updated successfully")
            return

    # If we got here, something went wrong
    log(f"❌ Failed to create connection: {response.status_code}")
    log(f"Response: {response.text}")
    raise RuntimeError(f"Failed to create connection: {response.status_code}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Create a Custom Key connection in AI Foundry for Logic Apps"
    )
    p.add_argument(
        "--project-endpoint",
        required=True,
        help="AI Foundry project endpoint (e.g., https://<account>.services.ai.azure.com/api/projects/<project-name>)"
    )
    p.add_argument(
        "--connection-name",
        required=True,
        help="Name for the connection"
    )
    p.add_argument(
        "--sig",
        required=True,
        help="The sig parameter value from Logic Apps callback URL"
    )
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    try:
        create_custom_key_connection(
            project_endpoint=args.project_endpoint,
            connection_name=args.connection_name,
            sig=args.sig
        )
        log("Done.")
        return 0
    except Exception as ex:
        log(f"Error: {ex}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
