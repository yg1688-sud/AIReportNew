# Speckit Git Extension: Commit and Push
# Called by after_implement or other post hooks

param(
    [string]$Message = "Auto-commit from Speckit",
    [switch]$Push = $true,
    [string]$Remote = "origin"
)

$ErrorActionPreference = "Stop"

Write-Host "Git Extension: Committing changes"

$branch = git rev-parse --abbrev-ref HEAD

git add -A

# Check if there are staged changes
$staged = git diff --cached --quiet 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Git Extension: No changes to commit"
    exit 0
}

git commit -m $Message

Write-Host "Git Extension: Committed on '$branch'"

if ($Push) {
    try {
        git push -u $Remote $branch
        Write-Host "Git Extension: Pushed '$branch' to $Remote"
    } catch {
        Write-Host "Git Extension: Push failed — check remote/network ($Remote)"
    }
}
