# Wage Extraction Agent - Pre-approval Review

Date: 8 November 2026  
Owner and reviewer: Data Scientist  
Scope: Local de-identified mock prototype  
Status: Local mock prototype accepted and complete

## Pre-approval completeness record

| Dimension | Status | Evidence | Blocking finding / owner |
|---|---|---|---|
| Architecture and orchestration | Pass | Design sections 4-6 contain the approved implementation-intent Mermaid DAG, twelve-node transition table, mixed TypedDict/Pydantic state contracts, exact edge predicates, bounded repair/retry routes, fan-out/fan-in, terminal statuses, in-memory/no-resume decision, no runtime interrupt and trace boundaries. | None |
| Prompt and context | Pass | Section 5 inventories all eight LLM stages and records roles, authority, trust boundaries, output contracts, abstention, verification and every baseline prompting-technique choice. | None |
| Guardrails and governance | Pass | Section 12 records risk, prohibited uses, accountability and the required control review: deterministic boundaries, Pydantic limits, injection controls, evidence checks, judge limits, human authority, least privilege and confidence treatment. | None |
| Evaluation and observability | Pass | `docs/evaluation-plan.md` separates deterministic mock conformance from unverified live quality and defines failure modes, datasets, gold labels, fact metrics, grounding dimensions, judge calibration, system tests, traces and release gates. | None for prototype; live release remains blocked pending gold evaluation and calibration |
| Integration and operations | Pass | Design sections 2, 4 and 10 define external adapter boundaries, mock/live modes, failure semantics, timeouts, bounded retries, safe publication, version records and privacy-minimised traces. | None for prototype scope |

## Required technique review record

| Technique or control | Status | Evidence, decision, or N/A rationale | Open decision / owner |
|---|---|---|---|
| LLM interpretation versus deterministic rules and controls | Pass | LLM interpretation is limited to ambiguous document tasks; schemas, IDs, page coverage, arithmetic, routing, retries, statuses and publication are deterministic. | None |
| Prompt role, task, scope, prohibited behavior and escalation boundaries | Pass | Each prompt stage has bounded authority, no tools, a structured output and an explicit abstention/escalation contract. | None |
| Pydantic/schema structural validation and failure handling | Pass | Pydantic is explicitly structural only; one allowed-field repair is followed by validation, partial/failed isolation and visible issues. | None |
| Prompt-injection and untrusted-content controls and tests | Pass | All document/model content is delimited as untrusted; schema, permissions and no-tool boundaries are fixed; adversarial fixtures are required. | None |
| Source attribution, evidence verification and semantic faithfulness | Pass | Page/location existence, evidence support and meaning preservation are retained and evaluated separately. | None |
| LLM judge necessity, calibration, limitations and human reference | Pass for prototype design | Judge runs only on anomalies, is advisory, has `inconclusive`, cannot override arithmetic and permits one targeted retry. Prototype mocks establish routing only; live calibration against human gold is a production release gate. | None for prototype |

## Design and approval readiness

- Pass: Implemented behavior, proposed work, external dependencies, assumptions and unverified capabilities are distinguished. Increment 1 foundation and schemas are implemented; all 13 collected increment-1 tests passed on 8 November 2026.
- Pass: Bookmarks use stable IDs. `B-001` is resolved; `B-002` and `B-003` are deferred with owners, milestones and reasons. No required bookmark is open.
- Pass: Scope, prohibited uses, decision boundaries, accountability and residual prototype risks are explicit.
- Pass: LangGraph is justified by independent branches, conditional bounded retries, partial failure and per-node observability; the simpler direct-function alternative is recorded.
- Pass: Nodes, state, conditions, joins, retries, checkpoints, interrupts, terminal outcomes and traces are defined and approved.
- Pass: All LLM prompt stages and baseline techniques are reviewed. RAG, ReAct, DSPy, few-shot baseline and hidden chain-of-thought are not used in the prototype for recorded reasons.
- Pass: Evidence grounding, injection exposure, nullable/unknown semantics and material prompt-change boundaries are defined.
- Pass: Risk-based layered controls retain case-manager authority and prohibit claim calculations or decisions.
- Pass: Deterministic mock thresholds are explicit. Future live factuality, coverage, unsupported-value, boundary, mapping, judge and operational thresholds remain release-blocking until supported by human-gold evidence.
- Pass: External writes are limited to validated JSON using temporary-file and atomic-publication behavior.
- Pass: The Data Scientist explicitly approved the complete local mock-prototype design and authorised implementation on 8 November 2026.

## Review outcome

- Blocking findings: None for approved local implementation scope.
- Open review bookmarks: None.
- Deferred bookmarks: `B-002` production schema evolution; `B-003` few-shot/other prompt-technique comparison after a representative real-payslip corpus exists.
- Non-blocking prototype limitations: Mock services do not establish live OCR/GPT accuracy; samples are not representative of all employers; the mock judge is not calibrated; production privacy, security and integration verification belongs to the later AI Engineering deployment review.
- Approved limitations: Prototype-only residual risks in design section 12 and evaluation-plan section 9. These are not accepted as production limitations.
- Implemented remediations: Project foundation, approved schemas/state, versioned mock adapters, controlled failures, twelve-node LangGraph workflow, dynamic destinations, bounded repair/retries, context-guided relationship selection, deterministic reconciliation, atomic JSON publication, immutable prompt bundles and 46 passing tests.
- Proposed implementation: Only the explicitly approved local mock-prototype scope after final design approval.
- Solution-technique summary: `docs/solution-technique-summary.md` generated from implemented code, prompts, graph, schemas, rules and evaluation evidence on 8 November 2026.
- Validator result: Pass on 8 November 2026.
- Reviewer decision: The Data Scientist accepted the completed local mock prototype with documented limitations on 8 November 2026. Azure deployment, Jade integration and production-data use remain unauthorised.
