"""Application bootstrap and configuration package.

This package contains the runtime wiring for hosting the Azure AI Foundry
chat agent inside an aiohttp web process.

Submodules:
  config      – Environment + hosting object initialization.
  logging     – Root logging configuration helper.
  server      – HTTP server (aiohttp) setup and start.
  bootstrap   – Public main() entry point used by the CLI script.
"""
from .bootstrap import main  # re-export for convenience

__all__ = ["main"]
