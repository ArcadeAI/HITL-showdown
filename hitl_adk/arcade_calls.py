from arcade_adk._utils import _get_arcade_tool_formats, get_arcade_client
from arcade_adk.tools import get_arcade_tools, ArcadeTool
import dotenv
import os
import pprint

dotenv.load_dotenv()


client = get_arcade_client(api_key=os.environ["ARCADE_API_KEY"])


async def main():
    pprint.pp(await _get_arcade_tool_formats(client, tools=["Google.ListEmails"]))
    google_tools = await get_arcade_tools(client, tools=["Google.ListEmails"])

    pprint.pp(
        google_tools[0]._get_declaration()
    )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
