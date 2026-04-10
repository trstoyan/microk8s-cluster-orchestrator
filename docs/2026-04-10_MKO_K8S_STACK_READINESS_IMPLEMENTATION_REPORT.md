# 2026-04-10 MKO Kubernetes Stack Readiness — Implementation Report

## Objective

Prepare MKO for in-cluster deployment as a stack component with minimal, production-oriented packaging and guardrails.

## Implemented

1. **Container runtime hardening**
- Switched image runtime command to Gunicorn (`wsgi:application`).
- Added root `wsgi.py` entrypoint.
- Added `kubectl` binary in image for plugin apply operations.
- Removed image build-time DB initialization.

2. **Kubernetes deployment assets**
- Added `deployment/k8s/` manifest set:
  - namespace
  - service account + RBAC
  - PVC
  - configmap
  - secret example
  - deployment
  - service
  - kustomization
- Added rollout helper script: `deployment/scripts/deploy_k8s_stack.sh`.

3. **Security/runtime wiring**
- Added environment override for Flask secret key (`FLASK_SECRET_KEY`) in app factory.
- Deployment now injects `FLASK_SECRET_KEY`/`SECRET_KEY` from Kubernetes secret.
- Deployment sets `ORCHESTRATOR_AUTO_MIGRATE=true` and PVC-backed database path.

4. **Documentation**
- Added `docs/DEPLOYMENT_K8S_STACK.md`.
- Updated `README.md` and `docs/DEPLOYMENT.md` references.
- Updated `docs/CHANGELOG.md`.

5. **Contract tests**
- Added `tests/test_k8s_stack_deployment_contracts.py`.

## Notes

- This slice adds deployment packaging and readiness assets.
- It does not perform an in-session cluster apply to avoid ambiguous-target mutations.
