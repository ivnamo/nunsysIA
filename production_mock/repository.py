import json
from pathlib import Path

from production_mock.schemas import ProductionOrder, ProductionStatus


DEFAULT_PRODUCTION_SEED_PATH = Path("data/production_seed.json")


class ProductionRepository:
    def __init__(self, orders: list[ProductionOrder]) -> None:
        self._orders = sorted(orders, key=lambda order: order.order_id)

    @classmethod
    def from_json(cls, seed_path: Path = DEFAULT_PRODUCTION_SEED_PATH) -> "ProductionRepository":
        raw_orders = json.loads(seed_path.read_text(encoding="utf-8"))
        return cls([ProductionOrder.model_validate(order) for order in raw_orders])

    def list_orders(self, status: ProductionStatus | None = None) -> list[ProductionOrder]:
        if status is None:
            return list(self._orders)
        return [order for order in self._orders if order.production_status == status]

    def get_order(self, order_id: int) -> ProductionOrder | None:
        return next((order for order in self._orders if order.order_id == order_id), None)
