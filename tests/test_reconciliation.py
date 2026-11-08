from wage_extraction_agent.models import (
    PrintedTotal,
    ReconciliationCheckState,
    RelationshipTerm,
    TotalRelationship,
)
from wage_extraction_agent.models.enums import (
    ReconciliationSourceType,
    ReconciliationStatus,
    RoundingAssessment,
    TotalType,
)
from wage_extraction_agent.workflow.rules import reconcile_check


def check_for(terms: list[RelationshipTerm]) -> ReconciliationCheckState:
    return ReconciliationCheckState(
        check_id="check-net",
        payslip_id="pay-1",
        printed_total_id="net",
        relationship=TotalRelationship(terms=terms, explanation="Context-selected sources."),
        printed_amount="731.00",
        currency="AUD",
        status=ReconciliationStatus.UNABLE_TO_CHECK,
        reason="Pending.",
        rounding_assessment=RoundingAssessment.NOT_APPLICABLE,
        source_pages=[1],
    )


def totals() -> list[PrintedTotal]:
    return [
        PrintedTotal(
            total_id="gross",
            total_type=TotalType.GROSS_PAY,
            amount="831.00",
            currency="AUD",
            source_page=1,
        ),
        PrintedTotal(
            total_id="net",
            total_type=TotalType.NET_PAY,
            amount="731.00",
            currency="AUD",
            source_page=1,
        ),
    ]


def test_context_selected_printed_total_can_contribute_to_another_total():
    check = check_for(
        [
            RelationshipTerm(
                source_type=ReconciliationSourceType.PRINTED_TOTAL,
                source_record_id="gross",
                multiplier=1,
                reason="Displayed gross feeds displayed net.",
            ),
            RelationshipTerm(
                source_type=ReconciliationSourceType.PAY_ITEM,
                source_record_id="tax",
                multiplier=1,
                reason="Withholding is already signed.",
            ),
        ]
    )
    from wage_extraction_agent.models import PayItem
    from wage_extraction_agent.models.enums import GroupLabel, MappingMethod, PayItemStatus

    tax = PayItem(
        item_id="tax",
        status=PayItemStatus.COMPLETE,
        original_label="PAYG",
        group_label=GroupLabel.PAYG_WITHHOLDING,
        amount="-100.00",
        currency="AUD",
        source_page=1,
        mapping_method=MappingMethod.RULE,
        mapping_confidence=1.0,
    )

    result = reconcile_check(check, [tax], totals())

    assert result.status is ReconciliationStatus.MATCHED
    assert result.source_record_ids == ["gross", "tax"]


def test_target_total_cannot_reference_itself():
    check = check_for(
        [
            RelationshipTerm(
                source_type=ReconciliationSourceType.PRINTED_TOTAL,
                source_record_id="net",
                multiplier=1,
                reason="Invalid self-reference.",
            )
        ]
    )

    result = reconcile_check(check, [], totals())

    assert result.status is ReconciliationStatus.UNABLE_TO_CHECK
    assert result.calculated_amount is None
