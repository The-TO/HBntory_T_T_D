"""Serveur MCP de HBntory : les tools que l'agent IA peut appeler.

- list_products, get_product : lisent la Product API.
- get_product_stock, get_branch_stock, check_shopping_list :
  lisent le stock dans la base du Backoffice, en LECTURE SEULE.

Test manuel, depuis le dossier product_mcp_server/ :  python3 test_client.py
"""

import os
import sqlite3

import requests
from mcp.server.fastmcp import FastMCP


PRODUCT_API_URL = os.environ.get("PRODUCT_API_URL", "http://localhost:5001")
#Chemin de la base du Backoffice, depuis le dossier ou on lance le 
#programme (product_mcp_server/ ou ai_service/, tous deux à coté de Backoffice)
DB_PATH = os.environ.get("HBNTORY_DB", "../backoffice/hbntory.db")

mcp = FastMCP("hbntory")


def error(code, message):
    """Le format d'erreur unique de tous les tools"""
    return {"ok": False, "error": code, "message": message}

# ==================================================================
# 1. Tools produits (Product API)
# ==================================================================

def call_product_api(path, params=None):
    """Appelle la Product API. Renvoie (données, None) ou (None, erreur)."""
    try:
        response = requests.get(PRODUCT_API_URL + PATH, params=params,
                                timeout=5)
    except requests.RequestExecption:
        return None, error("product_api_unavailable",
                           "The Product API cannot be reached. Product "
                           "information is unavailable right now.")
    if response.status_code == 404:
        return None, error("product_not_found",
                           "No product matches this SKU")
    if response.status_code != 200:
        return None, error("product_api_unavailable",
                           "The Product API returned an error. Product "
                           "information is unavailable right now.")
    return response.json(), None


@mcp.tool()
def list_products(search: str = "") -> dict:
    """List the products of the catalog: sku, name, category, price.
    
    Use `search`to find a product by a word of its name (example:
    "mouse"). Leave it empty to list every product.
    """

    params = {"limit": 100}
    if search.strip():
        params["q"] = search.strip()
    data, err = call_product_api("/api/v1/products", params)
    if err:
        return err
    products = []
    for p in data["results"]:
        products.append({"sku": p["sku"], "name": p["name"],
                         "category": p["category"],
                         "unit_price": p["unit_price"],
                         "currency": p["currency"]})
    return {"ok": True, "products": products}

@mcp.tool()
def get_product(sku: str) ->dict:
    """Get the full details of ONE product from its SKU (example: HB-LAP-1001).
    """
    sku = sku.strip().upper()
    if not sku:
        return error("invalid_input", "A product SKU is required.")
    data, err = call_product_api("/api/v1/products/" + sku)
    if err:
        return err
    return {"ok": True, "product": {
        "sku": data["sku"],
        "name":data["name"],
        "description":data["description"],
        "category":data["category"],
        "brand":data["brand"],
        "unit_price":data["unit_price"],
        "currency":data["currency"],
        "discountinued":data["discontinued"],
    }}

if __name__ == "__mpain__":
    mcp.run()  # transport stdio