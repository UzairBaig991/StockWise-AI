import json
import sqlite3
from typing import Any, Iterable

from src.config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL UNIQUE,
                name TEXT,
                category TEXT,
                unit_price REAL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory (
                product_id INTEGER PRIMARY KEY,
                current_stock REAL NOT NULL DEFAULT 0,
                safety_stock REAL NOT NULL DEFAULT 0,
                lead_time_days INTEGER NOT NULL DEFAULT 7,
                supplier_name TEXT,
                reorder_target_days INTEGER,
                unit_cost REAL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS import_batches (
                batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT,
                imported_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sales_transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_batch_id INTEGER,
                invoice_no TEXT,
                product_id INTEGER,
                invoice_date TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL,
                customer_id TEXT,
                country TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (import_batch_id) REFERENCES import_batches(batch_id),
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS forecasts (
                forecast_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                forecast_date TEXT NOT NULL,
                predicted_quantity REAL NOT NULL,
                model_name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS model_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                train_end_date TEXT,
                test_start_date TEXT,
                mae REAL,
                rmse REAL,
                baseline_mae REAL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                metadata_json TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sales_product_date ON sales_transactions(product_id, invoice_date)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_forecasts_sku_date ON forecasts(sku, forecast_date)"
        )


def ensure_product(sku: str, name: str | None = None, category: str | None = None, unit_price: float | None = None) -> int:
    with get_connection() as conn:
        existing = conn.execute("SELECT product_id FROM products WHERE sku = ?", (sku,)).fetchone()
        if existing:
            product_id = existing["product_id"]
            conn.execute(
                """
                UPDATE products
                SET name = COALESCE(?, name),
                    category = COALESCE(?, category),
                    unit_price = COALESCE(?, unit_price),
                    updated_at = datetime('now')
                WHERE product_id = ?
                """,
                (name, category, unit_price, product_id),
            )
            return product_id

        cursor = conn.execute(
            """
            INSERT INTO products (sku, name, category, unit_price, active, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, datetime('now'), datetime('now'))
            """,
            (sku, name or sku, category, unit_price),
        )
        return int(cursor.lastrowid)


def ensure_inventory_for_product(product_id: int, current_stock: float = 0, safety_stock: float = 0, lead_time_days: int = 7) -> None:
    with get_connection() as conn:
        row = conn.execute("SELECT product_id FROM inventory WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO inventory (product_id, current_stock, safety_stock, lead_time_days, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (product_id, current_stock, safety_stock, lead_time_days),
            )
        else:
            conn.execute(
                """
                UPDATE inventory
                SET current_stock = ?, safety_stock = ?, lead_time_days = ?, updated_at = datetime('now')
                WHERE product_id = ?
                """,
                (current_stock, safety_stock, lead_time_days, product_id),
            )


def save_transaction_batch(rows: Iterable[dict[str, Any]]) -> int:
    rows = list(rows)
    if not rows:
        return 0

    with get_connection() as conn:
        batch_id = conn.execute(
            "INSERT INTO import_batches (source_name, imported_at) VALUES (?, datetime('now'))",
            ("uploaded_data",),
        ).lastrowid

        for row in rows:
            product_id = row.get("product_id")
            if product_id is None:
                continue
            conn.execute(
                """
                INSERT INTO sales_transactions (
                    import_batch_id, invoice_no, product_id, invoice_date, quantity, unit_price, customer_id, country
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch_id,
                    row.get("invoice_no"),
                    product_id,
                    row.get("invoice_date"),
                    float(row.get("quantity", 0)),
                    row.get("unit_price"),
                    row.get("customer_id"),
                    row.get("country"),
                ),
            )

        return int(batch_id)


def fetch_products() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.product_id, p.sku, p.name, p.category, p.unit_price, p.active,
                   COALESCE(i.current_stock, 0) as current_stock,
                   COALESCE(i.safety_stock, 0) as safety_stock,
                   COALESCE(i.lead_time_days, 7) as lead_time_days
            FROM products p
            LEFT JOIN inventory i ON i.product_id = p.product_id
            ORDER BY p.sku
            """
        ).fetchall()
        return [dict(row) for row in rows]


def fetch_inventory_rows() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.sku, p.name, i.current_stock, i.safety_stock, i.lead_time_days,
                   i.supplier_name, i.reorder_target_days, i.unit_cost
            FROM inventory i
            JOIN products p ON p.product_id = i.product_id
            ORDER BY p.sku
            """
        ).fetchall()
        return [dict(row) for row in rows]


def update_inventory(product_id: int, current_stock: float, safety_stock: float, lead_time_days: int, supplier_name: str | None = None, reorder_target_days: int | None = None, unit_cost: float | None = None) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO inventory (product_id, current_stock, safety_stock, lead_time_days, supplier_name, reorder_target_days, unit_cost, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(product_id) DO UPDATE SET
                current_stock = excluded.current_stock,
                safety_stock = excluded.safety_stock,
                lead_time_days = excluded.lead_time_days,
                supplier_name = excluded.supplier_name,
                reorder_target_days = excluded.reorder_target_days,
                unit_cost = excluded.unit_cost,
                updated_at = datetime('now')
            """,
            (product_id, current_stock, safety_stock, lead_time_days, supplier_name, reorder_target_days, unit_cost),
        )


def fetch_product_sales(product_id: int | None = None) -> list[dict[str, Any]]:
    with get_connection() as conn:
        if product_id is None:
            rows = conn.execute(
                """
                SELECT p.sku, st.invoice_date, SUM(st.quantity) AS units_sold
                FROM sales_transactions st
                JOIN products p ON p.product_id = st.product_id
                GROUP BY p.sku, st.invoice_date
                ORDER BY st.invoice_date
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT p.sku, st.invoice_date, SUM(st.quantity) AS units_sold
                FROM sales_transactions st
                JOIN products p ON p.product_id = st.product_id
                WHERE st.product_id = ?
                GROUP BY p.sku, st.invoice_date
                ORDER BY st.invoice_date
                """,
                (product_id,),
            ).fetchall()
        return [dict(row) for row in rows]


def fetch_total_units() -> float:
    with get_connection() as conn:
        value = conn.execute("SELECT COALESCE(SUM(quantity), 0) FROM sales_transactions").fetchone()[0]
        return float(value or 0)


def fetch_recent_imports(limit: int = 10) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.sku, st.invoice_date, st.quantity, st.invoice_no, st.created_at
            FROM sales_transactions st
            JOIN products p ON p.product_id = st.product_id
            ORDER BY st.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def save_forecast_entries(rows: Iterable[dict[str, Any]]) -> None:
    with get_connection() as conn:
        for row in rows:
            conn.execute(
                """
                INSERT INTO forecasts (sku, forecast_date, predicted_quantity, model_name, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (row["sku"], row["forecast_date"], float(row["predicted_quantity"]), row["model_name"]),
            )


def fetch_low_stock_products() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.sku, p.name, i.current_stock, i.safety_stock, i.lead_time_days,
                   COALESCE(i.current_stock, 0) AS stock_level
            FROM products p
            JOIN inventory i ON i.product_id = p.product_id
            WHERE COALESCE(i.current_stock, 0) <= COALESCE(i.safety_stock, 0) + COALESCE(i.lead_time_days, 7) * 2
            ORDER BY p.sku
            """
        ).fetchall()
        return [dict(row) for row in rows]


def save_model_run(
    model_name: str,
    train_end_date: str | None,
    test_start_date: str | None,
    mae: float,
    rmse: float,
    baseline_mae: float,
    metadata_json: dict[str, Any] | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO model_runs (
                model_name, train_end_date, test_start_date, mae, rmse, baseline_mae, created_at, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'), ?)
            """,
            (model_name, train_end_date, test_start_date, mae, rmse, baseline_mae, json.dumps(metadata_json or {})),
        )


def fetch_model_runs(limit: int = 10) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT model_name, train_end_date, test_start_date, mae, rmse, baseline_mae, created_at, metadata_json
            FROM model_runs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    results: list[dict[str, Any]] = []
    for row in rows:
        payload = dict(row)
        metadata = payload.get("metadata_json")
        try:
            payload["metadata_json"] = json.loads(metadata) if metadata else {}
        except (TypeError, ValueError):
            payload["metadata_json"] = {}
        results.append(payload)
    return results
