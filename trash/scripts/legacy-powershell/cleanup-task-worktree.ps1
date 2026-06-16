[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $Slug,

    [switch] $Yes
)

. (Join-Path $PSScriptRoot '_worktree-common.ps1')

$workspaceRoot = Get-WorkspaceRoot
$safeSlug = ConvertTo-WorktreeSlug -Slug $Slug
$taskRoot = Join-Path (Join-Path $workspaceRoot 'worktrees') $safeSlug
$feWorktree = Join-Path $taskRoot 'fe'
$beWorktree = Join-Path $taskRoot 'be'
$feRepo = Join-Path $workspaceRoot 'myhospital-fe'
$beRepo = Join-Path $workspaceRoot 'myhospital-be'

Assert-CommandExists git

if (-not (Test-Path $taskRoot)) {
    throw "Task worktree folder not found: $taskRoot"
}

$dirty = @()
foreach ($entry in @(
    @{ Label = 'FE'; Path = $feWorktree },
    @{ Label = 'BE'; Path = $beWorktree }
)) {
    if (-not (Test-Path $entry.Path)) {
        continue
    }

    $status = (& git -C $entry.Path status --short)
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to inspect $($entry.Label) worktree: $($entry.Path)"
    }

    if ($status) {
        $dirty += "$($entry.Label) tracked/untracked changes:`n$($status -join [Environment]::NewLine)"
    }
}

if ($dirty.Count -gt 0) {
    Write-Host "Refusing cleanup because worktree still has Git-visible changes."
    Write-Host ""
    Write-Host ($dirty -join "`n`n")
    exit 1
}

if (-not $Yes) {
    Write-Host ""
    Write-Host "This will remove worktree folders, including ignored local files such as .env, node_modules, bin, and obj."
    Write-Host "Target: $taskRoot"
    $confirm = Read-Host "Type 'yes' to continue"
    if ($confirm -ne 'yes') {
        Write-Host "Cancelled."
        exit 1
    }
}

if (Test-Path $feWorktree) {
    Invoke-Checked git @('-C', $feRepo, 'worktree', 'remove', '--force', $feWorktree)
}
if (Test-Path $beWorktree) {
    Invoke-Checked git @('-C', $beRepo, 'worktree', 'remove', '--force', $beWorktree)
}

Invoke-Checked git @('-C', $feRepo, 'worktree', 'prune')
Invoke-Checked git @('-C', $beRepo, 'worktree', 'prune')

if (Test-Path $taskRoot) {
    $remaining = Get-ChildItem -Force $taskRoot -ErrorAction SilentlyContinue
    if (-not $remaining) {
        Remove-Item -LiteralPath $taskRoot -Force
    }
    else {
        Write-Warning "Task root still contains non-worktree artifacts: $taskRoot"
    }
}

Write-Host "Cleanup complete for '$safeSlug'."
