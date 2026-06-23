#!/bin/bash
# Speckit Git Extension: Create Feature Branch

set -e

FEATURE_NAME="${1:-}"
FEATURE_NUM="${2:-}"
BRANCH_NAME="${3:-}"
BASE_BRANCH="${4:-master}"

if [ -n "$BRANCH_NAME" ]; then
    branch="$BRANCH_NAME"
elif [ -n "$FEATURE_NUM" ] && [ -n "$FEATURE_NAME" ]; then
    branch="${FEATURE_NUM}-${FEATURE_NAME}"
elif [ -n "$FEATURE_NAME" ]; then
    branch="$FEATURE_NAME"
else
    echo "Error: Cannot determine branch name"
    exit 1
fi

echo "Git Extension: Creating branch '$branch' from '$BASE_BRANCH'"

git fetch origin "$BASE_BRANCH" 2>/dev/null || true
git checkout "$BASE_BRANCH"
git pull origin "$BASE_BRANCH" 2>/dev/null || true
git checkout -b "$branch"

echo "Git Extension: Switched to branch '$branch'"

echo "{\"BRANCH_NAME\": \"$branch\", \"FEATURE_NUM\": \"$FEATURE_NUM\"}"
