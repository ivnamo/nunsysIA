from app.agents.planner_context import (
    build_contextual_rule_based_plan,
    missing_customer_plan,
)
from app.agents.planner_models import ExecutionPlan, PlanStep
from app.agents.planner_utils import extract_customer_id
from app.agents.state import AgentIntent, AgentState


def build_rule_based_plan(
    question: str,
    normalized: str,
    state: AgentState,
) -> ExecutionPlan:
    contextual_plan = build_contextual_rule_based_plan(
        question=question,
        normalized=normalized,
        history=state.get("conversation_history", []),
    )
    if contextual_plan is not None:
        return contextual_plan

    if is_order_penalty_query(normalized):
        return ExecutionPlan(
            intent="mixed",
            steps=[
                PlanStep(
                    step_id=1,
                    tool="ERPTool",
                    action="get_orders_by_month",
                    args={"year": 2026, "month": 5},
                ),
                PlanStep(
                    step_id=2,
                    tool="ProductionAPITool",
                    action="get_status_for_erp_orders",
                ),
                PlanStep(
                    step_id=3,
                    tool="DocumentRAGTool",
                    action="query",
                    args={
                        "query": (
                            "penalizaciones por retrasos no aplicacion bloqueo "
                            "produccion falta material falta capacidad averia linea"
                        ),
                        "top_k": 5,
                    },
                ),
            ],
            expected_sources=["ERP", "Produccion", "Documentos"],
            answer_requirements=[
                "Devolver penalizacion aplicable por pedido usando ERP, produccion y normativa documental.",
            ],
        )

    if _is_document_query(normalized):
        return ExecutionPlan(
            intent="rag",
            steps=[
                PlanStep(
                    step_id=1,
                    tool="DocumentRAGTool",
                    action="query",
                    args={"query": question, "top_k": 5},
                )
            ],
            expected_sources=["Documentos"],
            answer_requirements=["Responder solo con chunks documentales recuperados."],
        )

    if "bloquead" in normalized:
        return ExecutionPlan(
            intent="erp_production",
            steps=[
                PlanStep(
                    step_id=1,
                    tool="ProductionAPITool",
                    action="list_orders",
                    args={"status": "blocked"},
                ),
                PlanStep(
                    step_id=2,
                    tool="ERPTool",
                    action="get_customers_for_production_orders",
                ),
            ],
            expected_sources=["Produccion", "ERP"],
            answer_requirements=["Devolver pedido, cliente y motivo de bloqueo."],
        )

    if "retrasad" in normalized or "demor" in normalized:
        return ExecutionPlan(
            intent="erp_production",
            steps=[
                PlanStep(
                    step_id=1,
                    tool="ProductionAPITool",
                    action="list_orders",
                    args={"status": "delayed"},
                ),
                PlanStep(
                    step_id=2,
                    tool="ERPTool",
                    action="get_customers_for_production_orders",
                ),
            ],
            expected_sources=["Produccion", "ERP"],
            answer_requirements=[
                "Devolver pedidos retrasados, clientes afectados y motivo del retraso."
            ],
        )

    if "mes" in normalized or "resumen" in normalized:
        return ExecutionPlan(
            intent="erp_production",
            steps=[
                PlanStep(
                    step_id=1,
                    tool="ERPTool",
                    action="get_orders_by_month",
                    args={"year": 2026, "month": 5},
                ),
                PlanStep(
                    step_id=2,
                    tool="ProductionAPITool",
                    action="get_status_for_erp_orders",
                ),
            ],
            expected_sources=["ERP", "Produccion"],
            answer_requirements=["Agrupar pedidos por estado de produccion."],
        )

    if "pendient" in normalized:
        customer_id = extract_customer_id(question)
        if customer_id is None:
            return missing_customer_plan()
        steps = [
            PlanStep(
                step_id=1,
                tool="ERPTool",
                action="get_pending_orders_by_customer",
                args={"customer_id": customer_id},
            )
        ]
        expected_sources = ["ERP"]
        if "producci" in normalized or "estado" in normalized:
            steps.append(
                PlanStep(
                    step_id=2,
                    tool="ProductionAPITool",
                    action="get_status_for_erp_orders",
                )
            )
            expected_sources.append("Produccion")
            intent: AgentIntent = "erp_production"
        else:
            intent = "erp"

        return ExecutionPlan(
            intent=intent,
            steps=steps,
            expected_sources=expected_sources,
            answer_requirements=["Devolver pedidos pendientes y datos disponibles."],
        )

    return ExecutionPlan(
        intent="unsupported",
        steps=[],
        expected_sources=[],
        answer_requirements=["Explicar que la pregunta esta fuera del alcance actual."],
    )


def is_order_penalty_query(normalized: str) -> bool:
    if "penaliz" not in normalized:
        return False
    if "pedido" not in normalized and "order" not in normalized:
        return False
    return any(
        marker in normalized
        for marker in (
            "estado",
            "produccion",
            "cada uno",
            "cada pedido",
            "en cada uno",
        )
    )


def _is_document_query(normalized: str) -> bool:
    return any(
        marker in normalized
        for marker in (
            "document",
            "pdf",
            "contrato",
            "plazo",
            "penalizacion",
            "penalizaci",
            "clausula",
            "entrega",
        )
    )
