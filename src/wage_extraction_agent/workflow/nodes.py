"""The twelve approved LangGraph node implementations."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

from langgraph.graph import END
from langgraph.types import Command, Send
from pydantic import ValidationError

from wage_extraction_agent.adapters import AdapterError, LlmAdapter, PromptStage
from wage_extraction_agent.models.common import (
    DocumentCounts,
    ItemCounts,
    PayslipCounts,
    ProcessingMetadata,
    ReconciliationCounts,
    ValidationErrorRecord,
)
from wage_extraction_agent.models.domain import (
    DocumentResult,
    DocumentState,
    EmployeeDetails,
    EmployerDetails,
    EmploymentDetails,
    ExtractionResponse,
    FlexibleField,
    LeaveBalance,
    PayItem,
    PayPeriodDetails,
    PayslipState,
    PrintedTotal,
    ReconciliationCheckState,
    TotalRelationship,
    UnresolvedSection,
)
from wage_extraction_agent.models.enums import (
    GroupLabel,
    JudgeOutcome,
    MappingMethod,
    PayslipStatus,
    ReconciliationStatus,
    RoundingAssessment,
    TargetedRetryType,
)
from wage_extraction_agent.workflow.contracts import (
    ExtractionRetryResult,
    GroupClassificationResult,
    JudgeResult,
    PayslipWork,
    RepairResult,
    SegmentationResult,
    UnresolvedWork,
    WorkflowState,
)
from wage_extraction_agent.workflow.publication import publish_response
from wage_extraction_agent.workflow.rules import (
    derive_document_status,
    derive_request_status,
    known_group_label,
    payslip_terminal_status,
    reconcile_check,
    review_issue,
)


def _document_key(document: DocumentState) -> str:
    return document.source_document_ref


def _payslip_branch_id(document: DocumentState, payslip: PayslipState) -> str:
    return f"payslip:{_document_key(document)}:{payslip.payslip_id}"


def _unresolved_branch_id(document: DocumentState, section: UnresolvedSection) -> str:
    return f"unresolved:{_document_key(document)}:{section.section_id}"


def _segmentation_fixture_key(document: DocumentState) -> str:
    name = Path(document.source_document_ref).name
    if name == "01-two-employers.pdf":
        return "two_payslips"
    if name == "02-multipage-payslip.pdf":
        return "multipage_continuation"
    if name == "05-partial-and-unresolved.pdf":
        return "partial_and_unresolved"
    return "default"


def _payslip_fixture_key(document: DocumentState, payslip: PayslipState) -> str:
    """Select a versioned mock response without coupling live adapters to fixtures."""

    name = Path(document.source_document_ref).stem
    pages = "-".join(str(page) for page in payslip.source_pages)
    return f"{name}__pages_{pages}"


def _validation_records(error: ValidationError) -> list[ValidationErrorRecord]:
    return [
        ValidationErrorRecord(
            field_path=".".join(str(part) for part in item["loc"]),
            error_type=item["type"],
            message=item["msg"],
        )
        for item in error.errors()
    ]


def _set_path(payload: dict[str, Any], path: str, value: Any) -> bool:
    parts = path.split(".")
    current: Any = payload
    for part in parts[:-1]:
        if isinstance(current, list) and part.isdigit():
            index = int(part)
            if index >= len(current):
                return False
            current = current[index]
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return False
    final = parts[-1]
    if isinstance(current, list) and final.isdigit():
        index = int(final)
        if index >= len(current):
            return False
        current[index] = value
        return True
    if isinstance(current, dict):
        current[final] = value
        return True
    return False


def _salvage_payslip(
    raw: dict[str, Any], shell: PayslipState, errors: list[ValidationErrorRecord]
) -> PayslipState:
    """Retain independently valid records after the single repair is exhausted."""

    def one(model, key: str, default):
        try:
            return model.model_validate(raw.get(key, {}))
        except ValidationError:
            return default

    def many(model, key: str):
        retained = []
        for item in raw.get(key, []) if isinstance(raw.get(key, []), list) else []:
            try:
                retained.append(model.model_validate(item))
            except ValidationError:
                continue
        return retained

    employer = one(EmployerDetails, "employer", shell.employer)
    employee = one(EmployeeDetails, "employee", shell.employee)
    pay_period = one(PayPeriodDetails, "pay_period", shell.pay_period)
    employment = one(EmploymentDetails, "employment", shell.employment)
    line_items = many(PayItem, "line_items")
    totals = many(PrintedTotal, "totals")
    leave_balances = many(LeaveBalance, "leave_balances")
    other_fields = many(FlexibleField, "other_fields")
    usable = bool(
        employer.name
        or employee.name
        or line_items
        or totals
        or leave_balances
        or other_fields
    )
    return shell.model_copy(
        update={
            "employer": employer,
            "employee": employee,
            "pay_period": pay_period,
            "employment": employment,
            "line_items": line_items,
            "totals": totals,
            "leave_balances": leave_balances,
            "other_fields": other_fields,
            "validation_errors": errors,
            "schema_repair_count": 1,
            "status": PayslipStatus.PARTIAL if usable else PayslipStatus.FAILED,
        }
    )


def _terminal_payslip_command(
    work: PayslipWork, payslip: PayslipState
) -> Command[Literal["assemble_response_json"]]:
    payslip = payslip.model_copy(update={"status": payslip_terminal_status(payslip)})
    document = work["document"].model_copy(update={"payslips": [payslip]})
    return Command(
        update={
            "documents": [document],
            "completed_branch_ids": {_payslip_branch_id(document, payslip)},
        },
        goto="assemble_response_json",
    )


class WorkflowNodes:
    def __init__(
        self,
        *,
        llm_adapter: LlmAdapter,
        output_dir: Path,
    ) -> None:
        self.llm = llm_adapter
        self.output_dir = output_dir

    async def _invoke_llm(
        self, stage: PromptStage, fixture_key: str = "default"
    ) -> dict[str, Any]:
        """Retry retryable service failures twice, for three total attempts."""

        for attempt in range(3):
            try:
                return await self.llm.invoke(stage, fixture_key)
            except AdapterError as exc:
                if not exc.retryable or attempt == 2:
                    raise
        raise AssertionError("unreachable retry state")

    async def segment_documents(
        self, work: dict[str, Any]
    ) -> Command[
        Literal[
            "extract_and_assign_group_labels",
            "record_unresolved_section",
            "assemble_response_json",
        ]
    ]:
        document: DocumentState = work["document"]
        try:
            raw = await self._invoke_llm(
                PromptStage.SEGMENT_DOCUMENTS,
                _segmentation_fixture_key(document),
            )
        except AdapterError:
            raw = {"invalid_after_service_failure": True}
        try:
            result = SegmentationResult.model_validate(raw)
        except ValidationError:
            result = SegmentationResult(
                unresolved_sections=[
                    UnresolvedSection(
                        section_id="unresolved-segmentation-output",
                        source_pages=list(range(1, document.page_count + 1)),
                        raw_text=None,
                        reason="Segmentation output was structurally invalid.",
                        issues=[],
                    )
                ]
            )

        assigned_pages = [
            page
            for boundary in result.payslips
            for page in boundary.source_pages
        ] + [
            page
            for section in result.unresolved_sections
            for page in section.source_pages
        ]
        expected_pages = list(range(1, document.page_count + 1))
        if sorted(assigned_pages) != expected_pages or len(set(assigned_pages)) != len(
            assigned_pages
        ):
            result = SegmentationResult(
                unresolved_sections=[
                    UnresolvedSection(
                        section_id="unresolved-page-coverage",
                        source_pages=expected_pages,
                        raw_text=None,
                        reason="Pages were missing or duplicated in segmentation output.",
                        issues=[],
                    )
                ]
            )

        payslips = [
            PayslipState(
                payslip_id=f"{document.document_id or 'document'}-payslip-{index}",
                document_id=document.document_id,
                source_pages=boundary.source_pages,
                boundary_evidence=boundary,
                status=PayslipStatus.PARTIAL,
            )
            for index, boundary in enumerate(result.payslips, start=1)
        ]
        expected = {
            *(_payslip_branch_id(document, payslip) for payslip in payslips),
            *(
                _unresolved_branch_id(document, section)
                for section in result.unresolved_sections
            ),
        }
        update_document = document.model_copy(update={"payslips": payslips})
        destinations: list[Send | str] = [
            Send(
                "extract_and_assign_group_labels",
                {
                    "request_id": work["request_id"],
                    "document": document,
                    "payslip": payslip,
                },
            )
            for payslip in payslips
        ]
        destinations.extend(
            Send(
                "record_unresolved_section",
                {
                    "request_id": work["request_id"],
                    "document": document,
                    "section": section,
                },
            )
            for section in result.unresolved_sections
        )
        if not destinations:
            destinations.append("assemble_response_json")
        return Command(
            update={
                "documents": [update_document],
                "expected_branch_ids": expected,
                "segmented_document_refs": {_document_key(document)},
            },
            goto=destinations,
        )

    async def record_unresolved_section(
        self, work: UnresolvedWork
    ) -> Command[Literal["assemble_response_json"]]:
        document = work["document"].model_copy(
            update={"unresolved_sections": [work["section"]]}
        )
        return Command(
            update={
                "documents": [document],
                "completed_branch_ids": {
                    _unresolved_branch_id(document, work["section"])
                },
            },
            goto="assemble_response_json",
        )

    async def extract_and_assign_group_labels(
        self, work: PayslipWork
    ) -> Command[Literal["schema_validation_pydantic"]]:
        try:
            raw = await self._invoke_llm(
                PromptStage.EXTRACT_PAYSLIP,
                _payslip_fixture_key(work["document"], work["payslip"]),
            )
        except AdapterError:
            raw = {"invalid_after_service_failure": True}
        raw = deepcopy(raw)
        shell = work["payslip"]
        raw.update(
            {
                "payslip_id": shell.payslip_id,
                "document_id": shell.document_id,
                "source_pages": shell.source_pages,
                "boundary_evidence": shell.boundary_evidence.model_dump(mode="json"),
            }
        )
        items = raw.get("line_items", [])
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                group = known_group_label(item.get("original_label"))
                if group is not None:
                    item.update(
                        {
                            "group_label": group.value,
                            "mapping_method": MappingMethod.RULE.value,
                            "mapping_confidence": 1.0,
                        }
                    )
                elif item.get("group_label") in {None, GroupLabel.UNKNOWN.value}:
                    try:
                        classification_raw = await self._invoke_llm(
                            PromptStage.CLASSIFY_UNFAMILIAR_GROUP_LABELS
                        )
                    except AdapterError:
                        classification_raw = {}
                    classification_raw = {
                        **classification_raw,
                        "item_id": item.get("item_id", "unknown-item"),
                    }
                    try:
                        classification = GroupClassificationResult.model_validate(
                            classification_raw
                        )
                        item.update(classification.model_dump(mode="json"))
                    except ValidationError:
                        item.update(
                            {
                                "group_label": GroupLabel.UNKNOWN.value,
                                "mapping_method": MappingMethod.UNKNOWN.value,
                                "mapping_confidence": None,
                            }
                        )
        next_work = dict(work)
        next_work.update(
            {"raw_payload": raw, "repair_count": 0, "valid_next": "interpret"}
        )
        return Command(goto=Send("schema_validation_pydantic", next_work))

    async def schema_validation_pydantic(
        self, work: PayslipWork
    ) -> Command[
        Literal[
            "schema_repair_once",
            "interpret_total_relationships",
            "reconcile_totals",
            "assemble_response_json",
        ]
    ]:
        raw = work.get("raw_payload", work["payslip"].model_dump(mode="python"))
        try:
            payslip = PayslipState.model_validate(raw)
        except ValidationError as exc:
            errors = _validation_records(exc)
            if work.get("repair_count", 0) == 0:
                next_work = dict(work)
                next_work["validation_errors"] = errors
                return Command(goto=Send("schema_repair_once", next_work))
            salvaged = _salvage_payslip(raw, work["payslip"], errors)
            return _terminal_payslip_command(work, salvaged)

        next_work = dict(work)
        next_work["payslip"] = payslip
        next_work["raw_payload"] = payslip.model_dump(mode="python")
        if work.get("valid_next") == "reconcile":
            return Command(goto=Send("reconcile_totals", next_work))
        return Command(goto=Send("interpret_total_relationships", next_work))

    async def schema_repair_once(
        self, work: PayslipWork
    ) -> Command[Literal["schema_validation_pydantic"]]:
        try:
            repair_raw = await self._invoke_llm(PromptStage.SCHEMA_REPAIR_ONCE)
        except AdapterError:
            repair_raw = {}
        payload = deepcopy(work.get("raw_payload", {}))
        allowed = {error.field_path for error in work.get("validation_errors", [])}
        try:
            repair = RepairResult.model_validate(repair_raw)
            for path in repair.repaired_field_paths:
                if path in allowed and path in repair.patch:
                    _set_path(payload, path, repair.patch[path])
        except ValidationError:
            pass
        next_work = dict(work)
        next_work.update({"raw_payload": payload, "repair_count": 1})
        return Command(goto=Send("schema_validation_pydantic", next_work))

    async def interpret_total_relationships(
        self, work: PayslipWork
    ) -> Command[Literal["reconcile_totals", "assemble_response_json"]]:
        payslip = work["payslip"]
        if not payslip.totals:
            return _terminal_payslip_command(work, payslip)

        previous = {
            check.printed_total_id: check for check in payslip.reconciliation_checks
        }
        checks: list[ReconciliationCheckState] = []
        for index, total in enumerate(payslip.totals, start=1):
            try:
                raw = await self._invoke_llm(
                    PromptStage.INTERPRET_TOTAL_RELATIONSHIPS,
                    total.total_id,
                )
            except AdapterError:
                raw = {}
            try:
                relationship = TotalRelationship.model_validate(raw)
            except ValidationError:
                relationship = TotalRelationship(
                    terms=[], explanation="Relationship output was structurally invalid."
                )
            existing = previous.get(total.total_id)
            base = ReconciliationCheckState(
                check_id=f"{payslip.payslip_id}-check-{index}",
                payslip_id=payslip.payslip_id,
                printed_total_id=total.total_id,
                relationship=relationship,
                printed_amount=total.amount,
                currency=total.currency or payslip.currency,
                status=ReconciliationStatus.UNABLE_TO_CHECK,
                reason="Pending deterministic reconciliation.",
                rounding_assessment=RoundingAssessment.NOT_APPLICABLE,
                source_pages=[total.source_page],
            )
            if existing is not None:
                base = base.model_copy(
                    update={
                        "targeted_retry_count": existing.targeted_retry_count,
                        "targeted_retry_type": existing.targeted_retry_type,
                        "judge_outcome": existing.judge_outcome,
                        "judge_reason": existing.judge_reason,
                        "issues": existing.issues,
                    }
                )
            checks.append(base)
        next_work = dict(work)
        next_work["payslip"] = payslip.model_copy(
            update={"reconciliation_checks": checks}
        )
        return Command(goto=Send("reconcile_totals", next_work))

    async def reconcile_totals(
        self, work: PayslipWork
    ) -> Command[Literal["llm_as_a_judge", "assemble_response_json"]]:
        payslip = work["payslip"]
        checks = [
            reconcile_check(check, payslip.line_items, payslip.totals)
            for check in payslip.reconciliation_checks
        ]
        payslip = payslip.model_copy(update={"reconciliation_checks": checks})
        for index, check in enumerate(checks):
            if (
                check.status is not ReconciliationStatus.MATCHED
                and check.targeted_retry_count == 0
                and check.judge_outcome is JudgeOutcome.NOT_RUN
            ):
                next_work = dict(work)
                next_work.update({"payslip": payslip, "current_check_index": index})
                return Command(goto=Send("llm_as_a_judge", next_work))

        for index, check in enumerate(checks):
            if check.status is ReconciliationStatus.MATCHED:
                continue
            if not any(issue.issue_code == "reconciliation_review" for issue in check.issues):
                checks[index] = check.model_copy(
                    update={
                        "issues": [
                            *check.issues,
                            review_issue(
                                issue_id=f"{check.check_id}-review",
                                code="reconciliation_review",
                                message="Reconciliation remains unresolved after approved checks.",
                                pages=check.source_pages,
                            ),
                        ]
                    }
                )
        payslip = payslip.model_copy(update={"reconciliation_checks": checks})
        return _terminal_payslip_command(work, payslip)

    async def llm_as_a_judge(
        self, work: PayslipWork
    ) -> Command[
        Literal[
            "retry_affected_extraction",
            "retry_reconciliation_item_selection",
            "reconcile_totals",
        ]
    ]:
        index = work["current_check_index"]
        payslip = work["payslip"]
        checks = list(payslip.reconciliation_checks)
        try:
            raw = await self._invoke_llm(PromptStage.LLM_AS_A_JUDGE)
        except AdapterError:
            raw = {}
        try:
            result = JudgeResult.model_validate(raw)
        except ValidationError:
            result = JudgeResult(
                judge_outcome=JudgeOutcome.INCONCLUSIVE,
                judge_reason="Judge output was invalid or unavailable.",
            )
        check = checks[index].model_copy(
            update={
                "judge_outcome": result.judge_outcome,
                "judge_reason": result.judge_reason,
            }
        )
        checks[index] = check
        payslip = payslip.model_copy(update={"reconciliation_checks": checks})
        next_work = dict(work)
        next_work["payslip"] = payslip
        if (
            result.judge_outcome is JudgeOutcome.POSSIBLE_EXTRACTION_ERROR
            and result.affected_field_paths
        ):
            next_work["affected_field_paths"] = result.affected_field_paths
            return Command(goto=Send("retry_affected_extraction", next_work))
        if (
            result.judge_outcome
            is JudgeOutcome.POSSIBLE_RECONCILIATION_ITEM_SELECTION_ERROR
        ):
            return Command(
                goto=Send("retry_reconciliation_item_selection", next_work)
            )
        return Command(goto=Send("reconcile_totals", next_work))

    async def retry_affected_extraction(
        self, work: PayslipWork
    ) -> Command[Literal["schema_validation_pydantic"]]:
        try:
            raw = await self._invoke_llm(PromptStage.RETRY_AFFECTED_EXTRACTION)
        except AdapterError:
            raw = {}
        payload = work["payslip"].model_dump(mode="python")
        allowed = set(work.get("affected_field_paths", []))
        try:
            result = ExtractionRetryResult.model_validate(raw)
            for path in result.affected_field_paths:
                if path in allowed and path in result.patch:
                    _set_path(payload, path, result.patch[path])
        except ValidationError:
            pass
        index = work["current_check_index"]
        checks = list(work["payslip"].reconciliation_checks)
        checks[index] = checks[index].model_copy(
            update={
                "targeted_retry_type": TargetedRetryType.EXTRACTION,
                "targeted_retry_count": 1,
            }
        )
        payload["reconciliation_checks"] = [
            check.model_dump(mode="python") for check in checks
        ]
        next_work = dict(work)
        next_work.update(
            {
                "raw_payload": payload,
                "repair_count": 1,
                "valid_next": "interpret",
            }
        )
        return Command(goto=Send("schema_validation_pydantic", next_work))

    async def retry_reconciliation_item_selection(
        self, work: PayslipWork
    ) -> Command[Literal["schema_validation_pydantic"]]:
        try:
            raw = await self._invoke_llm(
                PromptStage.RETRY_RECONCILIATION_ITEM_SELECTION
            )
        except AdapterError:
            raw = {}
        payslip = work["payslip"]
        checks = list(payslip.reconciliation_checks)
        index = work["current_check_index"]
        try:
            relationship = TotalRelationship.model_validate(raw)
            checks[index] = checks[index].model_copy(
                update={
                    "relationship": relationship,
                    "targeted_retry_type": TargetedRetryType.RECONCILIATION_ITEM_SELECTION,
                    "targeted_retry_count": 1,
                }
            )
        except ValidationError:
            checks[index] = checks[index].model_copy(
                update={
                    "targeted_retry_type": TargetedRetryType.RECONCILIATION_ITEM_SELECTION,
                    "targeted_retry_count": 1,
                    "validation_errors": [
                        ValidationErrorRecord(
                            field_path="relationship",
                            error_type="invalid_relationship",
                            message="Targeted relationship retry was structurally invalid.",
                        )
                    ],
                }
            )
        payslip = payslip.model_copy(update={"reconciliation_checks": checks})
        next_work = dict(work)
        next_work.update(
            {
                "payslip": payslip,
                "raw_payload": payslip.model_dump(mode="python"),
                "repair_count": 1,
                "valid_next": "reconcile",
            }
        )
        return Command(goto=Send("schema_validation_pydantic", next_work))

    async def assemble_response_json(
        self, state: WorkflowState
    ) -> Command[Literal["write_json", "__end__"]]:
        document_refs = {_document_key(document) for document in state["documents"]}
        segmented = state.get("segmented_document_refs", set())
        expected = state.get("expected_branch_ids", set())
        completed = state.get("completed_branch_ids", set())
        if not document_refs.issubset(segmented) or not expected.issubset(completed):
            return Command(goto=END)

        documents = [
            document.model_copy(update={"status": derive_document_status(document)})
            for document in state["documents"]
        ]
        item_count = sum(
            len(payslip.line_items)
            for document in documents
            for payslip in document.payslips
        )
        checks = [
            check
            for document in documents
            for payslip in document.payslips
            for check in payslip.reconciliation_checks
        ]
        metadata = ProcessingMetadata(
            documents=DocumentCounts(
                total=len(documents),
                successful=sum(document.status.value == "successful" for document in documents),
                partial=sum(document.status.value == "partial" for document in documents),
                failed=sum(document.status.value == "failed" for document in documents),
            ),
            payslips=PayslipCounts(
                detected=sum(len(document.payslips) for document in documents),
                successful=sum(
                    payslip.status.value == "successful"
                    for document in documents
                    for payslip in document.payslips
                ),
                partial=sum(
                    payslip.status.value == "partial"
                    for document in documents
                    for payslip in document.payslips
                ),
                failed=sum(
                    payslip.status.value == "failed"
                    for document in documents
                    for payslip in document.payslips
                ),
                unresolved=sum(len(document.unresolved_sections) for document in documents),
            ),
            items=ItemCounts(detected=item_count, successful=item_count),
            reconciliation=ReconciliationCounts(
                matched=sum(check.status is ReconciliationStatus.MATCHED for check in checks),
                mismatched=sum(check.status is ReconciliationStatus.MISMATCHED for check in checks),
                unable_to_check=sum(
                    check.status is ReconciliationStatus.UNABLE_TO_CHECK for check in checks
                ),
            ),
        )
        response = ExtractionResponse(
            request_id=state["request_id"],
            claim_number=state["claim_number"],
            documents=[DocumentResult.from_state(document) for document in documents],
            status=derive_request_status(documents),
            processing_metadata=metadata,
            adapter_mode=state["adapter_mode"],
            max_concurrency=state["max_concurrency"],
            versions=state["versions"],
            issues=state["issues"],
        )
        return Command(
            update={
                "documents": documents,
                "status": response.status,
                "processing_metadata": metadata,
                "response_json": response.model_dump(mode="json", by_alias=True),
            },
            goto="write_json",
        )

    async def write_json(
        self, state: WorkflowState
    ) -> Command[Literal["__end__"]]:
        response = ExtractionResponse.model_validate(state["response_json"])
        output_path = publish_response(response, self.output_dir)
        return Command(
            update={"output_path": str(output_path), "publication_complete": True},
            goto=END,
        )
