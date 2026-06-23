---
name: speckit-git-create-branch
description: Create a new feature branch from master as part of the Speckit workflow
user-invocable: true
---

## User Input

```text
$ARGUMENTS
```

Create a new feature branch from master. If a branch name is provided, use it directly. Otherwise, auto-generate from the next available feature number and the name provided.

Steps:
1. Determine branch name from arguments or auto-generate
2. `git fetch origin master`
3. `git checkout master && git pull origin master`
4. `git checkout -b <branch-name>`
5. Output the branch name for use by subsequent speckit commands
