#!/usr/bin/env bash
set -euo pipefail

# Rebuilds the API image, pushes it to GCR and rolls out the deployment in GKE.
# Usage examples:
#   ./scripts/redeploy.sh
#   TAG=v1.2.3 ./scripts/redeploy.sh
#   PROJECT_ID=my-project NAMESPACE=cassellas-api ./scripts/redeploy.sh

PROJECT_ID="${PROJECT_ID:-project-35924d4e-e4d4-4fb6-92e}"
NAMESPACE="${NAMESPACE:-cassellas-api}"
DEPLOYMENT="${DEPLOYMENT:-cassellas-api}"
CONTAINER_NAME="${CONTAINER_NAME:-cassellas-api}"
IMAGE_REPO="${IMAGE_REPO:-gcr.io/${PROJECT_ID}/cassellas-api}"
TAG="${TAG:-manual-$(date +%Y%m%d-%H%M%S)}"
API_URL="${API_URL:-http://api.cassellas.com.br}"
IMAGE="${IMAGE_REPO}:${TAG}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: command not found: $1" >&2
    exit 1
  fi
}

need_cmd docker
need_cmd gcloud
need_cmd kubectl
need_cmd curl

CURRENT_CONTEXT="$(kubectl config current-context)"
echo "Current kubectl context: ${CURRENT_CONTEXT}"

if [[ "${CURRENT_CONTEXT}" == "minikube" ]]; then
  echo "ERROR: current context is minikube. Switch to GKE before deploying." >&2
  exit 1
fi

if ! kubectl get ns "${NAMESPACE}" >/dev/null 2>&1; then
  echo "ERROR: namespace ${NAMESPACE} not found." >&2
  exit 1
fi

PREVIOUS_IMAGE="$(kubectl get deployment "${DEPLOYMENT}" -n "${NAMESPACE}" -o jsonpath='{.spec.template.spec.containers[0].image}')"

echo "Authenticating Docker for GCR..."
gcloud auth configure-docker --quiet

echo "Building image: ${IMAGE}"
docker build --no-cache -t "${IMAGE}" .

echo "Pushing image: ${IMAGE}"
docker push "${IMAGE}"

echo "Updating deployment ${DEPLOYMENT} in namespace ${NAMESPACE}"
kubectl set image deployment/"${DEPLOYMENT}" "${CONTAINER_NAME}"="${IMAGE}" -n "${NAMESPACE}"

echo "Waiting rollout..."
kubectl rollout status deployment/"${DEPLOYMENT}" -n "${NAMESPACE}" --timeout=420s

echo "Smoke test: ${API_URL}/healthz"
curl -fsS "${API_URL}/healthz" >/dev/null

echo
echo "Deploy finished successfully."
echo "New image: ${IMAGE}"
echo "Previous image: ${PREVIOUS_IMAGE}"
echo
echo "Rollback command (if needed):"
echo "kubectl set image deployment/${DEPLOYMENT} ${CONTAINER_NAME}=${PREVIOUS_IMAGE} -n ${NAMESPACE}"
