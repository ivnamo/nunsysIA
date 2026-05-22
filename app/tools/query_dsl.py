from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ERP_ENTITY = "orders"
PRODUCTION_ENTITY = "production_orders"

MAX_QUERY_LIMIT = 50

ERP_FILTER_FIELDS = frozenset(
    {
        "customer_id",
        "order_id",
        "erp_status",
        "year",
        "month",
    }
)
ERP_SELECT_FIELDS = (
    "order_id",
    "customer_id",
    "customer_name",
    "erp_status",
    "order_date",
    "amount",
)
ERP_ORDER_FIELDS = frozenset(ERP_SELECT_FIELDS)
ERP_STATUSES = frozenset({"pending", "shipped", "cancelled"})

PRODUCTION_FILTER_FIELDS = frozenset({"order_id", "production_status"})
PRODUCTION_SELECT_FIELDS = (
    "order_id",
    "production_status",
    "blocked_reason",
    "delay_reason",
    "estimated_finish_date",
)
PRODUCTION_ORDER_FIELDS = frozenset(PRODUCTION_SELECT_FIELDS)
PRODUCTION_STATUSES = frozenset({"in_progress", "blocked", "delayed", "finished"})

QueryOperator = Literal["eq", "in"]
SortDirection = Literal["asc", "desc"]


class QueryDSLValidationError(ValueError):
    pass


class QueryFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    operator: QueryOperator = "eq"
    value: Any


class QueryOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    direction: SortDirection = "asc"


class ERPQuerySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity: Literal["orders"] = ERP_ENTITY
    filters: list[QueryFilter] = Field(default_factory=list)
    select: list[str] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=MAX_QUERY_LIMIT)
    order_by: QueryOrder | None = None

    @model_validator(mode="after")
    def validate_erp_query(self) -> "ERPQuerySpec":
        self.select = _validated_select(self.select, ERP_SELECT_FIELDS)
        _validate_filters(self.filters, ERP_FILTER_FIELDS, _validate_erp_filter)
        _validate_order_by(self.order_by, ERP_ORDER_FIELDS)
        return self


class ProductionQuerySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity: Literal["production_orders"] = PRODUCTION_ENTITY
    filters: list[QueryFilter] = Field(default_factory=list)
    select: list[str] = Field(default_factory=list)
    limit: int = Field(default=20, ge=1, le=MAX_QUERY_LIMIT)
    order_by: QueryOrder | None = None

    @model_validator(mode="after")
    def validate_production_query(self) -> "ProductionQuerySpec":
        self.select = _validated_select(self.select, PRODUCTION_SELECT_FIELDS)
        _validate_filters(
            self.filters,
            PRODUCTION_FILTER_FIELDS,
            _validate_production_filter,
        )
        _validate_order_by(self.order_by, PRODUCTION_ORDER_FIELDS)
        return self


def _validated_select(select: list[str], allowed_fields: tuple[str, ...]) -> list[str]:
    if not select:
        return list(allowed_fields)

    unknown_fields = [field for field in select if field not in allowed_fields]
    if unknown_fields:
        raise QueryDSLValidationError(
            f"select contiene campos no permitidos: {', '.join(unknown_fields)}"
        )

    deduplicated = []
    for field in select:
        if field not in deduplicated:
            deduplicated.append(field)
    return deduplicated


def _validate_filters(
    filters: list[QueryFilter],
    allowed_fields: frozenset[str],
    value_validator: Any,
) -> None:
    for query_filter in filters:
        if query_filter.field not in allowed_fields:
            raise QueryDSLValidationError(
                f"filtro no permitido: {query_filter.field}"
            )
        query_filter.value = _validated_operator_value(
            query_filter.operator,
            query_filter.value,
        )
        query_filter.value = value_validator(query_filter.field, query_filter.value)


def _validated_operator_value(operator: QueryOperator, value: Any) -> Any:
    if operator == "eq":
        if isinstance(value, list):
            raise QueryDSLValidationError("operator eq no acepta listas")
        return value

    if not isinstance(value, list) or not value:
        raise QueryDSLValidationError("operator in requiere una lista no vacia")
    if len(value) > MAX_QUERY_LIMIT:
        raise QueryDSLValidationError("operator in supera el limite maximo")
    return value


def _validate_erp_filter(field: str, value: Any) -> Any:
    if field == "customer_id":
        return _normalize_string_or_list(value, uppercase=True)
    if field in {"order_id", "year", "month"}:
        return _normalize_int_or_list(value)
    if field == "erp_status":
        return _normalize_choice_or_list(value, ERP_STATUSES)
    raise QueryDSLValidationError(f"filtro ERP no soportado: {field}")


def _validate_production_filter(field: str, value: Any) -> Any:
    if field == "order_id":
        return _normalize_int_or_list(value)
    if field == "production_status":
        return _normalize_choice_or_list(value, PRODUCTION_STATUSES)
    raise QueryDSLValidationError(f"filtro produccion no soportado: {field}")


def _normalize_string_or_list(value: Any, uppercase: bool = False) -> Any:
    if isinstance(value, list):
        return [_normalize_string(item, uppercase=uppercase) for item in value]
    return _normalize_string(value, uppercase=uppercase)


def _normalize_string(value: Any, uppercase: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QueryDSLValidationError("se esperaba texto no vacio")
    normalized = value.strip()
    return normalized.upper() if uppercase else normalized


def _normalize_int_or_list(value: Any) -> Any:
    if isinstance(value, list):
        return [_normalize_positive_int(item) for item in value]
    return _normalize_positive_int(value)


def _normalize_positive_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise QueryDSLValidationError("se esperaba entero positivo")
    return value


def _normalize_choice_or_list(value: Any, allowed_values: frozenset[str]) -> Any:
    if isinstance(value, list):
        return [_normalize_choice(item, allowed_values) for item in value]
    return _normalize_choice(value, allowed_values)


def _normalize_choice(value: Any, allowed_values: frozenset[str]) -> str:
    if not isinstance(value, str):
        raise QueryDSLValidationError("se esperaba texto para valor enumerado")
    normalized = value.strip().lower()
    if normalized not in allowed_values:
        raise QueryDSLValidationError(f"valor no permitido: {value}")
    return normalized


def _validate_order_by(
    order_by: QueryOrder | None,
    allowed_fields: frozenset[str],
) -> None:
    if order_by is None:
        return
    if order_by.field not in allowed_fields:
        raise QueryDSLValidationError(
            f"order_by no permitido: {order_by.field}"
        )
