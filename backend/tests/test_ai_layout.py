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
    """Regression test: ensure fetch_dataset tool trims sales rows via SQLite."""

    responses = [
        make_response(
            tool_calls=[
                make_tool_call("fetch_dataset", {"source": "sales", "days": 7})
            ]
        ),
        make_response(
            tool_calls=[
                make_tool_call(
                    "build_chart_layout",
                    {
                        "source": "sales",
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
    assert "sales" in payload["datasets"]

    sales_rows = payload["datasets"]["sales"]
    assert len(sales_rows) == 7
    assert all("avg_order_value" in row for row in sales_rows)

    dates = [row["date"] for row in sales_rows]
    assert dates == sorted(dates)


def test_add_record_reports_missing_fields(client):
    """New insert tool should remind users about required fields."""

    response = backend_main.add_record("products", {"sku": "NEW-100"})
    assert response["type"] == "Text"
    assert "Missing fields" in response["content"]
    assert "name" in response["content"]


def test_mutation_flow_insert_update_delete(client):
    """Full mutation cycle against the runtime database."""

    insert_payload = {
        "sku": "NEW-200",
        "name": "Quantum Speaker",
        "category": "Audio",
        "unit_price": 149.0,
        "inventory": 45,
        "status": "active",
    }
    insert_result = backend_main.add_record("products", insert_payload)
    assert insert_result["meta"]["action"] == "insert"
    products = insert_result["datasets"]["products"]
    assert any(row["sku"] == "NEW-200" for row in products)

    update_payload = {
        "sku": "NEW-200",
        "status": "backorder",
        "inventory": 30,
    }
    update_result = backend_main.update_record("products", update_payload)
    assert update_result["meta"]["action"] == "update"
    updated_row = next(
        row for row in update_result["datasets"]["products"] if row["sku"] == "NEW-200"
    )
    assert updated_row["status"] == "backorder"
    assert updated_row["inventory"] == 30

    delete_result = backend_main.remove_record("products", {"sku": "NEW-200"})
    assert delete_result["meta"]["action"] == "delete"
    product_skus = [row["sku"] for row in delete_result["datasets"]["products"]]
    assert "NEW-200" not in product_skus


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
    """Non-SELECT statements should be rejected."""

    result = backend_main.fetch_dataset(query="DELETE FROM products")
    assert result["type"] == "Text"
    assert "Only SELECT statements" in result["content"]
