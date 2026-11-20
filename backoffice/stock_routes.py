"""Routes for displaying and updating branch stock levels."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
import permissions
import stock_service
from db import db_session
from models import Branch
import product_client

stock_bp = Blueprint("stock", __name__, url_prefix="/stock")

@stock_bp.route("/")
def index():
    """Display stock for the current branch.
    """
    branch_id = permissions.current_branch_id()
    branch = db_session.get(Branch, branch_id)

    # Les infos produits viennent de la Product API, jamais de la base locale.
    try:
        products = product_client.products_by_sku()
    except product_client.ProductAPIError:
        products = {}
        flash("Product API unavailable: product names cannot be displayed.", "error")

    return render_template(
        "stock.html",
        branch_name=branch.name,
        items=stock_service.list_stock(branch_id),
        products=products,
    )



@stock_bp.route("/add", methods=["POST"])
def add():
    """Add the requested quantity of a product to the current branch.
    """
    branch_id = permissions.current_branch_id()
    try:
        item = stock_service.add_stock(
            branch_id, request.form.get("product_id"), request.form.get("quantity"))
        flash("Done: %s now has %d in stock." % (item.product_id, item.quantity))
    except stock_service.StockError as error:
        flash(str(error), "error")
    return redirect(url_for("stock.index"))


@stock_bp.route("/remove", methods=["POST"])
def remove():
    """Remove the requested quantity of a product from the current branch.
    """
    branch_id = permissions.current_branch_id()
    try:
        item = stock_service.remove_stock(
            branch_id, request.form.get("product_id"), request.form.get("quantity"))
        flash("Done: %s now has %d in stock." % (item.product_id, item.quantity))
    except stock_service.StockError as error:
        flash(str(error), "error")
    return redirect(url_for("stock.index"))

@stock_bp.route("/quantity")
def quantity():
    """Display the current branch's quantity for a product.
    """
    branch_id = permissions.current_branch_id()
    product_id = (request.args.get("product_id") or "").strip().upper()
    if not product_id:
        flash("Product id is required.", "error")
    else:
        amount = stock_service.get_quantity(branch_id, product_id)
        flash("%s: %d in stock." % (product_id, amount))

    return redirect(url_for("stock.index"))
