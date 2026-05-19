import httpx

from app.production.schemas import ProductionOrder, ProductionOrdersResponse, ProductionStatus


class ProductionAPIError(RuntimeError):
    pass


class ProductionAPIClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
        )

    def get_order(self, order_id: int) -> ProductionOrder | None:
        try:
            response = self._client.get(f"/production/orders/{order_id}")
        except httpx.HTTPError as exc:
            raise ProductionAPIError(str(exc)) from exc

        if response.status_code == 404:
            return None
        self._raise_for_unexpected_status(response)
        return ProductionOrder.model_validate(response.json())

    def list_orders(self, status: ProductionStatus | None = None) -> list[ProductionOrder]:
        params = {"status": status} if status else None
        try:
            response = self._client.get("/production/orders", params=params)
        except httpx.HTTPError as exc:
            raise ProductionAPIError(str(exc)) from exc

        self._raise_for_unexpected_status(response)
        return ProductionOrdersResponse.model_validate(response.json()).orders

    @staticmethod
    def _raise_for_unexpected_status(response: httpx.Response) -> None:
        if response.status_code >= 400:
            raise ProductionAPIError(
                f"Production API returned status {response.status_code}: {response.text}"
            )
