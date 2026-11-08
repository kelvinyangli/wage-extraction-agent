# Wage Extraction Agent

Local mock prototype for converting payslip documents into evidence-grounded, API-ready JSON.

**Status:** Accepted local mock prototype as of 8 November 2026. This acceptance does not cover live Azure services, Jade integration, production data or deployment.

The approved design is in [`docs/design-specification.md`](docs/design-specification.md). This repository does not contain a live Azure Document Intelligence connection, Jade integration, deployment configuration, or production-data support.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
```

Configuration uses environment variables; no computer-specific paths are required. See [`.env.example`](.env.example).

## Current implementation status

Increments 1 through 3 implement project configuration, approved schemas/state, versioned mock Document Intelligence/GPT adapters, all twelve approved LangGraph nodes and dynamic destinations, bounded repair/retries, deterministic reconciliation, atomic JSON publication and route-focused tests. Increment 4 adds end-to-end synthetic expected-result fixtures and checks, context-guided selection of pay items or printed totals for reconciliation, and full conformance across all six synthetic documents.

The current approved prompt bundle is [`prompts/v2`](prompts/v2); [`prompts/v1`](prompts/v1) remains immutable for audit and rollback. Prompt wording is not embedded in Python files; the strict loader is under `src/wage_extraction_agent/prompting`.

