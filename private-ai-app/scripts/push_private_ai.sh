#!/usr/bin/env bash
set -euo pipefail

# Safe GitHub sync script for this project only (private-ai-app).
# It only stages/commits/pushes files under private-ai-app/.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(git -C "$PROJECT_DIR" rev-parse --show-toplevel)"
PROJECT_REL="${PROJECT_DIR#$REPO_ROOT/}"

DRY_RUN="false"
COMMIT_MESSAGE=""

usage() {
  cat <<EOF
Usage:
  $(basename "$0") [-m "commit message"] [--dry-run]

Options:
  -m, --message   Custom commit message
  --dry-run       Print what would happen without changing git state

Behavior:
  - Only stages and commits files under: ${PROJECT_REL}/
  - Refuses to run if staged files outside ${PROJECT_REL}/ already exist
  - Pushes current branch to origin
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--message)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] Missing value for $1" >&2
        exit 1
      fi
      COMMIT_MESSAGE="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[ERROR] Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

cd "$REPO_ROOT"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "[ERROR] Not inside a git repository." >&2
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "[ERROR] Git remote 'origin' is not configured." >&2
  exit 1
fi

if [[ -d .git/rebase-apply || -d .git/rebase-merge || -f .git/MERGE_HEAD || -f .git/CHERRY_PICK_HEAD ]]; then
  echo "[ERROR] Repository has an ongoing merge/rebase/cherry-pick. Resolve it first." >&2
  exit 1
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$CURRENT_BRANCH" == "HEAD" ]]; then
  echo "[ERROR] Detached HEAD is not supported by this script." >&2
  exit 1
fi

# Safety gate: if user already staged files outside private-ai-app, abort.
STAGED_OUTSIDE="$(git diff --cached --name-only -- . ":(exclude)${PROJECT_REL}")"
if [[ -n "$STAGED_OUTSIDE" ]]; then
  echo "[ERROR] Staged changes outside ${PROJECT_REL}/ detected. Abort to prevent accidental push." >&2
  echo "$STAGED_OUTSIDE" >&2
  exit 1
fi

PROJECT_CHANGES="$(git status --porcelain -- "${PROJECT_REL}")"
if [[ -z "$PROJECT_CHANGES" ]]; then
  echo "[INFO] No changes under ${PROJECT_REL}/. Nothing to commit."
  exit 0
fi

if [[ -z "$COMMIT_MESSAGE" ]]; then
  COMMIT_MESSAGE="chore(${PROJECT_REL}): sync updates $(date '+%Y-%m-%d %H:%M:%S')"
fi

echo "[INFO] Repo root: $REPO_ROOT"
echo "[INFO] Project scope: ${PROJECT_REL}/"
echo "[INFO] Branch: $CURRENT_BRANCH"

if [[ "$DRY_RUN" == "true" ]]; then
  echo "[DRY-RUN] Would stage:"
  git status --short -- "${PROJECT_REL}"
  echo "[DRY-RUN] Would commit message: $COMMIT_MESSAGE"
  echo "[DRY-RUN] Would push: origin $CURRENT_BRANCH"
  exit 0
fi

git add -- "${PROJECT_REL}"

# Double-check: after staging, only target path can be in index.
STAGED_AFTER_ADD="$(git diff --cached --name-only -- . ":(exclude)${PROJECT_REL}")"
if [[ -n "$STAGED_AFTER_ADD" ]]; then
  echo "[ERROR] Unexpected staged files outside ${PROJECT_REL}/ after git add. Abort." >&2
  echo "$STAGED_AFTER_ADD" >&2
  exit 1
fi

if git diff --cached --quiet; then
  echo "[INFO] Nothing staged for commit under ${PROJECT_REL}/."
  exit 0
fi

git commit -m "$COMMIT_MESSAGE"

if git rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
  git push origin "$CURRENT_BRANCH"
else
  git push -u origin "$CURRENT_BRANCH"
fi

echo "[OK] Pushed ${PROJECT_REL}/ changes to origin/${CURRENT_BRANCH}"
