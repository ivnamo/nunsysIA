from time import perf_counter

from pydantic import BaseModel, Field

from app.core.tracing import ToolCallTrace, ToolResult
from app.erp.repositories import NorthwindRepository


class PendingOrdersByCustomerInput(BaseModel):
    customer_id: str = Field(min_length=1)


class CustomerByOrderInput(BaseModel):
    order_id: int = Field(gt=0)


class OrdersByMonthInput(BaseModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)


class OrderAmountInput(BaseModel):
    order_id: int = Field(gt=0)


class ERPTool:
    name = "ERPTool"

    def __init__(self, repository: NorthwindRepository) -> None:
        self._repository = repository

    def get_pending_orders_by_customer(
        self,
        tool_input: PendingOrdersByCustomerInput,
    ) -> ToolResult:
        started_at = perf_counter()
        orders = self._repository.get_pending_orders_by_customer(tool_input.customer_id)
        data = [order.model_dump(mode="json") for order in orders]
        return ToolResult(
            data=data,
            tool_call=ToolCallTrace(
                tool=self.name,
                args=tool_input.model_dump(),
                status="success",
                output_summary=f"{len(data)} pedidos pendientes encontrados",
                duration_ms=self._duration_ms(started_at),
                source="ERP",
            ),
        )

    def get_customer_by_order(self, tool_input: CustomerByOrderInput) -> ToolResult:
        started_at = perf_counter()
        customer = self._repository.get_customer_by_order(tool_input.order_id)
        data = customer.model_dump(mode="json") if customer else None
        output_summary = (
            f"Cliente {customer.customer_id} encontrado"
            if customer
            else "No se encontro cliente para el pedido"
        )
        return ToolResult(
            data=data,
            tool_call=ToolCallTrace(
                tool=self.name,
                args=tool_input.model_dump(),
                status="success",
                output_summary=output_summary,
                duration_ms=self._duration_ms(started_at),
                source="ERP",
            ),
        )

    def get_orders_by_month(self, tool_input: OrdersByMonthInput) -> ToolResult:
        started_at = perf_counter()
        orders = self._repository.get_orders_by_month(tool_input.year, tool_input.month)
        data = [order.model_dump(mode="json") for order in orders]
        return ToolResult(
            data=data,
            tool_call=ToolCallTrace(
                tool=self.name,
                args=tool_input.model_dump(),
                status="success",
                output_summary=f"{len(data)} pedidos encontrados para el mes",
                duration_ms=self._duration_ms(started_at),
                source="ERP",
            ),
        )

    def calculate_order_amount(self, tool_input: OrderAmountInput) -> ToolResult:
        started_at = perf_counter()
        amount = self._repository.calculate_order_amount(tool_input.order_id)
        data = {"order_id": tool_input.order_id, "amount": str(amount)} if amount else None
        output_summary = "Importe calculado" if amount else "Pedido no encontrado"
        return ToolResult(
            data=data,
            tool_call=ToolCallTrace(
                tool=self.name,
                action="calculate_order_amount",
                args=tool_input.model_dump(),
                status="success",
                output_summary=output_summary,
                duration_ms=self._duration_ms(started_at),
                source="ERP",
            ),
        )

    @staticmethod
    def _duration_ms(started_at: float) -> int:
        return round((perf_counter() - started_at) * 1000)
