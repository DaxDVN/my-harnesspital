# Sync main FE/BE branches with upstream and re-apply local skip-worktree config.
#
# Flow for each repo:
#   1. Detect all skip-worktree files (S-flag from git ls-files -v)
#   2. Remove skip-worktree so git can see the local modifications
#   3. Restore (revert) all dirty tracked files back to HEAD
#   4. Pull latest from origin
#   5. Find the stash named "pre-config-before-dev" and apply it
#   6. Re-apply skip-worktree to every file the stash touched
#
# Prerequisites: the stash "pre-config-before-dev" must exist in both repos.
# Create/update it with: git stash push -m "pre-config-before-dev" -- <files...>
# The stash is NOT popped — it stays for future syncs.
#
# Usage:
#   .\scripts\sync-main-branches.ps1
#   .\scripts\sync-main-branches.ps1 -Yes          # skip confirmation prompt

[CmdletBinding()]
param(
    [switch] $Yes
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '_worktree-common.ps1')

$workspaceRoot = Get-WorkspaceRoot

$repos = @(
    [pscustomobject]@{ Path = Join-Path $workspaceRoot 'myhospital-fe'; Branch = 'master'; Label = 'FE' },
    [pscustomobject]@{ Path = Join-Path $workspaceRoot 'myhospital-be'; Branch = 'main';   Label = 'BE' }
)

if (-not $Yes) {
    Write-Host ""
    Write-Host "This will pull latest from origin for BOTH main repos and re-apply the"
    Write-Host "'pre-config-before-dev' stash. All un-stashed local changes will be lost."
    Write-Host ""
    Write-Host "Repos:"
    foreach ($r in $repos) { Write-Host "  $($r.Label): $($r.Path) ($($r.Branch))" }
    Write-Host ""
    $confirm = Read-Host "Type 'yes' to continue"
    if ($confirm -ne 'yes') {
        Write-Host "Cancelled."
        exit 1
    }
}

foreach ($repo in $repos) {
    Write-Host ""
    Write-Host "========================================"
    Write-Host "  $($repo.Label)  ($($repo.Branch))"
    Write-Host "========================================"

    # --- Step 1: detect current skip-worktree files ---
    $rawLines = & git -C $repo.Path ls-files -v 2>$null
    $skipFiles = $rawLines |
        Where-Object { $_ -match '^S ' } |
        ForEach-Object { $_.Substring(2).Trim() } |
        Where-Object { $_ -ne '' }

    if ($skipFiles) {
        Write-Host "Detected skip-worktree files: $($skipFiles -join ', ')"
    }
    else {
        Write-Host "No skip-worktree files detected."
    }

    # --- Step 2: remove skip-worktree so git sees the modifications ---
    foreach ($f in $skipFiles) {
        Invoke-Checked git @('-C', $repo.Path, 'update-index', '--no-skip-worktree', $f)
    }

    # --- Step 3: revert all dirty tracked files to HEAD ---
    Write-Host "Reverting dirty tracked files..."
    Invoke-Checked git @('-C', $repo.Path, 'restore', '.')

    # --- Step 4: pull latest from origin ---
    Write-Host "Pulling origin/$($repo.Branch)..."
    Invoke-Checked git @('-C', $repo.Path, 'pull', 'origin', $repo.Branch)

    # --- Step 5: find the pre-config stash ---
    $stashList = & git -C $repo.Path stash list 2>$null
    $stashRef  = $null

    foreach ($line in $stashList) {
        if ($line -match 'pre-config-before-dev') {
            if ($line -match '^(stash@\{\d+\})') {
                $stashRef = $Matches[1]
            }
            break
        }
    }

    if (-not $stashRef) {
        Write-Warning "$($repo.Label): No stash named 'pre-config-before-dev' found."
        Write-Warning "  Create it with: git -C $($repo.Path) stash push -m 'pre-config-before-dev' -- <files>"
        Write-Warning "  skip-worktree will NOT be re-applied for $($repo.Label)."
        continue
    }

    Write-Host "Found stash: $stashRef"

    # Get the list of files the stash touches (so we know what to skip-worktree after apply)
    $stashFiles = & git -C $repo.Path stash show $stashRef --name-only 2>$null |
        Where-Object { $_ -match '\S' }

    # --- Apply the stash (keep it in the list for future syncs) ---
    Write-Host "Applying $stashRef..."
    & git -C $repo.Path stash apply $stashRef 2>&1 | ForEach-Object { Write-Host "  $_" }

    if ($LASTEXITCODE -ne 0) {
        Write-Warning "$($repo.Label): 'git stash apply' exited with code $LASTEXITCODE."
        Write-Warning "Resolve any conflicts, then manually re-apply skip-worktree:"
        foreach ($f in $stashFiles) {
            Write-Warning "  git -C `"$($repo.Path)`" update-index --skip-worktree $f"
        }
        continue
    }

    # --- Step 6: re-apply skip-worktree to all stash files ---
    Write-Host "Re-applying skip-worktree..."
    foreach ($f in $stashFiles) {
        Invoke-Checked git @('-C', $repo.Path, 'update-index', '--skip-worktree', $f)
        Write-Host "  skip-worktree: $f"
    }

    Write-Host "$($repo.Label) sync complete."
}

Write-Host ""
Write-Host "Done. Both main repos are up to date with local config preserved."
