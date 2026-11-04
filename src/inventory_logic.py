from __future__ import annotations


def compute_reorder_metrics(
    current_stock: float,
    safety_stock: float,
    lead_time_days: int,
    daily_demand: float,
    review_period_days: int = 7,
) -> dict[str, float | bool]:
    lead_time_days = max(1, int(lead_time_days))
    expected_demand_during_lead = daily_demand * lead_time_days
    reorder_point = expected_demand_during_lead + safety_stock
    target_stock = expected_demand_during_lead + (daily_demand * review_period_days) + safety_stock
    recommended_order_qty = max(0.0, target_stock - current_stock)
    needs_review = current_stock <= reorder_point

    return {
        "expected_demand_during_lead_time": expected_demand_during_lead,
        "reorder_point": reorder_point,
        "target_stock": target_stock,
        "recommended_order_qty": recommended_order_qty,
        "needs_review": needs_review,
    }


def explain_reorder_reason(metrics: dict[str, float | bool], lead_time_days: int) -> str:
    if metrics["needs_review"]:
        return (
            f"Current stock is at or below the reorder point for a {lead_time_days}-day lead time. "
            f"This item should be reviewed with an order of {metrics['recommended_order_qty']:.1f} units."
        )
    return "Stock remains above the reorder threshold for the current lead time and safety stock assumptions."
