from fastapi import FastAPI, HTTPException, Query

from production_mock.repository import ProductionRepository
from production_mock.schemas import (
    HealthResponse,
    ProductionOrdersResponse,
    ProductionOrder,
    ProductionStatus,
)


def create_app(repository: ProductionRepository | None = None) -> FastAPI:
    production_repository = repository or ProductionRepository.from_json()
    app = FastAPI(
        title="Production Mock API",
        version="0.1.0",
        description="API REST mock de produccion para la POC agentic.",
    )

    @app.get("/health", response_model=HealthResponse)
    def health_check() -> HealthResponse:
        return HealthResponse()

    @app.get("/production/orders", response_model=ProductionOrdersResponse)
    def list_orders(
        status: ProductionStatus | None = Query(default=None),
    ) -> ProductionOrdersResponse:
        return ProductionOrdersResponse(
            orders=production_repository.list_orders(status=status),
        )

    @app.get("/production/orders/{order_id}", response_model=ProductionOrder)
    def get_order(order_id: int) -> ProductionOrder:
        order = production_repository.get_order(order_id)
        if order is None:
            raise HTTPException(status_code=404, detail="Production order not found")
        return order

    return app


app = create_app()
