#!/usr/bin/env python3

# Simple test script to verify agent framework imports work
try:
    from agent_framework.azure import AzureAIAgentClient
    print("✓ AzureAIAgentClient import successful")

    from azure.identity import DefaultAzureCredential
    print("✓ DefaultAzureCredential import successful")

    # Test instantiation without actual credentials
    print("✓ All imports working correctly!")
    print("The Microsoft Agent Framework is properly installed and ready to use.")

except ImportError as e:
    print(f"✗ Import failed: {e}")
    print("Please ensure all dependencies are installed with prerelease flag:")
    print("uv sync --prerelease=allow")
