"""Little HTTP Client for extern Product API (Read only)"""

import requests

import config


TIMEOUT = 5  # secondes : on attend pas l'API indefiniment


class ProductNotFound(Exception):
    """Le produit demandé n'existe pas dans la Product API"""


class ProductAPIError(Exception):
    """La Product API est injoignable ou a répondu par une erreur"""


def _get(path, params=None):
    url = config.PRODUCT_API_URL + path

    try:
        response = requests.get(url, params=params, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise ProductAPIError("Product API unreachable") from exc
    if response.status_code == 404:
        raise ProductNotFound(path)
    if response.status_code != 200:
        raise ProductAPIError(
            "Product API error (HTTP %d)" % response.status_code
        )
    return response.json()


def list_products():
    """Renvoie la liste des produits de catalogue (list de dict)"""
    data = _get("/api/v1/products", {"limit": 100, "sort": "name"})
    return data["results"]


def get_product(product_id):
    """Renvoi le detail d'un porduit à partir de son SKU"""
    return _get("/api/v1/products/" + product_id)


def products_by_sku():
    """Renvoie {sku: produit} pour retrouver un produit à partir de son SKU."""
    return {product["sku"]: product for product in list_products()}
