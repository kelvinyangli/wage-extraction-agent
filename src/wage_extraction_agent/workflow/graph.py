"""Build the approved twelve-node LangGraph."""

from __future__ import annotations

from pathlib import Path

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from wage_extraction_agent.adapters import LlmAdapter
from wage_extraction_agent.models.state import RequestState
from wage_extraction_agent.workflow.contracts import WorkflowState
from wage_extraction_agent.workflow.nodes import WorkflowNodes


APPROVED_NODE_NAMES = (
    "segment_documents",
    "record_unresolved_section",
    "extract_and_assign_group_labels",
    "schema_validation_pydantic",
    "schema_repair_once",
    "interpret_total_relationships",
    "reconcile_totals",
    "llm_as_a_judge",
    "retry_affected_extraction",
    "retry_reconciliation_item_selection",
    "assemble_response_json",
    "write_json",
)

APPROVED_DESTINATIONS = {
    "segment_documents": (
        "extract_and_assign_group_labels",
        "record_unresolved_section",
        "assemble_response_json",
    ),
    "record_unresolved_section": ("assemble_response_json",),
    "extract_and_assign_group_labels": ("schema_validation_pydantic",),
    "schema_validation_pydantic": (
        "schema_repair_once",
        "interpret_total_relationships",
        "reconcile_totals",
        "assemble_response_json",
    ),
    "schema_repair_once": ("schema_validation_pydantic",),
    "interpret_total_relationships": (
        "reconcile_totals",
        "assemble_response_json",
    ),
    "reconcile_totals": ("llm_as_a_judge", "assemble_response_json"),
    "llm_as_a_judge": (
        "retry_affected_extraction",
        "retry_reconciliation_item_selection",
        "reconcile_totals",
    ),
    "retry_affected_extraction": ("schema_validation_pydantic",),
    "retry_reconciliation_item_selection": ("schema_validation_pydantic",),
    "assemble_response_json": ("write_json", END),
    "write_json": (END,),
}


def build_graph(*, llm_adapter: LlmAdapter, output_dir: Path):
    """Compile the implementation-intent DAG without persistent checkpoints."""

    nodes = WorkflowNodes(llm_adapter=llm_adapter, output_dir=output_dir)
    builder = StateGraph(WorkflowState, input_schema=RequestState)
    for name in APPROVED_NODE_NAMES:
        builder.add_node(
            name,
            getattr(nodes, name),
            destinations=APPROVED_DESTINATIONS[name],
        )

    def fan_out_documents(state: RequestState):
        if not state["documents"]:
            return "assemble_response_json"
        return [
            Send(
                "segment_documents",
                {
                    "request_id": state["request_id"],
                    "document": document,
                },
            )
            for document in state["documents"]
        ]

    builder.add_conditional_edges(
        START,
        fan_out_documents,
        ["segment_documents", "assemble_response_json"],
    )
    return builder.compile()
