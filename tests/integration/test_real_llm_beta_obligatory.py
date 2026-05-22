import os

import pytest

from app.agents.service import QueryWorkflowService
from app.schemas.query import QueryRequest
from scripts.beta_validation_support import (
    OBLIGATORY_BETA_CASES,
    BetaCase,
    evaluate_beta_case,
)
from scripts.run_beta_validation import _build_workflow_service


pytestmark = pytest.mark.real_llm


@pytest.fixture(scope="session")
def beta_workflow_service() -> QueryWorkflowService:
    if os.getenv("RUN_REAL_LLM_TESTS") != "1":
        pytest.skip("RUN_REAL_LLM_TESTS=1 no esta configurado.")
    try:
        return _build_workflow_service()
    except RuntimeError as exc:
        pytest.skip(str(exc))


@pytest.mark.parametrize(
    "beta_case",
    OBLIGATORY_BETA_CASES,
    ids=[case.case_id for case in OBLIGATORY_BETA_CASES],
)
def test_real_llm_obligatory_beta_case_matches_expected_business_result(
    beta_workflow_service: QueryWorkflowService,
    beta_case: BetaCase,
) -> None:
    responses = []
    conversation_id = f"real-beta-{beta_case.case_id.lower()}"
    for turn in beta_case.turns:
        responses.append(
            beta_workflow_service.run(
                QueryRequest(
                    question=turn.question,
                    conversation_id=conversation_id,
                )
            )
        )

    verdict = evaluate_beta_case(beta_case, responses)

    assert verdict.status == "PASS", "\n".join(verdict.issues)
