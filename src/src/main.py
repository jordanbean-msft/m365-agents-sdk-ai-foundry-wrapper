# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import logging

# Import agent handlers so decorator side-effects register routes.
from . import agent  # noqa: F401
from .config import AGENT_APP, CONNECTION_MANAGER
# enable logging for Microsoft Agents library
# for more information, see README.md for Quickstart Agent
from .start_server import start_server

ms_agents_logger = logging.getLogger("microsoft_agents")
ms_agents_logger.addHandler(logging.StreamHandler())
ms_agents_logger.setLevel(logging.INFO)


def main():
    """Main entry point for the Azure AI Streaming Agent."""
    start_server(
        agent_application=AGENT_APP,
        auth_configuration=CONNECTION_MANAGER.get_default_connection_configuration(),  # noqa: E501
    )


if __name__ == "__main__":
    main()
