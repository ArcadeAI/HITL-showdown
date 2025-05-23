from agents import (Agent, Runner, AgentHooks, Tool, RunContextWrapper,
                    TResponseInputItem,
                    trace, set_tracing_export_api_key)
from functools import partial
from agents_arcade.errors import AuthorizationError
from arcadepy import AsyncArcade
from agents_arcade import get_arcade_tools
from typing import Any
from jit_permissions.tools import UserDeniedToolCall, confirm_tool_usage

import dotenv
import os
dotenv.load_dotenv()
set_tracing_export_api_key(os.environ["OPENAI_API_KEY"])

ENFORCE_HUMAN_CONFIRMATION = [
    "Google_SendEmail",
    "Slack_SendDmToUser",
]


class CustomAgentHooks(AgentHooks):
    def __init__(self, display_name: str):
        self.event_counter = 0
        self.display_name = display_name

    async def on_start(self,
                       context: RunContextWrapper,
                       agent: Agent) -> None:
        self.event_counter += 1
        print(f"### ({self.display_name}) {
              self.event_counter}: Agent {agent.name} started")

    async def on_end(self,
                     context: RunContextWrapper,
                     agent: Agent,
                     output: Any) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {
                # agent.name} ended with output {output}"
                agent.name} ended"
        )

    async def on_handoff(self,
                         context: RunContextWrapper,
                         agent: Agent,
                         source: Agent) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {
                source.name} handed off to {agent.name}"
        )

    async def on_tool_start(self,
                            context: RunContextWrapper,
                            agent: Agent,
                            tool: Tool) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}:"
            f" Agent {agent.name} started tool {tool.name}"
            f" with context: {context.context}"
        )

    async def on_tool_end(self,
                          context: RunContextWrapper,
                          agent: Agent,
                          tool: Tool,
                          result: str) -> None:
        self.event_counter += 1
        print(
            f"### ({self.display_name}) {self.event_counter}: Agent {
                # agent.name} ended tool {tool.name} with result {result}"
                agent.name} ended tool {tool.name}"
        )


async def main():

    context = {
        "user_id": "mateo@arcade.dev",
        "email": "mateo@arcade.dev",
    }

    client = AsyncArcade()

    google_tools = await get_arcade_tools(
        client, tools=["Google_ListEmails", "Google_SendEmail"])
    slack_tools = await get_arcade_tools(
        client, tools=["Slack_ListUsers", "Slack_SendDmToUser"])

    for t in google_tools + slack_tools:
        if t.name in ENFORCE_HUMAN_CONFIRMATION:
            t.on_invoke_tool = partial(
                confirm_tool_usage,
                tool_name=t.name,
                callback=t.on_invoke_tool,
            )

    google_agent = Agent(
        name="Google Agent",
        instructions="You are a helpful assistant that can assist using tools"
                     " to manage a Google account, contacts, and inbox.",
        handoff_description="An agent equipped with Google tools",
        model=os.environ["OPENAI_MODEL"],
        tools=google_tools,
        hooks=CustomAgentHooks(display_name="Google Agent")
    )

    slack_agent = Agent(
        name="Slack agent",
        instructions="You are a helpful assistant that can assist using tools"
                     " to interact with Slack."
                     " You have tools to manage channels and send DMs.",
        handoff_description="An agent equipped with Slack tools",
        model=os.environ["OPENAI_MODEL"],
        tools=slack_tools,
        hooks=CustomAgentHooks(display_name="Slack Agent"),
    )

    triage_agent = Agent(
        name="conversation_agent",
        instructions="You are a helpful assistant that can help with everyday"
                     " tasks. You can handoff to another agent with access to"
                     " Gmail tools if needed. You can also handoff to an agent"
                     " with Slack tools if needed. Handoff to the appropriate"
                     " agent based on the services required.",
        model=os.environ["OPENAI_MODEL"],
        handoffs=[google_agent, slack_agent],
        hooks=CustomAgentHooks(display_name="Conversation Agent")
    )

    google_agent.handoffs.extend([triage_agent, slack_agent])
    slack_agent.handoffs.extend([triage_agent, google_agent])

    history: list[TResponseInputItem] = []
    try:
        with trace("Arcade Agent SDK demo"):
            while True:
                # prompt = input("What would you like me to do?\n")
                # if len(history) == 0:
                #     prompt = ("get my latest 5 emails. Then summarize them."
                #               " Then send me (Mateo) a direct message on Slack"
                #               " that includes the summaries")
                #     history.append({"role": "user", "content": prompt})
                # else:
                #     prompt = input("You: ")
                #     if prompt.lower() == "exit":
                #         exit(0)

                prompt = input("You: ")
                if prompt.lower() == "exit":
                    exit(0)
                history.append({"role": "user", "content": prompt})
                try:
                    result = await Runner.run(
                        starting_agent=triage_agent,
                        input=history,
                        context=context
                    )
                    history = result.to_input_list()
                    print("Assistant:", result.final_output)
                except UserDeniedToolCall as e:
                    history.extend([
                        {
                            "role": "assistant",
                            "content": f"Please confirm the call to {e.message}"
                        },
                        {
                            "role": "user",
                            "content": "I changed my mind, please don't do it."
                        },
                        {
                            "role": "assistant",
                            "content": f"Ok, I won't call {e.message} now."
                            " What else can I do for you?"
                        }
                    ])
                    print(history[-1]["content"])
    except AuthorizationError as e:
        print("Please Login to service:", e)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
