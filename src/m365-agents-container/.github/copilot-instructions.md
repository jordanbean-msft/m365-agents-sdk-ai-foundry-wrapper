# Copilot Instructions for M365 Agents Container

## Project Overview

This is a Python-based container application that wraps Azure AI Foundry agents for use with the Microsoft 365 Agents SDK. It provides a Bot Framework-compatible endpoint that enables AI Foundry agents to be used in Microsoft Teams and other Bot Framework channels.

## Architecture & Design Patterns

### Core Components

- **Entry Point**: `src/main.py` (delegates to `src/app/bootstrap.py`)
- **Configuration**: `src/app/config.py` - Environment variables and service initialization
- **Server**: `src/app/server.py` - aiohttp web server setup
- **Handlers**: `src/api/handlers.py` - Bot Framework activity handlers (invoke, message)
- **Agent Factory**: `src/agents/factory.py` - Creates AI Foundry agent clients
- **State Management**: `src/agents/state.py` - In-memory conversation state
- **Cards**: `src/api/cards.py` - Adaptive card builders
- **Streaming**: `src/api/streaming.py` - Status update utilities

### Key Design Decisions

1. **Fresh Credentials Per Request**: Each message handler creates a new `DefaultAzureCredential()` instance to avoid token expiration issues in long-running containers
2. **Thread Reuse**: Conversation threads are cached in-memory per conversation_id but recreated if conversation is reset
3. **Tool Passthrough**: Tools from AI Foundry (code_interpreter, file_search, etc.) are passed through; function tools are logged but not implemented locally
4. **Streaming Suppression**: Text chunk streaming is suppressed via monkey-patching to avoid duplicate content (only adaptive cards are sent)
5. **Adaptive Cards Only**: Final responses are delivered as adaptive cards with metadata, not plain text
6. **No Welcome Message**: The `on_members_added` handler has been removed for Copilot Chat compatibility (membersAdded events fire differently across channels)

### Authentication Flow

```
Container App (User-Assigned MI)
    ↓ AZURE_CLIENT_ID env var
DefaultAzureCredential()
    ↓ Acquires token with scope: https://ai.azure.com/.default
AzureAIAgentClient
    ↓ Uses credential for all API calls
Azure AI Foundry Project
```

## Code Patterns & Conventions

### Environment Variables

- All config loaded via `dotenv` and `os.environ` in `src/app/config.py`
- Required vars: `AZURE_AI_PROJECT_ENDPOINT`, `AZURE_AI_FOUNDRY_AGENT_ID`, bot credentials
- Managed identity var: `AZURE_CLIENT_ID` (only needed in Azure, not local dev)
- Optional vars: `LOG_LEVEL`, `RESET_COMMAND_KEYWORDS`, `APPLICATIONINSIGHTS_CONNECTION_STRING`

### Logging

- Use standard Python `logging` module
- Logger instances: `logger = logging.getLogger(__name__)`
- Log important events: conversation start, thread creation, agent runs, token usage, errors
- Include context: conversation_id, thread_id, run_id, user_id

### Error Handling

- Use broad `except Exception` with logging for user-facing handlers (don't crash on single message)
- Include `exc_info=True` in error logs for stack traces
- Send friendly error messages to users via `context.send_activity()`
- Example:
  ```python
  except Exception as exc:  # noqa: BLE001
      logger.error("Error during agent run: %s", exc, exc_info=True)
      await context.send_activity("An error occurred. Please try again.")
  ```

### Conversation State Management

- State stored in module-level dicts: `conversation_threads`, `conversation_tool_resources`
- Reset via `reset_conversation(conversation_id)` function
- Keys: conversation_id from Bot Framework activity
- No external persistence (use Redis/Cosmos for production scale)

### Agent Creation Pattern

```python
# Always create fresh credential instance
fresh_credential = DefaultAzureCredential()

# Create agent with fresh credential
agent, tool_resources = await create_chat_agent_from_foundry(
    project_endpoint=AZURE_AI_PROJECT_ENDPOINT,
    agent_id=AZURE_AI_FOUNDRY_AGENT_ID,
    async_credential=fresh_credential,
)

# Reuse thread if exists
thread = conversation_threads.get(conversation_id)
if not thread:
    thread = agent.get_new_thread()
    conversation_threads[conversation_id] = thread
```

### Response Pattern

```python
# Collect response chunks
full_response = []
async for chunk in agent.run_stream(user_content, thread=thread):
    if getattr(chunk, "text", None):
        full_response.append(chunk.text)

# Build adaptive card
response_text = "".join(full_response)
card_dict = build_response_adaptive_card(response_text, metadata)

# Send via streaming response if available
if hasattr(context, "streaming_response"):
    sr = context.streaming_response
    sr.set_attachments([card_attachment])
    await sr.end_stream()
else:
    # Fallback to normal activity
    await context.send_activity(Activity(...))
```

## Deployment & Infrastructure

### Docker Build Requirements

**CRITICAL**: Azure Container Apps runs on `linux/amd64`. Always build with platform flag:

```bash
docker buildx build --platform linux/amd64 -t <image> .
```

Failure to do this on ARM machines (Apple Silicon) will cause startup failures.

### Terraform Integration

- Infrastructure defined in `../../infra/`
- Environment variables set via `container-apps` module
- Secrets stored in Key Vault, referenced by Container App
- Managed identity created by `identity` module, RBAC assigned in root `main.tf`

### Required RBAC

The user-assigned managed identity needs:

- **Azure AI User** role on the AI Foundry project resource
- **AcrPull** role on the Azure Container Registry

## Development Workflows

### Local Development

1. Copy `env.TEMPLATE` to `.env` and configure all required variables
2. Run dev tunnel: `devtunnel host -p 3978 --allow-anonymous`
3. Update Azure Bot messaging endpoint with tunnel URL
4. Run app: `uv run python -m src.main` or `python -m src.main`
5. Test via Bot Framework WebChat or Teams

### Adding New Features

**To add a new environment variable:**

1. Add to `env.TEMPLATE` with description
2. Add to `src/app/config.py` to load it
3. Update `infra/modules/container-apps/main.tf` to set it
4. Update `infra/modules/container-apps/variables.tf` if needed
5. Update README environment variables table

**To add a new handler:**

1. Add decorated function in `src/api/handlers.py`
2. Use `@AGENT_APP.message()`, `@AGENT_APP.activity()`, etc.
3. Follow existing patterns for logging and error handling

**To modify adaptive cards:**

1. Edit `src/api/cards.py`
2. Follow Adaptive Cards schema: https://adaptivecards.io/explorer/
3. Test in WebChat and Teams (rendering may differ)

### Testing Changes

1. **Local**: Test with dev tunnel + WebChat
2. **Container**: Build locally and run with Docker
3. **Azure**: Push to ACR and update Container App revision
4. **Verify**: Check Container App logs in Azure Portal

## Common Pitfalls

1. **Token Expiration**: Don't reuse `DefaultAzureCredential()` instances across requests
2. **ARM vs AMD64**: Always specify `--platform linux/amd64` when building on ARM
3. **Duplicate Content**: Suppress text streaming when using adaptive cards to avoid showing both
4. **Missing AZURE_CLIENT_ID**: Required in Azure but not needed for local dev with user credentials
5. **Thread State**: Threads don't expire automatically; implement manual reset or timeout logic
6. **Tool Deduplication**: OpenAPI tools can be duplicated; deduplicate by name (see factory.py)
7. **Copilot Chat vs Teams**: Bot Framework events (especially conversationUpdate/membersAdded) fire differently in M365 Copilot compared to Teams; avoid relying on these events for critical functionality

## References

- **M365 Agents SDK**: https://github.com/microsoft/agents
- **Azure AI Foundry**: https://ai.azure.com
- **Adaptive Cards**: https://adaptivecards.io
- **Bot Framework**: https://dev.botframework.com

---

**For AI assistants:**

- Always check `src/app/config.py` for environment variable usage before adding new config
- Follow the established logging patterns with conversation context
- Create fresh credential instances in handlers, don't reuse from module scope
- Use adaptive cards for all user-facing responses
- Test any Docker build changes with `--platform linux/amd64` flag
- Update both README and `env.TEMPLATE` when changing configuration
- Maintain consistency with the Terraform infrastructure in `../../infra/`
