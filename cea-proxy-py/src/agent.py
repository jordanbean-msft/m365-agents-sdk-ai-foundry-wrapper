from __future__ import annotations

from typing import Union

# Azure AI Foundry SDK imports
from azure.ai.projects import AIProjectClient
from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from config import Config
from microsoft_agents.activity import ChannelAccount
# Updated imports to new namespace microsoft_agents
from microsoft_agents.hosting.core import (ActivityHandler, MessageFactory,
                                           TurnContext)
from pydantic import BaseModel, Field


class WeatherForecastAgentResponse(BaseModel):
    contentType: str = Field(pattern=r"^(Text|AdaptiveCard)$")
    content: Union[dict, str]


class CustomEngineAgent(ActivityHandler):
    def __init__(self):
        super().__init__()
        # Lazily initialize Azure AI client; avoid construction if env not set
        self._ai_client: AIProjectClient | None = None
        self._agent_id: str | None = None
        # Map Bot Framework conversation ids -> Azure AI Foundry thread ids
        # NOTE: This is in-memory only; for multi-process or scaled out bots
        # you must persist this (e.g., Azure Cosmos DB, Redis, or Bot Framework
        # ConversationState storage) so threads survive restarts.
        self._threads: dict[str, str] = {}

    async def on_members_added_activity(
        self, members_added: list[ChannelAccount], turn_context: TurnContext
    ):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("Hello and welcome!")

    async def on_message_activity(self, turn_context: TurnContext):
        """Forward user message to Azure AI Foundry agent.

        Uses Config class for environment variables:
        - AZURE_AI_PROJECT_ENDPOINT: Project endpoint
        - AI_AGENT_NAME: Agent name to invoke
        - MODEL_DEPLOYMENT_NAME: If agent creation needed
        """
        user_text = (turn_context.activity.text or "").strip()
        conversation_id = getattr(
            turn_context.activity.conversation, "id", None
        )

        if conversation_id is None:
            activity = MessageFactory.text(
                "Missing conversation id; cannot route thread."
            )
            return await turn_context.send_activity(activity)

        # Allow user to force a fresh thread for this conversation
        reset_requested = user_text.lower() in {
            "/reset",
            "reset",
            "/new",
            "new thread",
        }

        if not Config.AZURE_AI_PROJECT_ENDPOINT:
            activity = MessageFactory.text(
                "Azure AI Project endpoint not configured "
                "(AZURE_AI_PROJECT_ENDPOINT)."
            )
            return await turn_context.send_activity(activity)

        if not Config.AI_AGENT_NAME:
            activity = MessageFactory.text(
                "AI agent name not configured (AI_AGENT_NAME)."
            )
            return await turn_context.send_activity(activity)

        if self._ai_client is None:
            try:
                self._ai_client = AIProjectClient(
                    endpoint=Config.AZURE_AI_PROJECT_ENDPOINT,
                    credential=DefaultAzureCredential(),
                )
            except HttpResponseError as http_err:
                activity = MessageFactory.text(
                    f"Client init HTTP error: {http_err}"
                )
                return await turn_context.send_activity(activity)
            except (ValueError, RuntimeError, OSError) as init_err:
                activity = MessageFactory.text(
                    f"Client init error: {init_err}"
                )
                return await turn_context.send_activity(activity)

        if self._ai_client is None:
            # If still None after attempt, abort
            activity = MessageFactory.text("AI client not initialized.")
            return await turn_context.send_activity(activity)

        if self._agent_id is None:
            try:
                existing = []
                for agent in self._ai_client.agents.list_agents():
                    if agent.name == Config.AI_AGENT_NAME:
                        existing.append(agent)
                if existing:
                    self._agent_id = existing[0].id
                else:
                    if not Config.MODEL_DEPLOYMENT_NAME:
                        activity = MessageFactory.text(
                            (
                                f"Agent '{Config.AI_AGENT_NAME}' not found; "
                                "set MODEL_DEPLOYMENT_NAME to create."
                            )
                        )
                        return await turn_context.send_activity(activity)
                    created = self._ai_client.agents.create_agent(
                        model=Config.MODEL_DEPLOYMENT_NAME,
                        name=Config.AI_AGENT_NAME,
                        instructions=(
                            f"You are {Config.AI_AGENT_NAME}, an AI assistant "
                            "helping with user queries."
                        ),
                    )
                    self._agent_id = created.id
            except HttpResponseError as http_err:
                activity = MessageFactory.text(
                    f"Agent retrieval/creation HTTP error: {http_err}"
                )
                return await turn_context.send_activity(activity)
            except (ValueError, RuntimeError, OSError) as agent_err:
                activity = MessageFactory.text(
                    f"Unexpected agent setup error: {agent_err}"
                )
                return await turn_context.send_activity(activity)

        try:
            # Retrieve or create thread for this conversation
            if reset_requested or conversation_id not in self._threads:
                thread = self._ai_client.agents.threads.create()
                self._threads[conversation_id] = thread.id
                if reset_requested:
                    system_msg = "Started a new conversation thread."
                    await turn_context.send_activity(system_msg)
            thread_id = self._threads[conversation_id]

            # Append user's message to existing thread
            self._ai_client.agents.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_text,
            )
            run = self._ai_client.agents.runs.create_and_process(
                thread_id=thread_id,
                agent_id=self._agent_id,
            )
            if run.status == "failed":
                msg = (
                    f"Agent run failed: {run.last_error}"
                    if run.last_error
                    else "Agent run failed."
                )
                activity = MessageFactory.text(msg)
                return await turn_context.send_activity(activity)

            messages = self._ai_client.agents.messages.list(
                thread_id=thread_id
            )
            assistant_reply = None
            for message in messages:
                has_text = getattr(message, "text_messages", None)
                if message.role == "assistant" and has_text:
                    assistant_reply = has_text[-1].text.value
            if not assistant_reply:
                assistant_reply = "No assistant reply received."
            activity = MessageFactory.text(assistant_reply)
            return await turn_context.send_activity(activity)
        except HttpResponseError as http_err:
            activity = MessageFactory.text(f"Azure AI error: {http_err}")
            return await turn_context.send_activity(activity)
        except (ValueError, RuntimeError, OSError) as run_err:
            activity = MessageFactory.text(
                f"Unexpected run error: {run_err}"
            )
            return await turn_context.send_activity(activity)
