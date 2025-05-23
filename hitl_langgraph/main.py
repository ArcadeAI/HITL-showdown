import os

# Import necessary classes and modules
from typing import Callable, Any
from langchain_arcade import ToolManager
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool, BaseTool
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import (END, START, MessagesState,
                             StateGraph)
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt, Command

from utils.hitl_commons import yes_no_loop

import pprint

from dotenv import load_dotenv

load_dotenv()

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


# Initialize the tool manager and fetch tools
manager = ToolManager(api_key=arcade_api_key)
manager.init_tools(toolkits=["Google"])

# convert to langchain tools and use interrupts for auth
tools = manager.to_langchain(use_interrupts=True)

tools = [add_human_in_the_loop(t) for t in tools]

# Initialize the prebuilt tool node
tool_node = ToolNode(tools)

# Create a language model instance and bind it with the tools
model = ChatOpenAI(model="gpt-4o")
model_with_tools = model.bind_tools(tools)


# Function to invoke the model and get a response
def call_agent(state: MessagesState):
    messages = state["messages"]
    response = model_with_tools.invoke(messages)
    # Return the updated message history
    return {"messages": [response]}


# Function to determine the next step in the workflow based on the last message
def should_continue(state: MessagesState):
    if state["messages"][-1].tool_calls:
        for tool_call in state["messages"][-1].tool_calls:
            if manager.requires_auth(tool_call["name"]):
                return "authorization"
        return "tools"  # Proceed to tool execution if no authorization is needed
    return END  # End the workflow if no tool calls are present


# Function to handle authorization for tools that require it
def authorize(state: MessagesState, config: dict):
    user_id = config["configurable"].get("user_id")
    for tool_call in state["messages"][-1].tool_calls:
        tool_name = tool_call["name"]
        if not manager.requires_auth(tool_name):
            continue
        auth_response = manager.authorize(tool_name, user_id)
        if auth_response.status != "completed":
            # Prompt the user to visit the authorization URL
            print(f"Visit the following URL to authorize: {auth_response.url}")

            # wait for the user to complete the authorization
            # and then check the authorization status again
            manager.wait_for_auth(auth_response.id)
            if not manager.is_authorized(auth_response.id):
                # node interrupt?
                raise ValueError("Authorization failed")

    return {"messages": []}


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
    # Build the workflow graph using StateGraph
    workflow = StateGraph(MessagesState)

    # Add nodes (steps) to the graph
    workflow.add_node("agent", call_agent)
    workflow.add_node("tools", tool_node)
    workflow.add_node("authorization", authorize)

    # Define the edges and control flow between nodes
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent",
                                   should_continue,
                                   ["authorization", "tools", END])
    workflow.add_edge("authorization", "tools")
    workflow.add_edge("tools", "agent")

    # Set up memory for checkpointing the state
    memory = MemorySaver()

    # Compile the graph with the checkpointer
    graph = workflow.compile(checkpointer=memory)

    config = {"configurable": {"thread_id": "4", "user_id": "mateo@arcade.dev"}}
    while True:

        user_input = input("User: ")
        if user_input.lower() == "exit":
            break

        user_message = {"messages": [{"role": "user", "content": user_input}]}
        run_graph(graph, config, user_message)

        # handle all interrupts in case there's any
        handle_interrupts(graph, config)
