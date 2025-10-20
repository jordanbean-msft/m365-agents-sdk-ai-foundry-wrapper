# Infra Scripts

This directory contains utility scripts to assist with post-provision configuration of the Terraform-managed infrastructure.

## `create_default_logicapp_workflow.py`

Creates (or updates) a minimal Logic App Standard workflow with an HTTP Request trigger and simple echo response. Optionally registers an OpenAPI tool with an AI Foundry project.

### Run (uv ephemeral environment – recommended)

```bash
cd infra/scripts
uv run create_default_logicapp_workflow.py --help

# Example
uv run create_default_logicapp_workflow.py \
  --subscription-id <SUB_ID> \
  --resource-group rg-m365-agents \
  --logic-app-name logic-1234 \
  --workflow-name AgentHttpWorkflow
```

`uv run` will create a lightweight environment using the local `pyproject.toml` and install only the required dependencies (`requests`, `azure-identity`).

### Register OpenAPI tool

The `azure-ai-agents` dependency is installed by default. To also register the workflow as an OpenAPI tool for an AI Foundry project, include the flags:

```bash
uv run create_default_logicapp_workflow.py \
  --subscription-id <SUB_ID> \
  --resource-group rg-m365-agents \
  --logic-app-name logic-1234 \
  --register-openapi \
  --ai-foundry-project <PROJECT_NAME>
```

### Run with pip and Python (alternative)

If you prefer to use `pip` and system Python instead of `uv`:

```bash
cd infra/scripts
pip install -r requirements.txt
python create_default_logicapp_workflow.py --help

# Example
python create_default_logicapp_workflow.py \
  --subscription-id <SUB_ID> \
  --resource-group rg-m365-agents \
  --logic-app-name logic-1234 \
  --workflow-name AgentHttpWorkflow
```

### Direct execution (fallback)

Or make the script executable (shebang uses `uv run`):

```bash
chmod +x create_default_logicapp_workflow.py
./create_default_logicapp_workflow.py --help
```

### Notes

- Idempotent: re-running overwrites the workflow definition safely for this simple example.
- Extend the workflow by editing `build_workflow_definition()`.
- The shebang now leverages `uv run` for reproducible, dependency-isolated execution.
- `azure-ai-agents` is a mandatory dependency (no extra required).
