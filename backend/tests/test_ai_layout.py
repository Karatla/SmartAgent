import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend import main as backend_main
from backend.database import RuntimeDatabase
from backend.history_store import HistoryStore


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Provide a TestClient backed by an isolated runtime database."""

    temp_db_path = tmp_path / "runtime.db"
    history_path = tmp_path / "history.jsonl"

    backend_main.database = RuntimeDatabase(temp_db_path)
    backend_main.history = HistoryStore(str(history_path))

    with TestClient(backend_main.app) as test_client:
        yield test_client


def make_tool_call(name, arguments):
    return SimpleNamespace(function=SimpleNamespace(name=name, arguments=arguments))


def make_response(*, tool_calls=None, content=None):
    return SimpleNamespace(
        message=SimpleNamespace(tool_calls=tool_calls or [], content=content)
    )


def test_ai_layout_orders_table_uses_runtime_database(client, monkeypatch):
    """Regression test: ensure table layouts pull rows from the SQLite store."""

    responses = [
        make_response(
            tool_calls=[
                make_tool_call(
                    "build_table_layout",
                    {"source": "orders", "title": "Orders Overview"},
                )
            ]
        ),
        make_response(
            content=json.dumps(
                {
                    "layout": {
                        "type": "Page",
                        "title": "Orders Overview",
                        "children": [{"type": "Table", "source": "orders"}],
                    }
                }
            )
        ),
    ]

    def fake_chat(model, messages, tools, think=False):
        assert responses, "chat invoked more times than expected"
        return responses.pop(0)

    monkeypatch.setattr(backend_main, "chat", fake_chat)

    response = client.post(
        "/ai_layout", json={"message": "Show recent orders", "session_id": "orders"}
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["layout"]["title"] == "Orders Overview"
    assert "orders" in payload["datasets"]

    orders = payload["datasets"]["orders"]
    assert orders  # seeded rows exist
    assert len(orders) == len(backend_main.database.get_rows("orders"))
    assert orders[0]["id"].startswith("SO-")
    assert "total" in orders[0]


def test_ai_layout_sales_chart_respects_day_filters(client, monkeypatch):
    """Regression test: ensure query-based fetches can limit sales data."""

    responses = [
        make_response(
            tool_calls=[
                make_tool_call(
                    "fetch_dataset",
                    {
                        "query": "SELECT * FROM sales ORDER BY date DESC LIMIT 7",
                        "alias": "sales_week",
                    },
                )
            ]
        ),
        make_response(
            tool_calls=[
                make_tool_call(
                    "build_chart_layout",
                    {
                        "source": "sales_week",
                        "chart_type": "line",
                        "metric": "total",
                        "title": "Weekly Sales",
                    },
                )
            ]
        ),
        make_response(content=""),
    ]

    def fake_chat(model, messages, tools, think=False):
        assert responses, "chat invoked more times than expected"
        return responses.pop(0)

    monkeypatch.setattr(backend_main, "chat", fake_chat)

    response = client.post(
        "/ai_layout",
        json={"message": "Plot the last week of sales", "session_id": "sales"},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["layout"]["title"] == "Weekly Sales"
    assert "sales_week" in payload["datasets"]

    sales_rows = payload["datasets"]["sales_week"]
    assert len(sales_rows) == 7
    assert all("avg_order_value" in row for row in sales_rows)

    dates = [row["date"] for row in sales_rows]
    assert dates == sorted(dates)


def test_fetch_dataset_query_path(client):
    """Allow LLMs to run arbitrary SELECT statements with aliases."""

    result = backend_main.fetch_dataset(
        query="SELECT sku, name, status FROM products WHERE status = :status",
        params={"status": "active"},
        alias="active_products",
    )

    assert "datasets" in result
    rows = result["datasets"]["active_products"]
    assert rows
    assert all(row["status"] == "active" for row in rows)
    meta = result["meta"]
    assert meta["query"].startswith("SELECT")
    assert meta["columns"] == ["sku", "name", "status"]


def test_fetch_dataset_query_validation(client):
    """Disallow statements outside SELECT/INSERT/UPDATE/DELETE."""

    result = backend_main.fetch_dataset(query="DROP TABLE products")
    assert result["type"] == "Text"
    assert "Only SELECT/INSERT/UPDATE/DELETE" in result["content"]


def test_fetch_dataset_handles_dml_queries(client):
    """Ensure INSERT/UPDATE/DELETE can be executed via fetch_dataset."""

    insert = backend_main.fetch_dataset(
        query="""
        INSERT INTO products (sku, name, category, unit_price, inventory, status)
        VALUES (:sku, :name, :category, :unit_price, :inventory, :status)
        """,
        params={
            "sku": "NEW-300",
            "name": "Photon Lamp",
            "category": "Lighting",
            "unit_price": 59.0,
            "inventory": 25,
            "status": "active",
        },
    )
    assert insert["type"] == "Text"
    assert "INSERT" in insert["content"]

    update = backend_main.fetch_dataset(
        query="UPDATE products SET inventory = :inv WHERE sku = :sku",
        params={"inv": 15, "sku": "NEW-300"},
    )
    assert update["type"] == "Text"
    assert "UPDATE" in update["content"]

    result = backend_main.fetch_dataset(
        query="SELECT sku, inventory FROM products WHERE sku = :sku",
        params={"sku": "NEW-300"},
        alias="single_product",
    )
    rows = result["datasets"]["single_product"]
    assert rows and rows[0]["inventory"] == 15

    delete = backend_main.fetch_dataset(
        query="DELETE FROM products WHERE sku = :sku", params={"sku": "NEW-300"}
    )
    assert delete["type"] == "Text"
    assert "DELETE" in delete["content"]

    confirm = backend_main.fetch_dataset(
        query="SELECT sku FROM products WHERE sku = :sku",
        params={"sku": "NEW-300"},
    )
    assert not confirm["datasets"]["query_results"]
