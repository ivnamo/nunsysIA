from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.final_response import FinalResponseBuilder
from app.agents.planner import PlannerAgent
from app.agents.reasoner import ReasonerExecutorAgent
from app.agents.state import AgentState
from app.core.llm import ChatModel
from app.agents.validator import ValidatorNode
from app.schemas.query import QueryResponse
from app.tools.erp_tool import ERPTool
from app.tools.production_tool import ProductionAPITool
from app.tools.rag_tool import DocumentRAGTool


def build_agent_graph(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
    rag_tool: DocumentRAGTool | None = None,
    chat_model: ChatModel | None = None,
    llm_timeout_seconds: float = 8.0,
):
    planner = PlannerAgent(
        chat_model=chat_model,
        llm_timeout_seconds=llm_timeout_seconds,
    )
    reasoner = ReasonerExecutorAgent(
        erp_tool=erp_tool,
        production_tool=production_tool,
        rag_tool=rag_tool,
    )
    validator = ValidatorNode()
    final_response = FinalResponseBuilder(
        chat_model=chat_model,
        llm_timeout_seconds=llm_timeout_seconds,
    )

    workflow = StateGraph(AgentState)
    workflow.add_node("planner", planner)
    workflow.add_node("reasoner", reasoner)
    workflow.add_node("validator", validator)
    workflow.add_node("final_response", final_response)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "reasoner")
    workflow.add_edge("reasoner", "validator")
    workflow.add_conditional_edges(
        "validator",
        _route_after_validation,
        {
            "finish": "final_response",
            "fail": "final_response",
            "replan": "planner",
        },
    )
    workflow.add_edge("final_response", END)
    return workflow.compile()


def run_agent_graph(
    erp_tool: ERPTool,
    production_tool: ProductionAPITool,
    question: str,
    conversation_id: str | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
    rag_tool: DocumentRAGTool | None = None,
    chat_model: ChatModel | None = None,
    llm_timeout_seconds: float = 8.0,
) -> QueryResponse:
    graph = build_agent_graph(
        erp_tool=erp_tool,
        production_tool=production_tool,
        rag_tool=rag_tool,
        chat_model=chat_model,
        llm_timeout_seconds=llm_timeout_seconds,
    )
    result = graph.invoke(
        {
            "question": question,
            "conversation_id": conversation_id,
            "conversation_history": conversation_history or [],
            "attempts": 0,
            "tool_results": [],
            "sources": [],
            "reasoning": [],
            "tool_calls": [],
            "fallbacks": [],
            "data": {},
            "replan_history": [],
        }
    )
    return QueryResponse.model_validate(result["response"])


def _route_after_validation(state: AgentState) -> str:
    return state["validation_decision"]
