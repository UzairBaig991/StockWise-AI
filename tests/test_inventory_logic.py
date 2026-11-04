from src.inventory_logic import compute_reorder_metrics


def test_reorder_logic_uses_expected_demand_and_safety_stock():
    metrics = compute_reorder_metrics(current_stock=40, safety_stock=15, lead_time_days=7, daily_demand=2.5)
    assert metrics["needs_review"] is False
    assert metrics["recommended_order_qty"] >= 0
    assert metrics["reorder_point"] > 0
