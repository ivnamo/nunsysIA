from app.erp.database import create_sqlite_connection, load_seed_sql
from app.erp.repositories import NorthwindRepository
from app.tools.erp_query_tool import ERPQueryTool
from app.tools.erp_tool import ERPTool


def create_erp_tools() -> tuple[ERPTool, ERPQueryTool]:
    connection = create_sqlite_connection(check_same_thread=False)
    load_seed_sql(connection)
    repository = NorthwindRepository(connection)
    return ERPTool(repository), ERPQueryTool(repository)

