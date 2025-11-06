from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

__all__ = ["RuntimeDatabase"]

DATASETS: Tuple[str, ...] = (
    "products",
    "sales",
    "customers",
    "orders",
    "order_items",
)

TABLE_META: Dict[str, Dict[str, Any]] = {
    "products": {
        "primary_key": ["sku"],
        "required": ["sku", "name", "category", "unit_price", "inventory", "status"],
        "columns": ["sku", "name", "category", "unit_price", "inventory", "status"],
    },
    "sales": {
        "primary_key": ["date"],
        "required": ["date", "total", "orders", "avg_order_value", "new_customers"],
        "columns": ["date", "total", "orders", "avg_order_value", "new_customers"],
    },
    "customers": {
        "primary_key": ["id"],
        "required": [
            "id",
            "name",
            "email",
            "segment",
            "city",
            "country",
            "lifetime_value",
            "joined_date",
        ],
        "columns": [
            "id",
            "name",
            "email",
            "segment",
            "city",
            "country",
            "lifetime_value",
            "joined_date",
        ],
    },
    "orders": {
        "primary_key": ["id"],
        "required": [
            "id",
            "customer_id",
            "order_date",
            "status",
            "channel",
            "total",
        ],
        "columns": [
            "id",
            "customer_id",
            "order_date",
            "status",
            "channel",
            "total",
        ],
    },
    "order_items": {
        "primary_key": ["id"],
        "required": ["order_id", "product_sku", "quantity", "unit_price"],
        "columns": ["id", "order_id", "product_sku", "quantity", "unit_price"],
        "auto": ["id"],
    },
}

PRODUCTS: List[Dict[str, Any]] = [
    {
        "sku": "LNR-001",
        "name": "Lunar Lamp",
        "category": "Lighting",
        "unit_price": 49.00,
        "inventory": 125,
        "status": "active",
    },
    {
        "sku": "SLR-002",
        "name": "Solar Speaker",
        "category": "Audio",
        "unit_price": 89.00,
        "inventory": 82,
        "status": "active",
    },
    {
        "sku": "GLX-003",
        "name": "Galaxy Projector",
        "category": "Lighting",
        "unit_price": 129.00,
        "inventory": 48,
        "status": "active",
    },
    {
        "sku": "AUR-004",
        "name": "Aurora Clock",
        "category": "Home",
        "unit_price": 75.00,
        "inventory": 60,
        "status": "active",
    },
    {
        "sku": "COS-005",
        "name": "Cosmic Candle",
        "category": "Home",
        "unit_price": 25.00,
        "inventory": 210,
        "status": "active",
    },
    {
        "sku": "STL-006",
        "name": "Starlight Charger",
        "category": "Accessories",
        "unit_price": 39.00,
        "inventory": 155,
        "status": "active",
    },
    {
        "sku": "MET-007",
        "name": "Meteor Mug",
        "category": "Kitchen",
        "unit_price": 19.00,
        "inventory": 260,
        "status": "active",
    },
    {
        "sku": "NEB-008",
        "name": "Nebula Diffuser",
        "category": "Wellness",
        "unit_price": 59.00,
        "inventory": 95,
        "status": "active",
    },
    {
        "sku": "ORB-009",
        "name": "Orbit Headphones",
        "category": "Audio",
        "unit_price": 139.00,
        "inventory": 70,
        "status": "backorder",
    },
    {
        "sku": "ECL-010",
        "name": "Eclipse Watch",
        "category": "Wearables",
        "unit_price": 199.00,
        "inventory": 38,
        "status": "preorder",
    },
]

CUSTOMERS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "name": "Aisha Khan",
        "email": "aisha.khan@example.com",
        "segment": "Premium",
        "city": "Seattle",
        "country": "USA",
        "lifetime_value": 4820.50,
        "joined_date": "2022-03-14",
    },
    {
        "id": 2,
        "name": "Leo Martinez",
        "email": "leo.martinez@example.com",
        "segment": "Loyal",
        "city": "Austin",
        "country": "USA",
        "lifetime_value": 3655.20,
        "joined_date": "2021-11-02",
    },
    {
        "id": 3,
        "name": "Harper Chen",
        "email": "harper.chen@example.com",
        "segment": "New",
        "city": "San Francisco",
        "country": "USA",
        "lifetime_value": 940.75,
        "joined_date": "2024-01-18",
    },
    {
        "id": 4,
        "name": "Mateo Silva",
        "email": "mateo.silva@example.com",
        "segment": "At Risk",
        "city": "Toronto",
        "country": "Canada",
        "lifetime_value": 2110.40,
        "joined_date": "2020-07-09",
    },
    {
        "id": 5,
        "name": "Sofia Ibarra",
        "email": "sofia.ibarra@example.com",
        "segment": "Premium",
        "city": "Miami",
        "country": "USA",
        "lifetime_value": 5320.10,
        "joined_date": "2019-05-27",
    },
    {
        "id": 6,
        "name": "Noah Becker",
        "email": "noah.becker@example.com",
        "segment": "Loyal",
        "city": "Berlin",
        "country": "Germany",
        "lifetime_value": 2985.90,
        "joined_date": "2023-04-06",
    },
]

_SALES_BASE: List[Tuple[str, float]] = [
    ("2025-10-01", 500.0),
    ("2025-10-02", 720.0),
    ("2025-10-03", 610.0),
    ("2025-10-04", 680.0),
    ("2025-10-05", 455.0),
    ("2025-10-06", 790.0),
    ("2025-10-07", 1020.0),
    ("2025-10-08", 880.0),
    ("2025-10-09", 940.0),
    ("2025-10-10", 560.0),
    ("2025-10-11", 730.0),
    ("2025-10-12", 845.0),
    ("2025-10-13", 620.0),
    ("2025-10-14", 970.0),
    ("2025-10-15", 1090.0),
    ("2025-10-16", 780.0),
    ("2025-10-17", 830.0),
    ("2025-10-18", 675.0),
    ("2025-10-19", 940.0),
    ("2025-10-20", 995.0),
    ("2025-10-21", 1105.0),
    ("2025-10-22", 910.0),
    ("2025-10-23", 765.0),
    ("2025-10-24", 830.0),
    ("2025-10-25", 1190.0),
    ("2025-10-26", 880.0),
    ("2025-10-27", 970.0),
    ("2025-10-28", 1050.0),
    ("2025-10-29", 990.0),
    ("2025-10-30", 1125.0),
    ("2025-10-31", 1230.0),
]


def _build_sales_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for date, total in _SALES_BASE:
        orders = max(18, round(total / 22))
        new_customers = max(2, orders // 5)
        avg_order_value = round(total / orders, 2)
        rows.append(
            {
                "date": date,
                "total": total,
                "orders": orders,
                "avg_order_value": avg_order_value,
                "new_customers": new_customers,
            }
        )
    return rows


SALES: List[Dict[str, Any]] = _build_sales_rows()

_ORDER_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "SO-1001",
        "customer_id": 1,
        "order_date": "2025-10-01",
        "status": "fulfilled",
        "channel": "online",
        "items": [
            {"product_sku": "LNR-001", "quantity": 1},
            {"product_sku": "STL-006", "quantity": 2},
        ],
    },
    {
        "id": "SO-1002",
        "customer_id": 3,
        "order_date": "2025-10-02",
        "status": "fulfilled",
        "channel": "online",
        "items": [
            {"product_sku": "GLX-003", "quantity": 1},
            {"product_sku": "COS-005", "quantity": 2},
        ],
    },
    {
        "id": "SO-1003",
        "customer_id": 4,
        "order_date": "2025-10-03",
        "status": "fulfilled",
        "channel": "retail",
        "items": [
            {"product_sku": "ORB-009", "quantity": 1},
        ],
    },
    {
        "id": "SO-1004",
        "customer_id": 2,
        "order_date": "2025-10-04",
        "status": "fulfilled",
        "channel": "online",
        "items": [
            {"product_sku": "NEB-008", "quantity": 1},
            {"product_sku": "MET-007", "quantity": 4},
        ],
    },
    {
        "id": "SO-1005",
        "customer_id": 5,
        "order_date": "2025-10-05",
        "status": "fulfilled",
        "channel": "online",
        "items": [
            {"product_sku": "ECL-010", "quantity": 1},
        ],
    },
    {
        "id": "SO-1006",
        "customer_id": 6,
        "order_date": "2025-10-06",
        "status": "processing",
        "channel": "online",
        "items": [
            {"product_sku": "SLR-002", "quantity": 1},
            {"product_sku": "COS-005", "quantity": 3},
        ],
    },
    {
        "id": "SO-1007",
        "customer_id": 1,
        "order_date": "2025-10-07",
        "status": "fulfilled",
        "channel": "retail",
        "items": [
            {"product_sku": "AUR-004", "quantity": 1},
            {"product_sku": "COS-005", "quantity": 2},
            {"product_sku": "MET-007", "quantity": 2},
        ],
    },
    {
        "id": "SO-1008",
        "customer_id": 2,
        "order_date": "2025-10-08",
        "status": "fulfilled",
        "channel": "online",
        "items": [
            {"product_sku": "LNR-001", "quantity": 2},
            {"product_sku": "NEB-008", "quantity": 1},
        ],
    },
    {
        "id": "SO-1009",
        "customer_id": 3,
        "order_date": "2025-10-09",
        "status": "fulfilled",
        "channel": "online",
        "items": [
            {"product_sku": "STL-006", "quantity": 1},
            {"product_sku": "MET-007", "quantity": 4},
        ],
    },
    {
        "id": "SO-1010",
        "customer_id": 4,
        "order_date": "2025-10-10",
        "status": "fulfilled",
        "channel": "retail",
        "items": [
            {"product_sku": "AUR-004", "quantity": 2},
            {"product_sku": "COS-005", "quantity": 1},
        ],
    },
    {
        "id": "SO-1011",
        "customer_id": 5,
        "order_date": "2025-10-11",
        "status": "processing",
        "channel": "online",
        "items": [
            {"product_sku": "ORB-009", "quantity": 1},
            {"product_sku": "MET-007", "quantity": 2},
        ],
    },
    {
        "id": "SO-1012",
        "customer_id": 6,
        "order_date": "2025-10-12",
        "status": "fulfilled",
        "channel": "online",
        "items": [
            {"product_sku": "GLX-003", "quantity": 1},
            {"product_sku": "SLR-002", "quantity": 1},
        ],
    },
]


def _build_orders() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    price_lookup = {row["sku"]: row["unit_price"] for row in PRODUCTS}
    orders: List[Dict[str, Any]] = []
    order_items: List[Dict[str, Any]] = []

    for template in _ORDER_TEMPLATES:
        total = 0.0
        for item in template["items"]:
            sku = item["product_sku"]
            quantity = int(item["quantity"])
            unit_price = price_lookup[sku]
            total += unit_price * quantity
            order_items.append(
                {
                    "order_id": template["id"],
                    "product_sku": sku,
                    "quantity": quantity,
                    "unit_price": unit_price,
                }
            )
        orders.append(
            {
                "id": template["id"],
                "customer_id": template["customer_id"],
                "order_date": template["order_date"],
                "status": template["status"],
                "channel": template["channel"],
                "total": round(total, 2),
            }
        )
    return orders, order_items


ORDERS, ORDER_ITEMS = _build_orders()

DEFAULT_ORDER_BY: Dict[str, str] = {
    "products": "name",
    "sales": "date",
    "customers": "joined_date DESC",
    "orders": "order_date DESC",
    "order_items": "order_id",
}


class RuntimeDatabase:
    """SQLite-backed dataset store seeded with realistic sample data."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else Path(__file__).with_name("runtime.db")
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    sku TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    unit_price REAL NOT NULL,
                    inventory INTEGER NOT NULL,
                    status TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sales (
                    date TEXT PRIMARY KEY,
                    total REAL NOT NULL,
                    orders INTEGER NOT NULL,
                    avg_order_value REAL NOT NULL,
                    new_customers INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    segment TEXT NOT NULL,
                    city TEXT NOT NULL,
                    country TEXT NOT NULL,
                    lifetime_value REAL NOT NULL,
                    joined_date TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    customer_id INTEGER NOT NULL,
                    order_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    total REAL NOT NULL,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                );
                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL,
                    product_sku TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price REAL NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(id),
                    FOREIGN KEY (product_sku) REFERENCES products(sku)
                );
                """
            )

            if self._requires_seed(conn):
                self._seed(conn)

    @staticmethod
    def _requires_seed(conn: sqlite3.Connection) -> bool:
        cur = conn.execute("SELECT COUNT(1) FROM products")
        total = cur.fetchone()
        return not total or int(total[0]) == 0

    def _seed(self, conn: sqlite3.Connection) -> None:
        conn.executemany(
            """
            INSERT INTO products (sku, name, category, unit_price, inventory, status)
            VALUES (:sku, :name, :category, :unit_price, :inventory, :status)
            """,
            PRODUCTS,
        )
        conn.executemany(
            """
            INSERT INTO sales (date, total, orders, avg_order_value, new_customers)
            VALUES (:date, :total, :orders, :avg_order_value, :new_customers)
            """,
            SALES,
        )
        conn.executemany(
            """
            INSERT INTO customers (id, name, email, segment, city, country, lifetime_value, joined_date)
            VALUES (:id, :name, :email, :segment, :city, :country, :lifetime_value, :joined_date)
            """,
            CUSTOMERS,
        )
        conn.executemany(
            """
            INSERT INTO orders (id, customer_id, order_date, status, channel, total)
            VALUES (:id, :customer_id, :order_date, :status, :channel, :total)
            """,
            ORDERS,
        )
        conn.executemany(
            """
            INSERT INTO order_items (order_id, product_sku, quantity, unit_price)
            VALUES (:order_id, :product_sku, :quantity, :unit_price)
            """,
            ORDER_ITEMS,
        )

    def get_rows(self, source: str, days: int | None = None) -> List[Dict[str, Any]]:
        source = source.lower()
        if source not in DATASETS:
            return []

        params: Iterable[Any] = ()
        order_clause = DEFAULT_ORDER_BY.get(source)
        query = f"SELECT * FROM {source}"

        if source == "sales" and days is not None and days > 0:
            query += " ORDER BY date DESC LIMIT ?"
            params = (days,)
        elif order_clause:
            query += f" ORDER BY {order_clause}"

        with self._connect() as conn:
            cursor = conn.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]

        if source == "sales" and days is not None and days > 0:
            rows.reverse()

        return rows

    def describe_sources(self) -> Dict[str, Dict[str, Any]]:
        summary: Dict[str, Dict[str, Any]] = {}
        with self._connect() as conn:
            for table in DATASETS:
                columns = [
                    info[1] for info in conn.execute(f"PRAGMA table_info({table})").fetchall()
                ]
                total = conn.execute(f"SELECT COUNT(1) FROM {table}").fetchone()
                summary[table] = {
                    "rows": int(total[0]) if total else 0,
                    "fields": columns,
                }
        return summary

    @property
    def available_sources(self) -> List[str]:
        return list(DATASETS)

    # ----- Mutation helpers -----

    def run_select(self, query: str, params: Iterable[Any] | Dict[str, Any] | None = None) -> Dict[str, Any]:
        if not isinstance(query, str):
            return {"ok": False, "message": "Query must be a string."}

        cleaned = query.strip()
        if not cleaned.lower().startswith("select"):
            return {
                "ok": False,
                "message": "Only SELECT statements are allowed via this tool.",
            }

        if ";" in cleaned[:-1]:
            return {
                "ok": False,
                "message": "Multiple SQL statements are not permitted.",
            }

        bound_params = params or ()

        with self._connect() as conn:
            try:
                cursor = conn.execute(cleaned, bound_params)
            except Exception as exc:
                return {"ok": False, "message": f"Query failed: {exc}"}
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return {"ok": True, "rows": rows, "columns": columns}

    def _get_meta(self, source: str) -> Dict[str, Any]:
        return TABLE_META.get(source)

    def _missing_required(
        self, meta: Dict[str, Any], payload: Dict[str, Any]
    ) -> List[str]:
        required = meta.get("required", [])
        missing: List[str] = []
        for field in required:
            if payload.get(field) in (None, ""):
                missing.append(field)
        return missing

    def _normalize_columns(
        self, meta: Dict[str, Any], payload: Dict[str, Any]
    ) -> List[str]:
        columns = meta.get("columns", [])
        return [col for col in columns if col in payload]

    def _fetch_by_pk(
        self, conn: sqlite3.Connection, source: str, meta: Dict[str, Any], values: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        pk_fields: List[str] = meta.get("primary_key", [])
        if not pk_fields or not all(field in values for field in pk_fields):
            return None
        where_clause = " AND ".join([f"{field} = ?" for field in pk_fields])
        params = [values[field] for field in pk_fields]
        row = conn.execute(
            f"SELECT * FROM {source} WHERE {where_clause} LIMIT 1",
            params,
        ).fetchone()
        return dict(row) if row else None

    def insert_row(self, source: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        meta = self._get_meta(source)
        if not meta:
            return {"ok": False, "message": f"Unknown source '{source}'"}

        missing = self._missing_required(meta, payload)
        if missing:
            return {
                "ok": False,
                "message": f"Missing required fields for '{source}'",
                "missing": missing,
            }

        columns = self._normalize_columns(meta, payload)
        if not columns:
            return {
                "ok": False,
                "message": f"No valid columns provided for '{source}'",
                "missing": meta.get("required", []),
            }

        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)

        with self._connect() as conn:
            cursor = conn.execute(
                f"INSERT INTO {source} ({col_names}) VALUES ({placeholders})",
                [payload[col] for col in columns],
            )
            pk_fields = meta.get("primary_key", [])
            pk_values = {field: payload.get(field) for field in pk_fields}

            auto_fields = meta.get("auto", [])
            for field in auto_fields:
                if field in pk_fields and pk_values.get(field) in (None, ""):
                    pk_values[field] = cursor.lastrowid

            row = self._fetch_by_pk(conn, source, meta, pk_values) if pk_fields else None

        dataset = self.get_rows(source)
        return {
            "ok": True,
            "message": f"Inserted row into '{source}'",
            "dataset": dataset,
            "row": row,
        }

    def update_row(self, source: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        meta = self._get_meta(source)
        if not meta:
            return {"ok": False, "message": f"Unknown source '{source}'"}

        pk_fields: List[str] = meta.get("primary_key", [])
        if not pk_fields:
            return {"ok": False, "message": f"No primary key defined for '{source}'"}

        missing_keys = [field for field in pk_fields if payload.get(field) in (None, "")]
        if missing_keys:
            return {
                "ok": False,
                "message": f"Missing primary key fields for '{source}'",
                "missing": missing_keys,
            }

        updates = {
            key: value
            for key, value in payload.items()
            if key in meta.get("columns", []) and key not in pk_fields
        }

        if not updates:
            return {
                "ok": False,
                "message": f"No updatable fields provided for '{source}'",
            }

        set_clause = ", ".join([f"{col} = ?" for col in updates])
        where_clause = " AND ".join([f"{field} = ?" for field in pk_fields])

        with self._connect() as conn:
            params = list(updates.values()) + [payload[field] for field in pk_fields]
            cursor = conn.execute(
                f"UPDATE {source} SET {set_clause} WHERE {where_clause}",
                params,
            )
            if cursor.rowcount == 0:
                return {
                    "ok": False,
                    "message": f"No matching row found in '{source}' for provided key.",
                }
            row = self._fetch_by_pk(conn, source, meta, payload)

        dataset = self.get_rows(source)
        return {
            "ok": True,
            "message": f"Updated row in '{source}'",
            "dataset": dataset,
            "row": row,
        }

    def delete_row(self, source: str, key_fields: Dict[str, Any]) -> Dict[str, Any]:
        meta = self._get_meta(source)
        if not meta:
            return {"ok": False, "message": f"Unknown source '{source}'"}

        pk_fields: List[str] = meta.get("primary_key", [])
        if not pk_fields:
            return {"ok": False, "message": f"No primary key defined for '{source}'"}

        missing_keys = [field for field in pk_fields if key_fields.get(field) in (None, "")]
        if missing_keys:
            return {
                "ok": False,
                "message": f"Missing primary key fields for '{source}'",
                "missing": missing_keys,
            }

        where_clause = " AND ".join([f"{field} = ?" for field in pk_fields])
        params = [key_fields[field] for field in pk_fields]

        with self._connect() as conn:
            cursor = conn.execute(
                f"DELETE FROM {source} WHERE {where_clause}",
                params,
            )
            if cursor.rowcount == 0:
                return {
                    "ok": False,
                    "message": f"No matching row found in '{source}' for provided key.",
                }

        dataset = self.get_rows(source)
        return {
            "ok": True,
            "message": f"Deleted row from '{source}'",
            "dataset": dataset,
        }
