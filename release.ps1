param (
    [Parameter(Mandatory=$true)]
    [ValidateSet('major', 'minor', 'patch')]
    [string]$versionPart
)

$currentBranch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($currentBranch -ne "main") {
    Write-Error "Must be on main branch to release. Currently on: $currentBranch"
    exit 1
}

$status = git status --porcelain
if ($status) {
    Write-Error "You have uncommitted changes. Commit or stash them first."
    exit 1  
}

try {
    poetry version $versionPart
} catch {
    Write-Error "Poetry version bump failed."
    exit 1
}

$newVersion = (poetry version -s).Trim()

if (-not $newVersion) {
    Write-Error "Could not retrieve the new version number from 'poetry version -s'."
    exit 1
}

Write-Host "Releasing v$newVersion" -ForegroundColor Green

git add .\pyproject.toml
git commit -m "Bump to v$newVersion"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Git commit failed."
    exit 1
}

git tag -a "v$newVersion" -m "Release v$newVersion"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Git tag failed."
    exit 1
}
$confirm = Read-Host "Push v$newVersion to origin/main? (y/n)"
if ($confirm -eq 'y') {
    git push origin main --tags
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Git push failed."
        exit 1
    }
    Write-Host "Release v$newVersion pushed successfully!" -ForegroundColor Green
} else {
    Write-Host "Push cancelled. To push later: git push origin main --tags"
}
