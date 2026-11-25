"""Serveur MCP de HBntory : les tools que l'agent IA peut appeler.

- list_products, get_product : lisent la Product API.
- get_product_stock, get_branch_stock, check_shopping_list :
  lisent le stock dans la base du Backoffice, en LECTURE SEULE.

Test manuel, depuis le dossier product_mcp_server/ :  python3 test_client.py

This module exposes product catalog and stock tools through an MCP server.
"""
import itertools
import os
import sqlite3
from contextlib import closing
from pathlib import Path
import requests
from mcp.server.fastmcp import FastMCP


PRODUCT_API_URL = os.environ.get("PRODUCT_API_URL", "http://localhost:5001")
#Chemin de la base du Backoffice, depuis le dossier ou on lance le
#programme (product_mcp_server/ ou ai_service/, tous deux à coté de Backoffice)
# DB_PATH = os.environ.get("HBNTORY_DB", "../data/hbntory.db")
# Modifié pour que ça soit plus pratique et polyvalent:
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get(
    "HBNTORY_DB", os.path.join(BASE_DIR, "..", "data", "hbntory.db")
)
# Cette version permets d'avoir le chemin sans avoir de pré-requis
# de dossier de lancement du programe
mcp = FastMCP("hbntory")


def error(code, message):
    """Le format d'erreur unique de tous les tools
    """
    return {"ok": False, "error": code, "message": message}

# ==================================================================
# 1. Tools produits (Product API)
# ==================================================================

def call_product_api(path, params=None):
    """Appelle la Product API. Renvoie (données, None) ou (None, erreur).
    """
    try:
        response = requests.get(PRODUCT_API_URL + path, params=params,
                                timeout=5)
    except requests.RequestException:
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
def get_product(sku: str) -> dict:
    """Get the full details of ONE product.

    `sku` can be the SKU (example: HB-LAP-1001) or the product name written by
    the customer: the tool finds the product itself. Never invent a SKU.
    `status` is "active" for a product sold normally and "discontinued" for a
    product that is no longer sold. It says nothing about the stock.
    """
    text = sku.strip()
    if not text:
        return error("invalid_input", "A product SKU or name is required.")
    names = product_names()  # {} if the Product API is down
    if names:
        sku, problem = resolve_product(text, names)
        if problem:
            return error("product_not_found", problem)
    else:
        sku = text.upper()  # catalog unavailable: we trust the SKU as given
    data, err = call_product_api("/api/v1/products/" + sku)
    if err:
        return err
    return {"ok": True, "product": {
        "sku": data["sku"],
        "name": data["name"],
        "description": data["description"],
        "category": data["category"],
        "brand": data["brand"],
        "unit_price": data["unit_price"],
        "currency": data["currency"],
        "status": "discontinued" if data["discontinued"] else "active",
    }}

# ==================================================================
# 2. Tools Stock
# ==================================================================

def query_db(sql, params=()):
    """Run a read-only query against the stock database.
    """
    path = Path(DB_PATH).resolve()
    unavailable = error("database_unavailable",
                        "The stock database cannot be read right now.")
    if not path.exists():
        return None, unavailable
    try:
        # mode=ro = nothing can be written through this connection.
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as conn:
            return conn.execute(sql, params).fetchall(), None
    except sqlite3.Error:
        return None, unavailable


def product_names():
    """Fetch product names by SKU.
    """
    data, err = call_product_api(
        "/api/v1/products", {"limit": 100, "include_discontinued": "true"}
    )
    if err:
        return {}
    return {p["sku"]: p["name"] for p in data["results"]}


def unknown_skus(skus):
    """SKUs that do not exist in the catalog.

    Returns [] if the Product API is down: we do not refuse a customer
    because of a catalog outage.
    """
    names = product_names()
    if not names:
        return []
    return [sku for sku in skus if sku not in names]


def resolve_product(text, names):
    """Turn a SKU or a product name into a SKU.

    Returns (sku, None), or (None, problem) if nothing (or too many things) match.
    `names` is the {sku: name} dictionary of the catalog.
    """
    wanted = text.strip().lower()
    if wanted.upper() in names:                       # already a real SKU
        return wanted.upper(), None
    same_name = [sku for sku, name in names.items() if name.lower() == wanted]
    if len(same_name) == 1:
        return same_name[0], None
    # Every word of the text must appear in the product name, in any order.
    words = wanted.split()
    matches = [sku for sku, name in names.items()
               if all(word in name.lower() for word in words)]
    if len(matches) == 1:
        return matches[0], None
    if matches:
        options = ", ".join("%s (%s)" % (names[sku], sku) for sku in matches[:5])
        return None, "'%s' matches several products: %s" % (text, options)
    return None, "'%s' matches no product of the catalog" % text


@mcp.tool()
def get_product_stock(sku: str) -> dict:
    """Get the stock of ONE product in every branch.

    `sku` can be the SKU (example: HB-LAP-1001) or the product name written by
    the customer: the tool finds the product itself. Never invent a SKU.
    For ONE product only, without a quantity. If the customer wants several
    products or gives quantities, use check_shopping_list instead.
    Only branches with at least one unit are listed. An empty list means the
    product is out of stock everywhere.
    """
    text = sku.strip()
    if not text:
        return error("invalid_input", "A product SKU or name is required.")
    names = product_names()  # {} if the Product API is down
    if names:
        sku, problem = resolve_product(text, names)
        if problem:
            return error("product_not_found", problem)
    else:
        sku = text.upper()  # catalog unavailable: we trust the SKU as given
    rows, err = query_db(
        "SELECT b.name, s.quantity FROM stock s "
        "JOIN branches b ON b.id = s.branch_id "
        "WHERE s.product_id = ? AND s.quantity > 0 ORDER BY b.name",
        (sku,),
    )
    if err:
        return err
    branches = [{"branch": name, "quantity": qty} for name, qty in rows]
    return {"ok": True, "sku": sku, "name": names.get(sku),
            "in_stock": bool(branches),
            "total": sum(b["quantity"] for b in branches), "branches": branches}


@mcp.tool()
def get_branch_stock(branch: str) -> dict:
    """List the products in stock in ONE branch, with their quantity.

    `branch` is the branch NAME, for example "Main Campus" (case does not matter).
    """
    branches, err = query_db("SELECT id, name FROM branches ORDER BY name")
    if err:
        return err
    wanted = branch.strip().lower()
    match = next((b for b in branches if b[1].lower() == wanted), None)
    if match is None:
        return error("branch_not_found",
                     "Unknown branch. Available branches: "
                     + ", ".join(b[1] for b in branches))
    rows, err = query_db(
        "SELECT product_id, quantity FROM stock "
        "WHERE branch_id = ? AND quantity > 0 ORDER BY product_id",
        (match[0],),
    )
    if err:
        return err
    names = product_names()
    products = [{"sku": sku, "name": names.get(sku), "quantity": qty}
                for sku, qty in rows]
    return {"ok": True, "branch": match[1], "products": products}


def parse_quantity(value):
    """Turn a quantity into a whole number, or return None if it is not one.

    Accepted: 2, 2.0, "2", "2.0". Refused (None): 2.9, "2.9", True, None,
    text, nan, inf. A quantity is never rounded or truncated silently.
    """
    if isinstance(value, bool):  # True would otherwise count as 1
        return None
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            try:
                value = float(value.strip())
            except ValueError:
                return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


@mcp.tool()
def check_shopping_list(items: list[dict]) -> dict:
    """Find which branch(es) to visit to buy a shopping list.

    Use this tool whenever the customer gives quantities, even for a single
    product. Never compute stock totals yourself.
    `items` is a list of objects with the keys "sku" and "quantity", for
    example [{"sku": "HB-LAP-1001", "quantity": 3}, {"sku": "Compact Keyboard ES",
    "quantity": 2}]. "sku" can be the SKU or the product name written by the
    customer: the tool finds the product itself. Never invent a SKU.
    Returns the branches that have EVERYTHING (`single_branch`), a visit `plan`
    using as few branches as possible, the products no branch can provide in
    full (`missing`), `products` (SKU -> name) and `unknown_products` (items not
    found in the catalog; the rest of the answer covers only the other items).
    """
    names = product_names()  # {} if the Product API is down
    wanted = {}
    unknown_products = []
    for item in items:
        try:
            text = str(item.get("sku", "")).strip()
            quantity = parse_quantity(item.get("quantity"))
        except AttributeError:  # the item is not an object
            return error("invalid_input",
                         "Each item needs a 'sku' and a whole 'quantity'.")
        if quantity is None:
            return error("invalid_input",
                         "The quantity must be a whole number (for example 2, "
                         "not 2.9).")
        if not text or quantity <= 0:
            return error("invalid_input",
                         "Each item needs a SKU and a quantity greater than zero.")
        if names:
            sku, problem = resolve_product(text, names)
            if problem:
                unknown_products.append(problem)
                continue
        else:
            sku = text.upper()  # catalog unavailable: we trust the SKU as given
        wanted[sku] = wanted.get(sku, 0) + quantity
    if not wanted:
        if unknown_products:
            return error("unknown_product", "; ".join(unknown_products))
        return error("invalid_input", "The shopping list is empty.")

    rows, err = query_db(
        "SELECT b.name, s.product_id, s.quantity FROM stock s "
        "JOIN branches b ON b.id = s.branch_id"
    )
    if err:
        return err
    stock = {}  # {branch: {sku: quantity}}
    for branch, sku, quantity in rows:
        stock.setdefault(branch, {})[sku] = quantity
    branches = sorted(stock)

    def has_enough(branch, sku):
        """Check whether a branch has the requested quantity of a SKU.
        """
        return stock[branch].get(sku, 0) >= wanted[sku]

    missing = []
    for sku, requested in wanted.items():
        if not any(has_enough(b, sku) for b in branches):
            missing.append({
                "sku": sku,
                "name": names.get(sku),
                "requested": requested,
                "by_branch": {b: stock[b].get(sku, 0) for b in branches},
                "note": "No single branch has the requested quantity.",
            })

    result = {
        "ok": True,
        "can_be_satisfied": not missing and not unknown_products,
        "single_branch": [b for b in branches
                          if all(has_enough(b, s) for s in wanted)],
        "missing": missing,
        "unknown_products": unknown_products,
        "products": {sku: names.get(sku, sku) for sku in wanted},
    }
    if not missing:
        for size in range(1, len(branches) + 1):
            group = next(
                (g for g in itertools.combinations(branches, size)
                 if all(any(has_enough(b, s) for b in g) for s in wanted)),
                None,
            )
            if group:
                visits = {}
                for sku, quantity in wanted.items():
                    branch = next(b for b in group if has_enough(b, sku))
                    visits.setdefault(branch, []).append(
                        {"sku": sku, "quantity": quantity})
                result["plan"] = [{"branch": b, "items": i}
                                  for b, i in visits.items()]
                break
    return result

if __name__ == "__main__":
    mcp.run()  # transport stdio
