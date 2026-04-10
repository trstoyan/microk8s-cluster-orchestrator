# MKO Kubernetes Stack Deployment

This guide deploys MKO as an in-cluster stack component.

## Included Assets

- `deployment/k8s/namespace.yaml`
- `deployment/k8s/serviceaccount-rbac.yaml`
- `deployment/k8s/pvc.yaml`
- `deployment/k8s/configmap.yaml`
- `deployment/k8s/deployment.yaml`
- `deployment/k8s/service.yaml`
- `deployment/k8s/secret.example.yaml`
- `deployment/scripts/deploy_k8s_stack.sh`

## Prerequisites

- Kubernetes cluster reachable via `kubectl`.
- Container image pushed and accessible by the cluster.
- A strong secret configured in `deployment/k8s/secret.yaml`.

## Deploy

1. Set deployment image in `deployment/k8s/deployment.yaml`.
2. Create `deployment/k8s/secret.yaml` from the example and replace keys.
3. Run:

```bash
./deployment/scripts/deploy_k8s_stack.sh
```

## Runtime Contract

- HTTP health endpoint: `GET /api/health`
- SQLite database path (PVC-backed): `/app/data/cluster_data.db`
- Config file path (ConfigMap-backed): `/app/config/cluster.yml`
- Startup mode: Gunicorn (`wsgi:application`)
- Auto migration: enabled via `ORCHESTRATOR_AUTO_MIGRATE=true`

## Plugin Apply Requirements

`/api/plugins/{plugin_id}/apply` shells out to `kubectl` and requires:

- Service account `mko`
- Namespace-local RBAC for `configmaps` create/update/patch and `deployments` patch

