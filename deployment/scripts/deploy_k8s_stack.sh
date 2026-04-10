#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
K8S_DIR="${ROOT_DIR}/deployment/k8s"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "[error] kubectl is required" >&2
  exit 1
fi

if [[ ! -f "${K8S_DIR}/secret.example.yaml" ]]; then
  echo "[error] missing ${K8S_DIR}/secret.example.yaml" >&2
  exit 1
fi

if [[ ! -f "${K8S_DIR}/secret.yaml" ]]; then
  echo "[info] creating ${K8S_DIR}/secret.yaml from template"
  cp "${K8S_DIR}/secret.example.yaml" "${K8S_DIR}/secret.yaml"
  echo "[warn] edit ${K8S_DIR}/secret.yaml before first production deployment"
fi

kubectl apply -f "${K8S_DIR}/namespace.yaml"
kubectl apply -f "${K8S_DIR}/serviceaccount-rbac.yaml"
kubectl apply -f "${K8S_DIR}/pvc.yaml"
kubectl apply -f "${K8S_DIR}/configmap.yaml"
kubectl apply -f "${K8S_DIR}/secret.yaml"
kubectl apply -f "${K8S_DIR}/deployment.yaml"
kubectl apply -f "${K8S_DIR}/service.yaml"

kubectl -n orchestrator rollout status deploy/microk8s-cluster-orchestrator --timeout=180s
kubectl -n orchestrator get pods -l app.kubernetes.io/name=microk8s-orchestrator
kubectl -n orchestrator get svc microk8s-cluster-orchestrator

