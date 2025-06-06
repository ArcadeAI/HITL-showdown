from agents import (Agent, Runner, AgentHooks, Tool, RunContextWrapper,
                    TResponseInputItem,)
from functools import partial
from arcadepy import AsyncArcade
from agents_arcade import get_arcade_tools
from typing import Any
from jit_permissions.tools import (UserDeniedToolCall,
                                   confirm_tool_usage,
                                   auth_tool)

import dotenv
import os
import agentops
dotenv.load_dotenv()

AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY")

agentops.init(tags="arcade")

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
    }

    client = AsyncArcade()

    google_tools = await get_arcade_tools(
        client, tools=["Google_ListEmails", "Google_SendEmail"])
    slack_tools = await get_arcade_tools(
        client, tools=["Slack_ListUsers", "Slack_SendDmToUser"])

    for tool in google_tools + slack_tools:
        # - human in the loop
        if tool.name in ENFORCE_HUMAN_CONFIRMATION:
            tool.on_invoke_tool = partial(
                confirm_tool_usage,
                tool_name=tool.name,
                callback=tool.on_invoke_tool,
            )
        # - auth
        await auth_tool(client, tool.name, user_id=context["user_id"])

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

    conversation_agent = Agent(
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

    google_agent.handoffs.extend([conversation_agent, slack_agent])
    slack_agent.handoffs.extend([conversation_agent, google_agent])

    # initialize the conversation
    history: list[TResponseInputItem] = []
    # run the loop!
    while True:
        prompt = input("You: ")
        if prompt.lower() == "exit":
            break
        history.append({"role": "user", "content": prompt})
        try:
            result = await Runner.run(
                starting_agent=conversation_agent,
                input=history,
                context=context
            )
            history = result.to_input_list()
            print(result.final_output)
        except UserDeniedToolCall as e:
            history.extend([
                {"role": "assistant",
                 "content": f"Please confirm the call to {e.tool_name}"},
                {"role": "user",
                 "content": "I changed my mind, please don't do it!"},
                {"role": "assistant",
                 "content": f"Sure, I cancelled the call to {e.tool_name}."
                 " What else can I do for you today?"
                 },
            ])
            print(history[-1]["content"])

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
