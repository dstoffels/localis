param (
    [Parameter(Mandatory=$false)]
    [ValidateSet('major', 'minor', 'patch', 'revert')]
    [string]$versionPart
)

# REVERT MODE
if ($versionPart -eq 'revert') {
    Write-Host "Reverting last release..." -ForegroundColor Yellow
    
    # Get the current version tag
    $currentVersion = (poetry version -s).Trim()
    $tag = "v$currentVersion"
    
    Write-Host "Current version: $tag"
    
    # Delete GitHub release using gh CLI (if available)
    $ghInstalled = Get-Command gh -ErrorAction SilentlyContinue
    if ($ghInstalled) {
        Write-Host "Deleting GitHub release..."
        gh release delete $tag -y 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "GitHub release deleted" -ForegroundColor Green
        } else {
            Write-Host "GitHub release not found or already deleted" -ForegroundColor Yellow
        }
    } else {
        Write-Host "GitHub CLI not installed. Manually delete release at: https://github.com/dstoffels/localis/releases" -ForegroundColor Yellow
    }
    
    # Delete remote tag
    Write-Host "Deleting remote tag..."
    git push origin --delete $tag 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Remote tag deleted" -ForegroundColor Green
    } else {
        Write-Host "Remote tag not found or already deleted" -ForegroundColor Yellow
    }
    
    # Delete local tag
    Write-Host "Deleting local tag..."
    git tag -d $tag 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Local tag deleted" -ForegroundColor Green
    } else {
        Write-Host "Local tag not found or already deleted" -ForegroundColor Yellow
    }
    
    # Revert to previous commit
    Write-Host "Reverting last commit..."
    git reset --hard HEAD~1
    
    Write-Host "Revert complete!" -ForegroundColor Green
    exit 0
}

# Require version part for release mode
if (-not $versionPart) {
    Write-Error "Version part required. Usage: .\release.ps1 [major|minor|patch|revert]"
    exit 1
}

# RELEASE MODE
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

$tag = "v" + (poetry version -s).Trim()

if (-not $tag) {
    Write-Error "Could not retrieve the new version number from 'poetry version -s'."
    exit 1
}

$repoUrl = "https://github.com/dstoffels/localis"
$tsvUrl = "$repoUrl/releases/download/$tag/cities.tsv"

python -c @"
from localis.data import MetaStore
from localis import CityRegistry
meta = MetaStore()
meta.set(CityRegistry.META_URL_KEY, '$tsvUrl')
print(f'Updated TSV URL to: $tsvUrl')
"@

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to update database metadata."
    exit 1
}

Write-Host "Releasing $tag" -ForegroundColor Green

git add .\pyproject.toml .\src\localis\data\localis.db
git commit -m "Release $tag"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Git commit failed."
    exit 1
}

git tag -a "$tag" -m "Release $tag"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Git tag failed."
    exit 1
}

$confirm = Read-Host "Push $tag to origin/main? (y/n)"
if ($confirm -eq 'y') {
    git push origin main --tags
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Git push failed."
        exit 1
    }
    Write-Host "Release $tag pushed successfully!" -ForegroundColor Green
} else {
    Write-Host "Push cancelled. To push later: git push origin main --tags"
}