# Speckit Git Extension: Create Feature Branch
# Called by before_specify hook

param(
    [string]$FeatureName,
    [string]$FeatureNum,
    [string]$BranchName,
    [string]$BaseBranch = "master"
)

$ErrorActionPreference = "Stop"

# Resolve branch name
if ($BranchName) {
    $branch = $BranchName
} elseif ($FeatureNum -and $FeatureName) {
    $branch = "$FeatureNum-$FeatureName"
} elseif ($FeatureName) {
    $branch = $FeatureName
} else {
    Write-Error "Cannot determine branch name: provide BranchName or FeatureNum+FeatureName"
    exit 1
}

Write-Host "Git Extension: Creating branch '$branch' from '$BaseBranch'"

# Ensure on base branch and up to date
git fetch origin $BaseBranch 2>$null
git checkout $BaseBranch
git pull origin $BaseBranch 2>$null

# Create and switch
git checkout -b $branch

Write-Host "Git Extension: Switched to branch '$branch'"

# Output for the calling command
$output = @{
    BRANCH_NAME = $branch
    FEATURE_NUM = $FeatureNum
} | ConvertTo-Json -Compress

Write-Output $output
