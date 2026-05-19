from fastapi.testclient import TestClient

from production_mock.main import app


client = TestClient(app)


def test_production_mock_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_production_order_returns_blocked_order() -> None:
    response = client.get("/production/orders/10252")

    assert response.status_code == 200
    assert response.json() == {
        "order_id": 10252,
        "production_status": "blocked",
        "blocked_reason": "Falta de material",
        "delay_reason": None,
        "estimated_finish_date": "2026-05-30",
    }


def test_list_production_orders_can_filter_blocked_orders() -> None:
    response = client.get("/production/orders", params={"status": "blocked"})

    assert response.status_code == 200
    assert [order["order_id"] for order in response.json()["orders"]] == [10252, 10312]


def test_list_production_orders_can_filter_delayed_orders() -> None:
    response = client.get("/production/orders", params={"status": "delayed"})

    assert response.status_code == 200
    assert response.json()["orders"] == [
        {
            "order_id": 10301,
            "production_status": "delayed",
            "blocked_reason": None,
            "delay_reason": "Averia en linea de produccion",
            "estimated_finish_date": "2026-06-03",
        }
    ]


def test_get_production_order_returns_404_for_unknown_order() -> None:
    response = client.get("/production/orders/99999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Production order not found"}


def test_list_production_orders_rejects_unknown_status() -> None:
    response = client.get("/production/orders", params={"status": "unknown"})

    assert response.status_code == 422
