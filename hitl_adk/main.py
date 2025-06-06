from arcadepy import AsyncArcade
from dotenv import load_dotenv
from google.adk import Agent, Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService, Session
from google_adk_arcade.tools import get_arcade_tools
from google.genai import types
from jit_permissions.tools import auth_tool, confirm_tool_usage

import agentops
import os


load_dotenv(override=True)

AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY")
agentops.init(tags=["hitl-google-adk"])


async def main():
    app_name = 'my_app'
    user_id = 'mateo@arcade.dev'

    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()
    client = AsyncArcade()

    google_tools = await get_arcade_tools(
        client, tools=["Google_ListEmails", "Google_SendEmail"])
    slack_tools = await get_arcade_tools(
        client, tools=["Slack_ListUsers", "Slack_SendDmToUser"])

    for tool in google_tools + slack_tools:
        # - human in the loop
        # if tool.name in ENFORCE_HUMAN_CONFIRMATION:
        #     tool.on_invoke_tool = partial(
        #         confirm_tool_usage,
        #         tool_name=tool.name,
        #         callback=tool.on_invoke_tool,
        #     )
        # - auth
        await auth_tool(client, tool_name=tool.name, user_id=user_id)

    google_agent = Agent(
        model=LiteLlm(model=f"openai/{os.environ["OPENAI_MODEL"]}"),
        name="google_agent",
        instruction="You are a helpful assistant that can assist using tools"
                    " to manage a Google account, contacts, and inbox.",
        description="An agent equipped with Google tools",
        tools=google_tools,
        before_tool_callback=[confirm_tool_usage],
    )

    slack_agent = Agent(
        model=LiteLlm(model=f"openai/{os.environ["OPENAI_MODEL"]}"),
        name="slack_agent",
        instruction="You are a helpful assistant that can assist using tools"
                    " to interact with Slack."
                    " You have tools to manage channels and send DMs.",
        description="An agent equipped with Slack tools",
        tools=slack_tools,
        before_tool_callback=[confirm_tool_usage],
    )

    conversation_agent = Agent(
        model=LiteLlm(model=f"openai/{os.environ["OPENAI_MODEL"]}"),
        name="conversation_agent",
        instruction="You are a helpful assistant that can help with everyday"
                    " tasks. You can handoff to another agent with access to"
                    " Gmail tools if needed. You can also handoff to an agent"
                    " with Slack tools if needed. Handoff to the appropriate"
                    " agent based on the services required.",
        sub_agents=[google_agent, slack_agent],
    )

    session = await session_service.create_session(
        app_name=app_name, user_id=user_id, state={
            "user_id": user_id,
        }
    )
    runner = Runner(
        app_name=app_name,
        agent=conversation_agent,
        artifact_service=artifact_service,
        session_service=session_service,
    )

    async def run_prompt(session: Session, new_message: str):
        content = types.Content(
            role='user', parts=[types.Part.from_text(text=new_message)]
        )
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.content.parts and event.content.parts[0].text:
                print(f'** {event.author}: {event.content.parts[0].text}')

    while True:
        user_input = input("User: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        await run_prompt(session, user_input)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
