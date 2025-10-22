# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import logging
import os

# Import agent handlers so decorator side-effects register routes.
from . import agent  # noqa: F401
from .config import AGENT_APP, CONNECTION_MANAGER
# enable logging for Microsoft Agents library
# for more information, see README.md for Quickstart Agent
from .start_server import start_server


def _configure_root_logging() -> None:
    """Configure root logging once with level, format, and stdout handler.

    LOG_LEVEL can be overridden via environment variable. Defaults to INFO.
    """
    root_logger = logging.getLogger()
    if root_logger.handlers:  # already configured (hosting env)
        return

    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, log_level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format=(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        ),
    )

    # Ensure microsoft_agents logger inherits level (override possible later)
    logging.getLogger("microsoft_agents").setLevel(level)


_configure_root_logging()


def main():
    """Main entry point for the Azure AI Streaming Agent."""
    start_server(
        agent_application=AGENT_APP,
        auth_configuration=CONNECTION_MANAGER.get_default_connection_configuration(),  # noqa: E501
    )


if __name__ == "__main__":
    main()
