import os

# Import necessary classes and modules
from typing import Callable, Any
from langchain_arcade import ToolManager
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool, BaseTool
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langgraph.types import interrupt, Command

from utils.hitl_commons import yes_no_loop
# import agentops
import pprint

from dotenv import load_dotenv


load_dotenv()

AGENTOPS_API_KEY = os.getenv("AGENTOPS_API_KEY")
# agentops.init(tags=["hitl-google-adk"])

arcade_api_key = os.environ["ARCADE_API_KEY"]


def add_human_in_the_loop(
    target_tool: Callable | BaseTool,
) -> BaseTool:
    """Wrap a tool to support human-in-the-loop review."""
    if not isinstance(target_tool, BaseTool):
        target_tool = tool(target_tool)

    @tool(
        target_tool.name,
        description=target_tool.description,
        args_schema=target_tool.args_schema
    )
    def call_tool_with_interrupt(config: RunnableConfig, **tool_input):

        arguments = pprint.pformat(tool_input, indent=4)
        response = interrupt(
            f"Do you allow the call to {target_tool.name} with arguments:\n"
            f"{arguments}"
        )

        # approve the tool call
        if response == "yes":
            tool_response = target_tool.invoke(tool_input, config)
        # deny tool call
        elif response == "no":
            tool_response = "The User did not allow the tool to run"
        else:
            raise ValueError(
                f"Unsupported interrupt response type: {response}"
            )

        return tool_response

    return call_tool_with_interrupt


ENFORCE_HUMAN_CONFIRMATION = [
    "Google_SendEmail",
    "Slack_SendDmToUser",
]


def run_graph(graph: CompiledStateGraph, config, input: Any):
    for event in graph.stream(input, config=config, stream_mode="values"):
        if "messages" in event:
            # Pretty-print the last message
            event["messages"][-1].pretty_print()


def handle_interrupts(graph: CompiledStateGraph, config):
    for interr in graph.get_state(config).interrupts:
        approved = yes_no_loop(interr.value)
        run_graph(graph, config, Command(resume=approved))


if __name__ == "__main__":
    user_id = "mateo@arcade.dev"
    config = {"configurable": {"thread_id": "4",
                               "user_id": user_id}}
    # Set up memory for checkpointing the state
    memory = MemorySaver()

    # Initialize google tools
    manager = ToolManager(api_key=arcade_api_key)
    manager.init_tools(tools=["Google_ListEmails", "Google_SendEmail",
                              "Slack_ListUsers", "Slack_SendDmToUser"])

    for t in manager.tools:
        manager.authorize(tool_name=t, user_id=user_id)

    # separate tools for multiple agents
    google_tools = []
    slack_tools = []
    for t in manager.to_langchain(use_interrupts=True):
        print(t.name)
        if t.name.startswith("Google"):
            if t.name in ENFORCE_HUMAN_CONFIRMATION:
                print(f"Adding hitl to {t.name}")
                google_tools.append(add_human_in_the_loop(t))
            else:
                google_tools.append(t)
        if t.name.startswith("Slack"):
            if t.name in ENFORCE_HUMAN_CONFIRMATION:
                print(f"Adding hitl to {t.name}")
                slack_tools.append(add_human_in_the_loop(t))
            else:
                slack_tools.append(t)

    google_agent = create_react_agent(
        model="openai:gpt-4o",
        tools=google_tools,
        prompt="You are a helpful assistant that can assist using tools"
               " to manage a Google account, contacts, and inbox.",
        name="google_agent"
    )

    slack_agent = create_react_agent(
        model="openai:gpt-4o",
        tools=slack_tools,
        prompt="You are a helpful assistant that can assist using tools"
               " to interact with Slack."
               " You have tools to manage channels and send DMs.",
        name="slack_agent"
    )

    conversation_agent = create_supervisor(
        model=init_chat_model("openai:gpt-4o"),
        agents=[google_agent, slack_agent],
        prompt="You are a helpful assistant that can help with everyday"
               " tasks. You can handoff to another agent with access to"
               " Gmail tools if needed. You can also handoff to an agent"
               " with Slack tools if needed. Handoff to the appropriate"
               " agent based on the services required.",
        add_handoff_back_messages=True,
        output_mode="full_history",
    ).compile(checkpointer=memory)

    while True:

        user_input = input("User: ")
        if user_input.lower() == "exit":
            break

        user_message = {"messages": [{"role": "user", "content": user_input}]}
        run_graph(conversation_agent, config, user_message)

        # handle all interrupts in case there's any
        handle_interrupts(conversation_agent, config)
