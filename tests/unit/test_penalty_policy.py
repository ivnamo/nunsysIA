from app.agents.penalty_policy import (
    build_order_penalties_answer,
    evaluate_order_penalties,
)


def test_penalty_policy_excludes_blocked_and_production_caused_delays() -> None:
    result = evaluate_order_penalties(
        orders=[
            {"order_id": 10252, "customer_id": "ALFKI", "erp_status": "pending"},
            {
                "order_id": 10301,
                "customer_name": "Ana Trujillo Emparedados",
                "erp_status": "pending",
            },
        ],
        production_by_order={
            10252: {
                "order_id": 10252,
                "production_status": "blocked",
                "blocked_reason": "Falta de material",
            },
            10301: {
                "order_id": 10301,
                "production_status": "delayed",
                "delay_reason": "Averia en linea de produccion",
            },
        },
        rag_evidence=_penalty_rag_evidence(),
    )

    answer = result.answer()

    assert result.has_document_evidence is True
    assert "10252 (ALFKI): bloqueado (Falta de material)" in answer
    assert "10301 (Ana Trujillo Emparedados): retrasado" in answer
    assert answer.count("exclusion documental") == 2


def test_penalty_policy_keeps_finished_order_without_delay_as_not_applicable() -> None:
    answer = build_order_penalties_answer(
        {
            "erp_orders": [
                {
                    "order_id": 10255,
                    "customer_id": "ALFKI",
                    "required_date": "2026-05-20",
                    "shipped_date": "2026-05-14",
                }
            ],
            "production_by_order": {
                10255: {
                    "order_id": 10255,
                    "production_status": "finished",
                }
            },
            "rag": _penalty_rag_evidence(),
        }
    )

    assert "10255 (ALFKI): finalizado" in answer
    assert "consta enviado antes del plazo requerido" in answer


def test_penalty_policy_requires_document_evidence_before_assessing() -> None:
    answer = build_order_penalties_answer(
        {
            "erp_orders": [
                {"order_id": 10252, "customer_id": "ALFKI", "erp_status": "pending"}
            ],
            "production_by_order": {
                10252: {
                    "order_id": 10252,
                    "production_status": "blocked",
                    "blocked_reason": "Falta de material",
                }
            },
            "rag": {
                "status": "insufficient_context",
                "chunks": [],
            },
        }
    )

    assert answer == (
        "No hay contexto documental suficiente para estimar penalizaciones sin inventar."
    )
    assert "10252" not in answer


def _penalty_rag_evidence() -> dict:
    return {
        "status": "completed",
        "chunks": [
            {
                "text": (
                    "Penalizaciones por retrasos. No aplicacion por bloqueo "
                    "de produccion, falta de material, falta de capacidad o "
                    "averia en linea."
                ),
                "metadata": {
                    "filename": "anexo_penalizaciones_sla.pdf",
                    "page": 1,
                    "chunk_id": "doc_1_p1_c1",
                },
                "score": 0.9,
            }
        ],
    }
