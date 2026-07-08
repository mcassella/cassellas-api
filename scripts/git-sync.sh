#!/usr/bin/env bash
set -euo pipefail

# Sync helper for GitHub workflow.
#
# Usage:
#   ./scripts/git-sync.sh push "chore: update api"
#   ./scripts/git-sync.sh pull
#   BRANCH=main ./scripts/git-sync.sh pull
#
# Behavior:
# - push: adds all changes, commits with provided message, then pushes to origin/<branch>
# - pull: fetches and rebases local branch on origin/<branch> using autostash

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: command not found: $1" >&2
    exit 1
  fi
}

need_cmd git

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: run this script inside a git repository." >&2
  exit 1
fi

MODE="${1:-}"
if [[ -z "${MODE}" ]]; then
  echo "Usage: ./scripts/git-sync.sh <push|pull> [commit-message]" >&2
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "ERROR: remote 'origin' is not configured." >&2
  exit 1
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
BRANCH="${BRANCH:-${CURRENT_BRANCH}}"

if [[ "${CURRENT_BRANCH}" != "${BRANCH}" ]]; then
  echo "Switching from ${CURRENT_BRANCH} to ${BRANCH}..."
  git checkout "${BRANCH}"
fi

case "${MODE}" in
  push)
    COMMIT_MSG="${2:-}"

    if [[ -z "${COMMIT_MSG}" ]]; then
      echo "ERROR: commit message is required for push mode." >&2
      echo "Example: ./scripts/git-sync.sh push \"chore: update api\"" >&2
      exit 1
    fi

    echo "Checking remote branch ${BRANCH}..."
    git fetch origin "${BRANCH}" || true

    echo "Staging local changes..."
    git add -A

    if git diff --cached --quiet; then
      echo "No staged changes to commit."
    else
      echo "Creating commit..."
      git commit -m "${COMMIT_MSG}"
    fi

    echo "Pushing to origin/${BRANCH}..."
    git push origin "${BRANCH}"

    echo "Done: local changes pushed to GitHub."
    ;;

  pull)
    echo "Fetching from origin..."
    git fetch origin

    echo "Rebasing ${BRANCH} onto origin/${BRANCH} (autostash enabled)..."
    git pull --rebase --autostash origin "${BRANCH}"

    echo "Done: local branch updated from GitHub."
    ;;

  *)
    echo "ERROR: invalid mode '${MODE}'. Use push or pull." >&2
    exit 1
    ;;
esac
