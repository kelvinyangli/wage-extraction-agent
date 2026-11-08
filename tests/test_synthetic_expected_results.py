"""End-to-end conformance checks for the versioned synthetic gold fixture."""

import asyncio
import json
from decimal import Decimal
from pathlib import Path

from wage_extraction_agent.adapters import FixtureRepository, MockLlmAdapter
from wage_extraction_agent.models import (
    ComponentVersions,
    DocumentEvidence,
    DocumentState,
    ProcessingMetadata,
)
from wage_extraction_agent.models.enums import (
    AdapterMode,
    DocumentType,
    ProcessingStatus,
)
from wage_extraction_agent.workflow.graph import build_graph


PROJECT_ROOT = Path(__file__).parents[1]
FIXTURE_ROOT = PROJECT_ROOT / "fixtures" / "mock_services"
EXPECTED_PATH = PROJECT_ROOT / "sample-payslips" / "synthetic" / "expected-results.json"
CASES = {
    case["file"]: case
    for case in json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))["cases"]
}


def run_case(name: str, tmp_path: Path) -> dict:
    case = CASES[name]
    document_type = (
        DocumentType.PAY_SUMMARY
        if case["expected"].get("document_type") == "pay_summary"
        else DocumentType.PAYSLIP
    )
    document = DocumentState(
        document_id=Path(name).stem,
        source_document_ref=name,
        page_count=case["pages"],
        document_type=document_type,
        document_evidence=DocumentEvidence(),
        status=ProcessingStatus.PARTIAL,
    )
    state = {
        "request_id": f"synthetic-eval-{Path(name).stem}",
        "claim_number": "CLAIM-SYNTHETIC-EVAL",
        "documents": [document],
        "status": ProcessingStatus.PARTIAL,
        "processing_metadata": ProcessingMetadata(),
        "adapter_mode": AdapterMode.MOCK,
        "max_concurrency": 2,
        "versions": ComponentVersions(
            model="mock-model-v1",
            prompt="prompt-bundle-v2",
            schema="schema-v2",
            mapping="mapping-v1",
            adapter="mock-adapter-v1",
            mock_fixture="mock-services-v1",
        ),
        "issues": [],
    }
    graph = build_graph(
        llm_adapter=MockLlmAdapter(FixtureRepository(FIXTURE_ROOT, "v1")),
        output_dir=tmp_path,
    )
    return asyncio.run(graph.ainvoke(state))["response_json"]["documents"][0]


def amounts(items: list[dict], *, exclude_tax: bool = False) -> list[Decimal]:
    return [
        Decimal(item["amount"])
        for item in items
        if item["amount"] is not None
        and (not exclude_tax or item["group_label"] != "PAYG withholding")
    ]


def test_two_employers_remain_separate_and_gross_checks_match(tmp_path):
    document = run_case("01-two-employers.pdf", tmp_path)
    expected = CASES["01-two-employers.pdf"]["expected"]

    assert len(document["payslips"]) == expected["payslips"]
    assert len({payslip["employer"]["name"] for payslip in document["payslips"]}) == expected["employers"]
    assert [amounts(payslip["line_items"], exclude_tax=True) for payslip in document["payslips"]] == [
        [Decimal(str(value)) for value in row] for row in expected["earnings_amounts"]
    ]
    assert [payslip["reconciliation_checks"][0]["status"] for payslip in document["payslips"]] == expected["gross_checks"]


def test_multipage_payslip_is_one_record_with_expected_items(tmp_path):
    document = run_case("02-multipage-payslip.pdf", tmp_path)
    expected = CASES["02-multipage-payslip.pdf"]["expected"]
    payslip = document["payslips"][0]

    assert len(document["payslips"]) == expected["payslips"]
    assert payslip["source_pages"] == expected["source_pages"]
    assert len(payslip["line_items"]) == expected["item_count"]
    assert [check["status"] for check in payslip["reconciliation_checks"]] == [
        expected["gross_check"], expected["net_check"]
    ]


def test_pay_summary_preserves_all_rows_without_inventing_totals(tmp_path):
    document = run_case("03-pay-summary.pdf", tmp_path)
    expected = CASES["03-pay-summary.pdf"]["expected"]
    payslip = document["payslips"][0]

    assert document["document_type"] == expected["document_type"]
    assert len(payslip["line_items"]) == expected["payment_rows"]
    assert amounts(payslip["line_items"]) == [Decimal(str(value)) for value in expected["amounts"]]
    assert [item["group_label"] for item in payslip["line_items"]] == expected["groups"]
    assert payslip["totals"] == []
    assert payslip["reconciliation_checks"] == []


def test_duplicates_and_conflicting_totals_are_preserved(tmp_path):
    document = run_case("04-duplicates-conflicts.pdf", tmp_path)
    expected = CASES["04-duplicates-conflicts.pdf"]["expected"]
    payslip = document["payslips"][0]

    duplicate_rows = [item for item in payslip["line_items"] if item["original_label"] == "Meal Allowance"]
    assert len(duplicate_rows) == expected["duplicate_rows_preserved"]
    assert [Decimal(total["amount"]) for total in payslip["totals"]] == [Decimal(str(value)) for value in expected["conflicting_gross_values"]]
    assert {check["status"] for check in payslip["reconciliation_checks"]} == {expected["reconciliation"]}


def test_partial_unreadable_and_unresolved_content_remains_visible(tmp_path):
    document = run_case("05-partial-and-unresolved.pdf", tmp_path)
    expected = CASES["05-partial-and-unresolved.pdf"]["expected"]
    page1, page3 = sorted(document["payslips"], key=lambda payslip: payslip["source_pages"])

    assert len(document["payslips"]) == expected["identified_payslips"]
    assert len(document["unresolved_sections"]) == expected["unresolved_sections"]
    assert page1["status"] == expected["page1_status"]
    assert page1["line_items"][1]["amount"] is expected["unreadable_allowance_amount"]
    assert page1["reconciliation_checks"][0]["status"] == expected["page1_gross_check"]
    assert page3["status"] == expected["page3_status"]


def test_total_mismatch_uses_context_selected_records_for_each_total(tmp_path):
    document = run_case("06-total-mismatch.pdf", tmp_path)
    expected = CASES["06-total-mismatch.pdf"]["expected"]
    gross, net = document["payslips"][0]["reconciliation_checks"]

    assert Decimal(gross["calculated_amount"]) == Decimal(str(expected["calculated_gross"]))
    assert Decimal(gross["printed_amount"]) == Decimal(str(expected["printed_gross"]))
    assert Decimal(gross["difference"]) == Decimal(str(expected["difference_calculated_minus_printed"]))
    assert gross["status"] == expected["gross_check"]
    assert gross["rounding_assessment"] == "not_applicable"

    assert net["status"] == expected["net_check"]
    assert Decimal(net["calculated_amount"]) == Decimal("731.00")
    assert net["source_record_ids"] == ["06-gross", "06-tax"]
