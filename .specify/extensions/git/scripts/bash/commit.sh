#!/bin/bash
# Speckit Git Extension: Commit and Push

set -e

MESSAGE="${1:-Auto-commit from Speckit}"
PUSH="${2:-true}"
REMOTE="${3:-origin}"

echo "Git Extension: Committing changes"

branch=$(git rev-parse --abbrev-ref HEAD)
git add -A

if git diff --cached --quiet 2>/dev/null; then
    echo "Git Extension: No changes to commit"
    exit 0
fi

git commit -m "$MESSAGE"
echo "Git Extension: Committed on '$branch'"

if [ "$PUSH" = "true" ]; then
    git push -u "$REMOTE" "$branch" 2>/dev/null || echo "Git Extension: Push failed — check remote/network"
fi
