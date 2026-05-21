from time import perf_counter

from pydantic import BaseModel, Field

from app.core.tracing import ToolCallTrace, ToolResult
from app.production.client import ProductionAPIClient, ProductionAPIError
from app.production.schemas import ProductionStatus


class ProductionOrderInput(BaseModel):
    order_id: int = Field(gt=0)


class ProductionOrdersInput(BaseModel):
    status: ProductionStatus | None = None


class ProductionOrdersByIdsInput(BaseModel):
    order_ids: list[int] = Field(min_length=1)
    status: ProductionStatus | None = None


class ProductionAPITool:
    name = "ProductionAPITool"

    def __init__(self, client: ProductionAPIClient) -> None:
        self._client = client

    def get_order_status(self, tool_input: ProductionOrderInput) -> ToolResult:
        started_at = perf_counter()
        try:
            order = self._client.get_order(tool_input.order_id)
        except ProductionAPIError as exc:
            return self._error_result(tool_input.model_dump(), str(exc), started_at)

        data = order.model_dump(mode="json") if order else None
        output_summary = (
            f"Estado de produccion {order.production_status}"
            if order
            else "Pedido no encontrado en produccion"
        )
        return ToolResult(
            data=data,
            tool_call=ToolCallTrace(
                tool=self.name,
                args=tool_input.model_dump(),
                status="success",
                output_summary=output_summary,
                duration_ms=self._duration_ms(started_at),
                source="Produccion",
            ),
        )

    def list_orders(self, tool_input: ProductionOrdersInput) -> ToolResult:
        started_at = perf_counter()
        try:
            orders = self._client.list_orders(status=tool_input.status)
        except ProductionAPIError as exc:
            return self._error_result(tool_input.model_dump(), str(exc), started_at)

        data = [order.model_dump(mode="json") for order in orders]
        status_suffix = f" con estado {tool_input.status}" if tool_input.status else ""
        return ToolResult(
            data=data,
            tool_call=ToolCallTrace(
                tool=self.name,
                args=tool_input.model_dump(),
                status="success",
                output_summary=f"{len(data)} pedidos de produccion encontrados{status_suffix}",
                duration_ms=self._duration_ms(started_at),
                source="Produccion",
            ),
        )

    def get_status_for_order_ids(
        self,
        tool_input: ProductionOrdersByIdsInput,
    ) -> ToolResult:
        started_at = perf_counter()
        orders = []
        try:
            for order_id in tool_input.order_ids:
                order = self._client.get_order(order_id)
                if order is None:
                    continue
                if tool_input.status and order.production_status != tool_input.status:
                    continue
                orders.append(order)
        except ProductionAPIError as exc:
            return self._error_result(
                tool_input.model_dump(),
                str(exc),
                started_at,
                action="get_status_for_order_ids",
            )

        data = [order.model_dump(mode="json") for order in orders]
        status_suffix = f" con estado {tool_input.status}" if tool_input.status else ""
        return ToolResult(
            data=data,
            tool_call=ToolCallTrace(
                tool=self.name,
                action="get_status_for_order_ids",
                args=tool_input.model_dump(),
                status="success",
                output_summary=(
                    f"{len(data)} pedidos de produccion encontrados por ids"
                    f"{status_suffix}"
                ),
                duration_ms=self._duration_ms(started_at),
                source="Produccion",
            ),
        )

    def _error_result(
        self,
        args: dict[str, object],
        error: str,
        started_at: float,
        action: str | None = None,
    ) -> ToolResult:
        return ToolResult(
            data=None,
            tool_call=ToolCallTrace(
                tool=self.name,
                action=action,
                args=args,
                status="error",
                output_summary="Error al consultar API de produccion",
                error=error,
                duration_ms=self._duration_ms(started_at),
                source="Produccion",
            ),
        )

    @staticmethod
    def _duration_ms(started_at: float) -> int:
        return round((perf_counter() - started_at) * 1000)
