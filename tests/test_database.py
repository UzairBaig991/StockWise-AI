from src.database import ensure_inventory_for_product, ensure_product, initialize_database


def test_database_initializes_and_stores_products(monkeypatch, tmp_path):
    test_db_path = tmp_path / "stockwise-test.db"
    monkeypatch.setattr("src.database.DB_PATH", test_db_path)
    initialize_database()
    product_id = ensure_product("SKU-123", name="Sample product")
    ensure_inventory_for_product(product_id, current_stock=12, safety_stock=5, lead_time_days=10)
    assert product_id > 0
    assert test_db_path.exists()
