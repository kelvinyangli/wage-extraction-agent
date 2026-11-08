from wage_extraction_agent.models import DocumentEvidence, DocumentState, merge_document_updates
from wage_extraction_agent.models.enums import DocumentType, ProcessingStatus


def make_document(document_id: str, status: ProcessingStatus) -> DocumentState:
    return DocumentState(
        document_id=document_id,
        source_document_ref=f"input/{document_id}.pdf",
        page_count=1,
        document_type=DocumentType.PAYSLIP,
        document_evidence=DocumentEvidence(),
        status=status,
    )


def test_document_reducer_appends_independent_branches_in_order():
    first = make_document("doc-1", ProcessingStatus.SUCCESSFUL)
    second = make_document("doc-2", ProcessingStatus.PARTIAL)

    merged = merge_document_updates([first], [second])

    assert [document.document_id for document in merged] == ["doc-1", "doc-2"]


def test_document_reducer_replaces_an_update_without_duplication():
    original = make_document("doc-1", ProcessingStatus.PARTIAL)
    completed = make_document("doc-1", ProcessingStatus.SUCCESSFUL)

    merged = merge_document_updates([original], [completed])

    assert len(merged) == 1
    assert merged[0].status is ProcessingStatus.SUCCESSFUL


def test_document_reducer_merges_parallel_payslip_updates():
    from wage_extraction_agent.models import BoundaryEvidence, PayslipState
    from wage_extraction_agent.models.enums import BoundaryDecision

    first = make_document("doc-1", ProcessingStatus.PARTIAL).model_copy(
        update={
            "payslips": [
                PayslipState(
                    payslip_id="pay-1",
                    source_pages=[1],
                    boundary_evidence=BoundaryEvidence(
                        decision=BoundaryDecision.NEW_PAYSLIP,
                        reason="First",
                        source_pages=[1],
                    ),
                    status=ProcessingStatus.SUCCESSFUL,
                )
            ]
        }
    )
    second = make_document("doc-1", ProcessingStatus.PARTIAL).model_copy(
        update={
            "payslips": [
                PayslipState(
                    payslip_id="pay-2",
                    source_pages=[2],
                    boundary_evidence=BoundaryEvidence(
                        decision=BoundaryDecision.NEW_PAYSLIP,
                        reason="Second",
                        source_pages=[2],
                    ),
                    status=ProcessingStatus.SUCCESSFUL,
                )
            ]
        }
    )

    merged = merge_document_updates([first], [second])

    assert [item.payslip_id for item in merged[0].payslips] == ["pay-1", "pay-2"]
