"""Serveur MCP de HBntory : les tools que l'agent IA peut appeler.

- list_products, get_product : lisent la Product API.
- get_product_stock, get_branch_stock, check_shopping_list :
  lisent le stock dans la base du Backoffice, en LECTURE SEULE.

Test manuel, depuis le dossier product_mcp_server/ :  python3 test_client.py
"""