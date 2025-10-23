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
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, log_level_name, logging.INFO)

    root_logger = logging.getLogger()

    # Set root logger level (always do this even if handlers exist)
    root_logger.setLevel(level)

    # If handlers already exist (hosting env), update their levels
    # instead of adding new ones
    if root_logger.handlers:
        for handler in root_logger.handlers:
            handler.setLevel(level)
    else:
        # No handlers exist, add a new one
        import sys
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    # Ensure microsoft_agents logger inherits level
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
