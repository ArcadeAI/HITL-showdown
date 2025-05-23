from agents import AgentsException, RunContextWrapper
from pprint import pp
import json


class UserDeniedToolCall(AgentsException):
    """Exception raised when an user denies a tool call"""

    message: str

    def __init__(self, message: str):
        self.message = message


async def confirm_tool_usage(context: RunContextWrapper,
                             tool_args: str,
                             tool_name: str,
                             callback) -> str:
    """
    Ask the user to confirm the use of a specific tool

    Args:
        text (str): The clarification question to ask the user.

    Returns:
        str: The clarification from the user (y or n)
    """
    print("\nThe agent is asking for clarification:\n"
          f"I'm about to call {tool_name} with these parameters {tool_args}\n"
          "Do you approve?")
    clarification = input("Your response [y/n]: ")
    while clarification.lower() not in ["y", "n"]:
        clarification = input("Your response (must be either y or n): ")
    if clarification.lower() == "y":
        return await callback(context, tool_args)
    raise UserDeniedToolCall(tool_name)
