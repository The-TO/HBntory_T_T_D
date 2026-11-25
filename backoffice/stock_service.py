"""Règles métier du stock. Toute modification du stock passe par ici."""
from db import db_session
from models import Branch, Stock
import product_client


class StockError(Exception):
    """Opération de stock refusée (le message est affichable).

    Raised when a stock operation cannot be completed.
    """


def parse_quantity(value):
    """Vérifie que la quantité est un entier strictement positif.
    """
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        raise StockError("Quantity must be a whole number.")
    if quantity <= 0:
        raise StockError("Quantity must be greater than zero.")
    return quantity


def _check_branch(branch_id):
    """Verifie que la branche existe
    """
    branch = db_session.get(Branch, branch_id)
    if branch is None:
        raise StockError("Unknown branch.")
    return branch


def _check_product(product_id):
    """Vérifie que le produit existe dans la Product API.
    """
    product_id = (product_id or "").strip().upper()
    if not product_id:
        raise StockError("Product identifier is required.")
    if not (product_id.isascii() and product_id.replace("-", "").isalnum()):
        raise StockError(
            "Invalid product identifier: use only letters, digits and hyphens."
        )
    try:
        product = product_client.get_product(product_id)
    except product_client.ProductNotFound:
        raise StockError("Product %s does not exist." % product_id)
    except product_client.ProductAPIError:
        raise StockError(
            "Product API unavailable: cannot check the product right now."
        )
    if product["sku"] != product_id:
        raise StockError("Use the product SKU (for example HB-LAP-1001), not his number.")
    return product["sku"]


def _find(branch_id, product_id):
    """Find a stock record for a branch and product.
    """
    return db_session.query(Stock).filter_by(
        branch_id=branch_id, product_id=product_id
    ).first()


def add_stock(branch_id, product_id, quantity):
    """Add a quantity of a product to a branch's stock.
    """
    quantity = parse_quantity(quantity)
    _check_branch(branch_id)
    sku = _check_product(product_id)
    item = _find(branch_id, sku)
    if item is None:
        item = Stock(branch_id=branch_id, product_id=sku, quantity=0)
        db_session.add(item)
    item.quantity += quantity
    db_session.commit()
    return item


def remove_stock(branch_id, product_id, quantity):
    """Remove a quantity of a product from a branch's stock.
    """
    quantity = parse_quantity(quantity)
    _check_branch(branch_id)
    sku = (product_id or "").strip().upper()
    item = _find(branch_id, sku)
    available = item.quantity if item else 0
    if quantity > available:
        raise StockError(
            "Not enough stock: %d available, %d requested."
            % (available, quantity)
        )
    item.quantity -= quantity
    db_session.commit()
    return item


def list_stock(branch_id):
    """Produits réellement en stock (quantité > 0) dans une branche.
    """
    return db_session.query(Stock).filter(
        Stock.branch_id == branch_id, Stock.quantity > 0
    ).order_by(Stock.product_id).all()


def get_quantity(branch_id, product_id):
    """Get the quantity of a product held by a branch.
    """
    item = _find(branch_id, (product_id or "").strip().upper())
    return item.quantity if item else 0
