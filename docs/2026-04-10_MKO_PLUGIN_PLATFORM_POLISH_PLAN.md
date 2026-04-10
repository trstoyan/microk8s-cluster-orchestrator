# MKO Polish Plan (Boundary-Safe, Business-Agnostic)

## Purpose
Polish MKO as a reusable orchestration platform without embedding project-specific business logic.
This plan intentionally excludes downstream-project-specific product behavior and data semantics.

## Boundary Rules
- MKO owns platform primitives: plugin lifecycle, security controls, execution guardrails, auditability.
- Downstream projects own business plugins and domain-specific checks/actions.
- MKO must not hardcode external project namespaces, routes, strategy terms, or runtime semantics.

## Current Baseline Delivered
- Plugin installation registry and action audit tables.
- Manifest-based plugin loading contract (`mko_plugin_api=v1`).
- Admin-gated plugin install/enable/disable/rollback/apply APIs.
- Pinned repo+commit trust enforcement for git install path.
- Two-step action flow (`plan` then `execute`) with signed short-lived tokens.

## Polish Backlog (MKO Core)
1. Security hardening
- Add IP allowlist middleware for mutation endpoints.
- Add per-action rate limit and cooldown guardrails.
- Add token replay prevention beyond hash logging.

2. Execution reliability
- Move plugin action execution to app-context-safe worker path.
- Add cancellation semantics and deterministic final states.
- Add operation timeout policy per action class.

3. Plugin UX and operations
- Add plugin inventory page in UI with status and audit trail.
- Show manifest validation failures with actionable diagnostics.
- Add dry-run preview for apply/install and rollback impacts.

4. Supply-chain controls
- Add optional signed-tag verification layer (post pinned-commit baseline).
- Add plugin SBOM/checksum metadata in install records.

5. Conformance tests
- Add API-level tests for plugin authz and boundary checks.
- Add end-to-end tests for install -> enable -> plan -> execute -> audit.
- Add migration compatibility tests for plugin tables.

## Acceptance Criteria for MKO Polish
- MKO core remains domain-agnostic with no project-coupled constants.
- All plugin mutation APIs are admin-only and auditable.
- Failed plugin operations fail closed with explicit error status.
- Plugin execution lifecycle is reproducible and test-covered.

## Out of Scope
- Any downstream-project-specific health model, strategy logic, or runtime diagnosis.
- Any downstream project UI semantics inside MKO core pages.
