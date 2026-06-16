[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $Slug,

    [Parameter(Mandatory = $true)]
    [ValidateSet(1, 2, 3, 4)]
    [int] $Slot,

    [string] $FeBase = 'master',

    [string] $BeBase = 'main',

    [string] $FeBranch,

    [string] $BeBranch,

    [string] $MigrationBePath,

    [string] $SqlPassword = $(if ($env:MYHOSPITAL_SQL_PASSWORD) { $env:MYHOSPITAL_SQL_PASSWORD } else { 'Hospital123!' }),

    [switch] $SkipDbSync,

    [switch] $SkipFeInstall,

    [switch] $AllowPortInUse
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_worktree-common.ps1')

$workspaceRoot = Get-WorkspaceRoot
$safeSlug = ConvertTo-WorktreeSlug -Slug $Slug
$cfg = Get-WorktreeSlotConfig -Slot $Slot

$feRepo = Join-Path $workspaceRoot 'myhospital-fe'
$beRepo = Join-Path $workspaceRoot 'myhospital-be'
$taskRoot = Join-Path (Join-Path $workspaceRoot 'worktrees') $safeSlug
$feWorktree = Join-Path $taskRoot 'fe'
$beWorktree = Join-Path $taskRoot 'be'
$migrationSourceInfo = $null

if (-not $FeBranch) {
    $FeBranch = "feature/$safeSlug"
}
if (-not $BeBranch) {
    $BeBranch = "feature/$safeSlug"
}

Assert-CommandExists git
if (-not $SkipFeInstall) {
    Assert-CommandExists npm
}

if (-not (Test-Path $feRepo)) {
    throw "FE repo not found: $feRepo"
}
if (-not (Test-Path $beRepo)) {
    throw "BE repo not found: $beRepo"
}
if (Test-Path $taskRoot) {
    throw "Task worktree folder already exists: $taskRoot"
}
if (-not $SkipDbSync -or $MigrationBePath) {
    $migrationSourceInfo = Resolve-BeMigrationSource -WorkspaceRoot $workspaceRoot -PreferredPath $MigrationBePath
    Write-Host "Using migration source: $($migrationSourceInfo.Path) ($($migrationSourceInfo.Label))"
}

foreach ($check in @(
    @{ Repo = $feRepo; Ref = $FeBase; Label = 'FE base' },
    @{ Repo = $beRepo; Ref = $BeBase; Label = 'BE base' }
)) {
    & git -C $check.Repo rev-parse --verify "$($check.Ref)^{commit}" *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "$($check.Label) ref '$($check.Ref)' was not found in $($check.Repo)."
    }
}

foreach ($check in @(
    @{ Repo = $feRepo; Branch = $FeBranch; Label = 'FE branch' },
    @{ Repo = $beRepo; Branch = $BeBranch; Label = 'BE branch' }
)) {
    & git -C $check.Repo show-ref --verify "refs/heads/$($check.Branch)" *> $null
    if ($LASTEXITCODE -eq 0) {
        throw "$($check.Label) '$($check.Branch)' already exists. Choose another slug or branch."
    }
}

if (-not $AllowPortInUse) {
    foreach ($port in @($cfg.FePort, $cfg.BePort)) {
        if (Test-PortListening -Port $port) {
            throw "Port $port is already listening. Stop that process, choose another slot, or pass -AllowPortInUse."
        }
    }
}

Write-Host "Fetching latest $FeBase from origin (FE)..."
$feSourceRef = "refs/remotes/origin/$FeBase"
Invoke-Checked git @('-C', $feRepo, 'fetch', 'origin', "+refs/heads/$($FeBase):$feSourceRef")

Write-Host "Fetching latest $BeBase from origin (BE)..."
$beSourceRef = "refs/remotes/origin/$BeBase"
Invoke-Checked git @('-C', $beRepo, 'fetch', 'origin', "+refs/heads/$($BeBase):$beSourceRef")

New-Item -ItemType Directory -Force -Path $taskRoot | Out-Null

Invoke-Checked git @('-C', $feRepo, 'worktree', 'add', '-b', $FeBranch, $feWorktree, $feSourceRef)
Invoke-Checked git @('-C', $beRepo, 'worktree', 'add', '-b', $BeBranch, $beWorktree, $beSourceRef)

Remove-TelerikFromSolution -BePath $beWorktree

$feTemplate = Join-Path $feRepo '.env'
if (-not (Test-Path $feTemplate)) {
    $feTemplate = Join-Path $feRepo 'env'
}
$feEnvLines = if (Test-Path $feTemplate) { @(Get-Content $feTemplate) } else { @() }
$feEnvLines = Set-EnvLine -Lines $feEnvLines -Name 'VITE_DEV_PORT' -Value $cfg.FePort
$feEnvLines = Set-EnvLine -Lines $feEnvLines -Name 'VITE_BACKEND_URL' -Value "http://localhost:$($cfg.BePort)"
$feEnvLines = Set-EnvLine -Lines $feEnvLines -Name 'VITE_INDEXEDDB_VERSION' -Value (100 + $Slot)
$feEnvLines = Set-EnvLine -Lines $feEnvLines -Name 'VITE_DEV_PERSIST_ALL' -Value 'true'
Write-Utf8NoBom -Path (Join-Path $feWorktree '.env') -Lines $feEnvLines

$beTemplate = Join-Path $beRepo '.env'
$beEnvLines = if (Test-Path $beTemplate) { @(Get-Content $beTemplate) } else { @() }
$targetConnectionString = Get-SqlConnectionString -Port $cfg.SqlPort -Database $cfg.DatabaseName -Password $SqlPassword
$corsOrigins = @(
    'http://localhost:5173',
    'http://localhost:3000',
    'http://localhost:3001',
    'http://localhost:3002',
    'http://localhost:3003',
    'http://localhost:3004',
    'http://localhost:5000',
    'http://localhost:5001',
    'http://localhost:5002',
    'http://localhost:5003',
    'http://localhost:5004'
) -join ','

$beEnvLines = Set-EnvLine -Lines $beEnvLines -Name 'ASPNETCORE_ENVIRONMENT' -Value 'Development'
$beEnvLines = Set-EnvLine -Lines $beEnvLines -Name 'ASPNETCORE_URLS' -Value "http://localhost:$($cfg.BePort)"
$beEnvLines = Set-EnvLine -Lines $beEnvLines -Name 'ConnectionStrings__DefaultConnection' -Value $targetConnectionString
$beEnvLines = Set-EnvLine -Lines $beEnvLines -Name 'ConnectionStrings__ReadOnlyConnection' -Value $targetConnectionString
$beEnvLines = Set-EnvLine -Lines $beEnvLines -Name 'CORS_ORIGINS' -Value $corsOrigins
Write-Utf8NoBom -Path (Join-Path $beWorktree '.env') -Lines $beEnvLines

foreach ($relativePath in @('MyHospital\LocalBootstrap.cs', 'nuget.config')) {
    $source = Join-Path $beRepo $relativePath
    if (Test-Path $source) {
        $target = Join-Path $beWorktree $relativePath
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
        Copy-Item -Path $source -Destination $target -Force
    }
    else {
        Write-Warning "Local-only file not found in main BE repo: $relativePath"
    }
}

# Migrations are local-only in this workspace. When the current checkout does
# not have them, DB sync will use the resolved source path directly so the EF
# model and migration snapshot stay paired.
if ($migrationSourceInfo) {
    Write-Host "DB sync migration source: $($migrationSourceInfo.Path)"
}

# Copy skip-worktree local-config files from main repos into the new worktrees.
# These files are tracked in git but have local OS-specific modifications that must not
# be committed (the original dev used a different OS). Git worktree add checks out the
# committed version; this block replaces them with the locally-modified version and
# re-applies skip-worktree so the worktree behaves identically to the main checkout.
Write-Host ""
Write-Host "Copying skip-worktree local-config files..."
foreach ($pair in @(
    @{ Repo = $feRepo; Worktree = $feWorktree; Label = 'FE' },
    @{ Repo = $beRepo; Worktree = $beWorktree; Label = 'BE' }
)) {
    $rawLines = & git -C $pair.Repo ls-files -v 2>$null
    $skipFiles = $rawLines |
        Where-Object { $_ -match '^S ' } |
        ForEach-Object { $_.Substring(2).Trim() }

    if (-not $skipFiles) {
        Write-Host "  $($pair.Label): no skip-worktree files detected."
        continue
    }

    foreach ($relPath in $skipFiles) {
        $src = Join-Path $pair.Repo $relPath
        $dst = Join-Path $pair.Worktree $relPath
        if (Test-Path $src) {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
            Copy-Item -Path $src -Destination $dst -Force
            Invoke-Checked git @('-C', $pair.Worktree, 'update-index', '--skip-worktree', $relPath)
            Write-Host "  $($pair.Label) skip-worktree copied: $relPath"
        }
        else {
            Write-Warning "  $($pair.Label): skip-worktree source not found in main repo: $relPath"
        }
    }
}

if (-not $SkipFeInstall) {
    Write-Host ""
    Write-Host "Installing FE dependencies..."

    if (Test-Path (Join-Path $feWorktree 'package-lock.json')) {
        Invoke-Checked npm @('ci', '--no-audit', '--fund=false') -WorkingDirectory $feWorktree
    }
    else {
        Invoke-Checked npm @('install', '--no-audit', '--fund=false') -WorkingDirectory $feWorktree
    }
}
else {
    Write-Host ""
    Write-Host "Skipping FE dependency install because -SkipFeInstall was passed."
}

if (-not $SkipDbSync) {
    $dbSyncArgs = @{
        Slot        = $Slot
        BePath      = $beWorktree
        SqlPassword = $SqlPassword
        Yes         = $true
    }
    if ($migrationSourceInfo -and $migrationSourceInfo.Path -ne $beWorktree) {
        $dbSyncArgs.MigrationBePath = $migrationSourceInfo.Path
    }

    & (Join-Path $PSScriptRoot 'sync-worktree-db.ps1') @dbSyncArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Worktree was created, but DB sync failed. Inspect: $taskRoot"
    }
}
else {
    & (Join-Path $PSScriptRoot 'init-db-slots.ps1') -Slots $Slot -SaPassword $SqlPassword
    if ($LASTEXITCODE -ne 0) {
        throw "Worktree was created, but DB slot initialization failed. Inspect: $taskRoot"
    }
}

Write-Host ""
Write-Host "Worktree ready: $taskRoot"
Write-Host "FE: $feWorktree"
Write-Host "BE: $beWorktree"
Write-Host ""
Write-Host "Run BE:"
Write-Host "  cd $beWorktree"
Write-Host "  dotnet run --project MyHospital --no-launch-profile"
Write-Host ""
Write-Host "Run FE:"
Write-Host "  cd $feWorktree"
if ($SkipFeInstall) {
    Write-Host "  npm install"
}
else {
    Write-Host "  # FE dependencies were installed by this script"
}
Write-Host "  npm run dtos:update"
Write-Host "  npm run client:generate"
Write-Host "  npm run dev"
Write-Host ""
Write-Host "URLs: FE http://localhost:$($cfg.FePort), BE http://localhost:$($cfg.BePort), DB localhost,$($cfg.SqlPort)/$($cfg.DatabaseName)"
