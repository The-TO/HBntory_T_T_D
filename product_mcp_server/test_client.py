"""Test manuel du serveur MCP.

Lancement, depuis le dossier product_mcp_server/ :  python3 test_client.py
Il démarre server.py, affiche ses tools, puis les appelle un par un.

Chaque appel a un résultat attendu : "ok" (la réponse contient "ok": true)
ou un code d'erreur (par exemple "product_not_found"). Le script affiche
✅ ou ❌ pour chaque appel, puis un résumé. Il se termine avec le code 1
si au moins un appel ne donne pas le résultat attendu.

Prérequis : la Product API tourne et la base du Backoffice existe.
Deux cas ne peuvent pas être dans cette liste, car ils demandent de changer
l'environnement : à faire à la main (voir docs/mcp.md).
- Product API arrêtée : docker stop hbntory-external-products-api
- Base absente : HBNTORY_DB=/tmp/nothing.db python3 test_client.py
"""
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# (nom du tool, arguments, résultat attendu)
CALLS = [
    # --- Tools produits (Product API) ---
    ("list_products", {"search": "keyboard"}, "ok"),
    ("get_product", {"sku": "HB-LAP-1001"}, "ok"),
    ("get_product", {"sku": "Compact Keyboard ES"}, "ok"),
    ("get_product", {"sku": "HB-OLD-1301"}, "ok"),  # discontinued
    ("get_product", {"sku": "HB-DOES-NOT-EXIST"}, "product_not_found"),
    ("get_product", {"sku": ""}, "invalid_input"),

    # --- Tools stock (base de données) ---
    ("get_product_stock", {"sku": "HB-MON-2102"}, "ok"),
    ("get_product_stock", {"sku": "Compact Monitor 24"}, "ok"),
    ("get_product_stock", {"sku": "HB-KBD-4101"}, "ok"),  # en stock nulle part
    ("get_product_stock", {"sku": "monitor"}, "product_not_found"),  # vague
    ("get_branch_stock", {"branch": "main campus"}, "ok"),
    ("get_branch_stock", {"branch": "Paris"}, "branch_not_found"),

    # --- check_shopping_list ---
    ("check_shopping_list",
     {"items": [{"sku": "HB-MON-2102", "quantity": 2},
                {"sku": "HB-MON-2101", "quantity": 1}]}, "ok"),
    ("check_shopping_list",
     {"items": [{"sku": "HB-MON-2102", "quantity": 30}]}, "ok"),  # missing
    ("check_shopping_list",
     {"items": [{"sku": "HB-MON-2102", "quantity": 15}]}, "ok"),  # missing
    ("check_shopping_list",
     {"items": [{"sku": "Flying Carpet", "quantity": 2},
                {"sku": "HB-MON-2102", "quantity": 1}]}, "ok"),
    ("check_shopping_list",
     {"items": [{"sku": "Flying Carpet", "quantity": 2}]}, "unknown_product"),
    ("check_shopping_list",
     {"items": [{"sku": "HB-MON-2102", "quantity": 0}]}, "invalid_input"),
    ("check_shopping_list",
     {"items": [{"sku": "HB-MON-2102", "quantity": 2.9}]}, "invalid_input"),
    ("check_shopping_list", {"items": []}, "invalid_input"),
]


def result_text(result):
    """Le premier texte du résultat d'un tool ('' s'il n'y en a pas)."""
    for block in result.content:
        text = getattr(block, "text", None)
        if text:
            return text
    return ""


def outcome(text):
    """Résume une réponse du serveur : "ok", un code d'erreur, ou "?"."""
    try:
        data = json.loads(text)
    except ValueError:
        return "?"
    if not isinstance(data, dict):
        return "?"
    if data.get("ok") is True:
        return "ok"
    return data.get("error", "?")


async def main():
    """Start the MCP server and call each configured tool.
    """
    # sys.executable : le Python de ton environnement virtuel.
    # env : transmet tes variables d'environnement au serveur.
    server = StdioServerParameters(command=sys.executable,
                                   args=["server.py"],
                                   env=dict(os.environ))
    failures = 0
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("TOOLS:", [tool.name for tool in tools.tools])
            for name, arguments, expected in CALLS:
                result = await session.call_tool(name, arguments)
                text = result_text(result)
                # isError : le serveur MCP signale une erreur technique
                # (exception dans le tool, arguments refusés par la librairie).
                got = "isError" if result.isError else outcome(text)
                passed = got == expected
                failures += not passed
                print("\n>>>", name, arguments)
                print(text)
                print("%s attendu : %s, obtenu : %s"
                      % ("✅" if passed else "❌", expected, got))
    print("\n%d appel(s), %d échec(s)." % (len(CALLS), failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
