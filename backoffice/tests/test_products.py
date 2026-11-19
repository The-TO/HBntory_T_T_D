import product_client

#you to need to move this test in backoffice to start it 

def test_products_by_sku_indexes_products(monkeypatch):
    monkeypatch.setattr(
        product_client,
        "list_products",
        lambda: [{"sku": "A1", "name": "Pen"}, {"sku": "B2", "name": "Book"}],
    )
    result = product_client.products_by_sku()
    assert result["A1"]["name"] == "Pen"
    assert set(result) == {"A1", "B2"}
