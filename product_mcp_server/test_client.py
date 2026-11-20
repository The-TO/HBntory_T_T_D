"""Test manuel du serveur MCP.

Lancement, depuis le dossier product_mcp_server/ :  python3 test_client.py
Il démarre server.py, affiche ses tools, puis les appelle un par un.
"""
import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# (nom du tool, arguments)
CALLS = [
    ("list_products", {"search": "keyboard"}),
    ("get_product", {"sku": "HB-LAP-1001"}),
    ("get_product", {"sku": "HB-DOES-NOT-EXIST"}),
    ("get_product", {"sku": ""}),
]


async def main():
    # sys.executable : le Python de ton environnement virtuel.
    # env : transmet tes variables d'environnement au serveur.
    server = StdioServerParameters(command=sys.executable,
                                   args=["server.py"],
                                   env=dict(os.environ))
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("TOOLS:", [tool.name for tool in tools.tools])
            for name, arguments in CALLS:
                result = await session.call_tool(name, arguments)
                print("\n>>>", name, arguments)
                print(result.content[0].text)


asyncio.run(main())