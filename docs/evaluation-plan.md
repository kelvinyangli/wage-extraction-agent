# Wage Extraction Agent Evaluation Plan

System/version: Proposed local mock prototype; versions recorded per run  
Owner: Data Scientist  
Risk classification: Moderate-risk de-identified mock prototype; future production is high risk  
Evaluation date: 8 November 2026  
Release decision owner: Data Scientist for the local prototype; production owners to be assigned separately

Current execution result (8 November 2026): all 46 tests pass. All six synthetic documents conform to their versioned expected results. In the mismatch fixture, the LLM-selected mock relationship checks gross from its contributing pay items and net from the context-supported printed gross plus signed PAYG; deterministic code validates the source references, rejects target-total self-reference and performs the arithmetic. Atomic-publication fault injection also confirms that a failed replacement leaves no final or temporary file. This supports the deterministic mock-conformance claim only, not live-model accuracy.

Machine-readable evidence: `output/evaluation/pytest-results.xml`. Prompt identity: `prompt-bundle-v2`, SHA-256 `742cf4119d2a4ebdeb8720c580e2483953676e8778e941fcbe871525664101a2`.

## 1. Claims and release decision

### Prototype claims

- The approved LangGraph routes mock Document Intelligence and mock GPT responses into the agreed JSON structure.
- Deterministic schema checks, page coverage, signed-decimal reconciliation, retry limits, branch isolation, status derivation and safe publication behave exactly as designed.
- Mock fixtures preserve readable values, duplicates, conflicts, unresolved content and source references without silent invention or deletion.
- Prompt-injection fixtures do not alter task scope, permissions, routing or output structure.

### Decisions supported

- Whether the local prototype conforms to its approved deterministic contracts.
- Whether it is ready for a later, separately approved live Azure integration and quality-evaluation phase.

### Non-goals

- The mock evaluation does not establish live OCR accuracy, GPT extraction accuracy, generalisation across employers, calibrated mapping confidence, live judge quality, production security or operational readiness.
- It does not validate claim calculations, entitlement, eligibility, liability, fraud or any automated claim decision.

### Baseline

- Primary prototype baseline: versioned expected outputs for the approved mock fixtures.
- Future live-model comparison baseline: zero-shot prompt configuration. Few-shot or other techniques must be compared on a separate held-out set under bookmark `B-003`.

## 2. Failure model

| Failure mode | Impact | Detection method | Required control |
|---|---|---|---|
| Readable source value omitted or changed | Incorrect downstream spreadsheet data | Atomic fact recall and exact-value comparison | Preserve original values; human gold labels; partial results rather than silent loss |
| Unsupported value invented | Financial/administrative error | Fact precision and unsupported-claim rate | Evidence grounding, nullable fields and abstention outcomes |
| Incorrect page-to-payslip boundary | Values assigned to wrong employer or period | Boundary accuracy and exactly-once page coverage | Continuity rules, boundary evidence and unresolved path |
| Duplicate or conflicting source record removed | Loss of source fidelity | Record-count and identity comparison | No deduplication; preserve every source record |
| Incorrect group label | Misleading later grouping | Mapping accuracy and confusion matrix | Deterministic known mappings first; `Unknown` for uncertainty |
| Malformed structured output | Downstream processing failure | Pydantic and output-schema tests | One bounded repair, then partial/failed isolation |
| Incorrect reconciliation relationship | False mismatch or false reassurance | Human-labelled relationship accuracy and deterministic test oracle | LLM selects terms; code validates IDs/currency and performs arithmetic |
| Arithmetic or rounding error | Incorrect quality signal | Unit/property tests with exact decimals | `Decimal`, exact comparison and explicit rounding assessment |
| Judge misclassifies anomaly | Unnecessary or harmful retry | Human-gold confusion matrix and class precision/recall | Advisory judge, `inconclusive`, one targeted retry, human review |
| Embedded instruction changes behavior | Scope or data-integrity failure | Adversarial injection suite | Delimitation, no tools, fixed schema and deterministic permissions |
| One branch failure stops other work | Missing results | Orchestration failure-injection tests | Independent branches and terminal fan-in |
| Retry loop exceeds limit | Cost/latency escalation | Attempt-count assertions | One schema repair and one targeted retry per check |
| Interrupted JSON write exposes partial file | Consumer receives corrupt output | Publication fault-injection tests | Same-directory temporary file and atomic replacement |

## 3. Dataset and gold labels

### Prototype fixture suite

- Version the current sample and synthetic documents, mock service outputs and `expected-results.json` together.
- Cover multiple employers, multi-page continuation, pay summaries, duplicates/conflicts, partial and unresolved pages, total mismatches, malformed model output, timeouts, transient/permanent failures and direct/indirect prompt injection.
- Treat this suite as deterministic conformance evidence only. Do not report it as live-model accuracy.

### Future live-quality dataset

- Sample de-identified real payslips across employers, layouts, scan quality, page counts, pay frequencies, currencies and item types.
- Include representative, edge, adversarial, conflicting, unreadable and correct-abstention cases.
- Split development and held-out sets by source document and employer/layout family where possible, preventing near-duplicate leakage.
- Keep the held-out set unavailable for prompt/example selection. Version documents, labels, instructions and split membership.
- Use case managers or payroll-literate subject-matter reviewers for factual labels. Difficult boundary, mapping and relationship cases require independent second review and adjudication by the Data Scientist with a business SME.
- Gold labels may explicitly allow `unreadable`, `Unknown`, `uncertain`, `unable_to_check` or more than one acceptable interpretation.
- Record inter-rater agreement and adjudication counts. Production thresholds cannot be set or claimed until the dataset is sufficiently representative.

## 4. Metrics and thresholds

### Local mock prototype release thresholds

| Dimension | Metric | Threshold |
|---|---|---|
| Schema | Expected valid/invalid outcomes and JSON conformance | 100% of versioned fixtures |
| Source preservation | Readable fixture values, labels, duplicates and conflicts preserved exactly | 100% |
| Page handling | Exactly-once assignment and expected payslip/unresolved boundaries | 100% |
| Deterministic mapping | Known mapping outcomes | 100% |
| Reconciliation | Expected decimal sums, differences, statuses and retry routes | 100% |
| Failure isolation | Unaffected documents, payslips and items continue | 100% of injected cases |
| Retry limits | Schema repair and targeted retry counts never exceed approved limits | 100% |
| Prompt injection | Embedded instructions do not change permissions, schema or scope | 100% of adversarial fixtures |
| Publication | Interrupted/failed writes never expose a half-written final JSON file | 100% of fault-injection cases |

An expected `None`, `Unknown`, `unreadable`, `uncertain`, `partial`, `failed`, `unable_to_check` or `inconclusive` outcome counts as correct when supported by the fixture. Passing these thresholds authorises only the mock prototype claim.

### Future live-quality metrics

| Dimension | Metric | Required slices | Threshold status |
|---|---|---|---|
| Factuality | Atomic fact precision | Field type, employer/layout, scan quality | Must be set from human-gold baseline before live release |
| Coverage | Atomic fact recall | Field type, item type, employer/layout, scan quality | Must be set before live release |
| Grounding | Unsupported-claim/value rate | Material monetary and identity fields separately | Must be set before live release |
| Attribution | Source page/location locatability | Fixed fields, items and totals | Must be set before live release |
| Evidence verification | Exact value supported by the cited source region | Monetary versus non-monetary facts | Must be set before live release |
| Semantic faithfulness | Structured meaning preserves source meaning | Dates, signs, units, rates and totals | Must be set before live release |
| Boundary quality | Page/payslip boundary precision, recall and exact-document accuracy | Single/multi-page and multi-employer | Must be set before live release |
| Group mapping | Accuracy, macro precision/recall and `Unknown` appropriateness | Known versus unfamiliar labels | Must be set before live release |
| Reconciliation | Relationship-selection accuracy plus deterministic arithmetic correctness | Total type and complexity | Arithmetic must remain 100%; relationship threshold set from gold data |
| Abstention | Appropriate abstention and inappropriate-certainty rates | Unreadable, conflicting and novel layouts | Must be set before live release |
| Operations | Latency, token/cost, external failure and escalation rates | Node and document type | Budgets require measured Azure evidence |

Report denominators and confidence intervals where sample size permits. Never collapse attribution, evidence support and semantic faithfulness into a single grounding score.

## 5. LLM judge calibration

- The judge is used only for reconciliation anomalies where deterministic arithmetic can detect a problem but cannot determine whether extraction or item selection is more likely responsible.
- Prototype evaluation verifies mock routing only and makes no live judge-accuracy claim.
- Before any live reliance, create a human-labelled anomaly set covering `supports_extraction`, `possible_extraction_error`, `possible_reconciliation_item_selection_error` and `inconclusive`.
- Record judge model/settings, prompt/rubric version, blinded inputs where practical, agreement, confusion matrix, per-class precision/recall, rerun stability and difficult slices.
- A human-gold baseline must set the acceptance threshold. The judge cannot grade its own outputs as the sole release gate.
- Sample live judge outcomes for governed human review. A model/version or material prompt/rubric change triggers recalibration.

## 6. Deterministic and system tests

- Pydantic required, nullable, enum, bound, extra-field and nested-validation cases.
- Decimal sign, precision, exact-match, non-match, rounding-assessment and missing-input cases.
- Relationship ID existence, duplicate term, multiplier and currency compatibility checks.
- Page exactly-once coverage, continuation, new-payslip and unresolved routing.
- All approved conditional edges, fan-out/fan-in behavior and terminal statuses.
- One schema repair, one total targeted retry, retry exhaustion and allowed-field-diff enforcement.
- Transient versus permanent external failures, timeouts and branch isolation.
- No-tool/no-action negative tests and direct/indirect injection cases.
- Final schema validation, decimal-string serialization and atomic-publication fault tests.
- Version and trace-field assertions without full OCR text, pay values, prompts or secrets in operational logs.

## 7. Execution and evidence

- Pin code, fixture, expected-result, model, prompt, schema, mapping and adapter versions.
- Store machine-readable test results plus a concise failure report by fixture, node, route and failure class.
- Keep gold labels separate from model outputs and record any post-evaluation label correction.
- Any threshold failure blocks the corresponding claim. Corrective changes require regression of the full deterministic suite and affected quality slices.
- Record deviations from this plan and their owner; do not silently exclude failing cases.

## 8. Production monitoring requirements

Production monitoring is outside prototype implementation and remains owned by AI Engineering and future service owners. Before production, define:

- privacy-minimised traces with request/document/payslip/check IDs, versions, routes, rule results, attempts, latency, token/cost signals, errors and uncertainty outcomes;
- alert thresholds and owners for failure, partial, unresolved, mismatch, judge, retry, latency and drift rates;
- runbooks, rollback/kill-switch criteria, retention and access controls;
- governed sampling and human labeling rather than treating user feedback as automatic truth;
- re-evaluation triggers for model, prompt, schema, mapping, adapter, OCR-service or material population/layout changes.

## 9. Release decision

- Prototype release requires every deterministic mock threshold above to pass and the approved design/review checklist to be complete.
- Passing permits only local mock prototype use. It does not approve Azure deployment, Jade integration, production data or operational claim use.
- Live or production release remains `no release` until representative human-gold evaluation, explicit quality thresholds, judge calibration, security/privacy/integration verification and named production owners are complete.
- Residual prototype limitations are accepted only by the Data Scientist through explicit final design and evaluation approval.

### Recorded decision

**Accepted for local mock-prototype use on 8 November 2026 by the Data Scientist.** All 46 tests passed and the six versioned synthetic scenarios conformed to expected results. The accepted limitations are that Azure OCR/GPT services are mocked, live extraction and judge accuracy are unverified, the sample set is not representative of production diversity, and production security, privacy, Jade integration and operations remain outside this acceptance.
