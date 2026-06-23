---
name: speckit-git-commit
description: Stage all changes, commit with a structured message, and optionally push
user-invocable: true
---

## User Input

```text
$ARGUMENTS
```

Stage all changes (`git add -A`), create a commit with the provided message (or auto-generate one from the recent changes), and push to the remote.

Steps:
1. Check current branch and working tree status
2. `git add -A`
3. Generate commit message from arguments or diff summary
4. `git commit -m "<message>"`
5. `git push -u origin <branch>` (with proxy bypass if needed)
