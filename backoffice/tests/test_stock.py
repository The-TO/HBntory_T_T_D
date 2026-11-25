"""Automatic tests of the stock rules (stock_service.py).

Run from the backoffice/ folder:  python3 -m pytest tests

The tests use a temporary database in memory and a fake Product API:
the real database and the real API are never used.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

import product_client
import stock_service
from models import Base, Branch

SKU = "HB-LAP-1001"
MAIN = 1
NORTH = 2


@pytest.fixture(autouse=True)
def fake_environment(monkeypatch):
    """Give each test an empty database with two branches."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = scoped_session(sessionmaker(bind=engine))
    session.add_all([Branch(id=MAIN, name="Main"), Branch(id=NORTH, name="North")])
    session.commit()
    monkeypatch.setattr(stock_service, "db_session", session)

    def fake_get_product(sku):
        """Only one product exists. Like the real API, it also answers to "1"."""
        if sku not in (SKU, "1"):
            raise product_client.ProductNotFound(sku)
        return {"sku": SKU}

    monkeypatch.setattr(product_client, "get_product", fake_get_product)
    yield
    session.remove()


def test_add_stock():
    stock_service.add_stock(MAIN, SKU, "5")
    stock_service.add_stock(MAIN, SKU, "3")
    assert stock_service.get_quantity(MAIN, SKU) == 8


def test_sku_can_be_typed_in_lower_case():
    stock_service.add_stock(MAIN, "  hb-lap-1001 ", "2")
    assert stock_service.get_quantity(MAIN, SKU) == 2


def test_remove_stock():
    stock_service.add_stock(MAIN, SKU, "5")
    stock_service.remove_stock(MAIN, SKU, "2")
    assert stock_service.get_quantity(MAIN, SKU) == 3


def test_cannot_remove_more_than_available():
    stock_service.add_stock(MAIN, SKU, "5")
    with pytest.raises(stock_service.StockError):
        stock_service.remove_stock(MAIN, SKU, "6")
    assert stock_service.get_quantity(MAIN, SKU) == 5  # nothing changed


@pytest.mark.parametrize("quantity", [
    "0", "-1", "2.5", "abc", "",
    str(stock_service.MAX_QUANTITY + 1),
    "100000000000000000000",
])
def test_invalid_quantity_is_refused(quantity):
    with pytest.raises(stock_service.StockError):
        stock_service.add_stock(MAIN, SKU, quantity)
    assert stock_service.get_quantity(MAIN, SKU) == 0


def test_maximum_quantity_is_accepted():
    stock_service.add_stock(MAIN, SKU, str(stock_service.MAX_QUANTITY))
    assert stock_service.get_quantity(MAIN, SKU) == stock_service.MAX_QUANTITY


@pytest.mark.parametrize("product_id", ["", "#", "?q=x", "../categories", "HB LAP"])
def test_invalid_identifier_is_refused(product_id):
    with pytest.raises(stock_service.StockError):
        stock_service.add_stock(MAIN, product_id, "1")


def test_unknown_product_is_refused():
    with pytest.raises(stock_service.StockError):
        stock_service.add_stock(MAIN, "HB-NOPE", "1")


def test_numeric_id_is_refused():
    with pytest.raises(stock_service.StockError):
        stock_service.add_stock(MAIN, "1", "1")
    assert stock_service.get_quantity(MAIN, SKU) == 0


@pytest.mark.parametrize("product_id", ["", "#", "?q=x", "1"])
def test_checking_a_quantity_refuses_invalid_identifiers(product_id):
    with pytest.raises(stock_service.StockError):
        stock_service.get_quantity(MAIN, product_id)


def test_unavailable_product_api_refuses_the_addition(monkeypatch):
    def api_down(sku):
        raise product_client.ProductAPIError("down")

    monkeypatch.setattr(product_client, "get_product", api_down)
    with pytest.raises(stock_service.StockError):
        stock_service.add_stock(MAIN, SKU, "1")
    assert stock_service.get_quantity(MAIN, SKU) == 0


def test_unknown_branch_is_refused():
    with pytest.raises(stock_service.StockError):
        stock_service.add_stock(99, SKU, "1")


def test_branches_have_separate_stock():
    stock_service.add_stock(MAIN, SKU, "5")
    assert stock_service.get_quantity(NORTH, SKU) == 0
    with pytest.raises(stock_service.StockError):
        stock_service.remove_stock(NORTH, SKU, "1")
    assert stock_service.get_quantity(MAIN, SKU) == 5


def test_empty_lines_are_not_listed():
    stock_service.add_stock(MAIN, SKU, "1")
    stock_service.remove_stock(MAIN, SKU, "1")
    assert stock_service.list_stock(MAIN) == []
