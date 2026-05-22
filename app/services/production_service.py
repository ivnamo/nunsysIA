from app.core.config import Settings
from app.production.client import ProductionAPIClient
from app.tools.production_query_tool import ProductionQueryTool
from app.tools.production_tool import ProductionAPITool


def create_production_tools(
    settings: Settings,
) -> tuple[ProductionAPITool, ProductionQueryTool]:
    client = ProductionAPIClient(
        base_url=settings.production_api_base_url,
        timeout=settings.production_api_timeout_seconds,
    )
    return ProductionAPITool(client), ProductionQueryTool(client)

