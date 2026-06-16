[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet(1, 2, 3, 4)]
    [int] $Slot,

    [Parameter(Mandatory = $true)]
    [string] $BePath,

    [string] $MigrationBePath,

    [string] $SourceServer = 'localhost',

    [int] $SourcePort = 1433,

    [string] $SourceDatabase = 'MyHospital',

    [string] $TargetDatabase = 'MyHospital',

    [string] $SqlUser = 'sa',

    [string] $SqlPassword = $(if ($env:MYHOSPITAL_SQL_PASSWORD) { $env:MYHOSPITAL_SQL_PASSWORD } else { 'Hospital123!' }),

    [string] $Python = 'python',

    [string] $BackupDir,

    [switch] $Yes
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_worktree-common.ps1')

$workspaceRoot = Get-WorkspaceRoot
$resolvedBePath = (Resolve-Path $BePath).Path
$migrationSourceInfo = Resolve-BeMigrationSource -WorkspaceRoot $workspaceRoot -BePath $resolvedBePath -PreferredPath $MigrationBePath
$resolvedMigrationBePath = $migrationSourceInfo.Path
$cfg = Get-WorktreeSlotConfig -Slot $Slot
$resolvedMigrationsPath = Get-BeMigrationsPath -BePath $resolvedMigrationBePath

Assert-SafeSqlName $SourceDatabase
Assert-SafeSqlName $TargetDatabase
Assert-CommandExists git
Assert-CommandExists docker
Assert-CommandExists dotnet
Assert-CommandExists $Python

if (-not (Test-Path $resolvedMigrationsPath)) {
    throw "Migration source does not contain MyHospital.ServiceInterface\Migrations: $resolvedMigrationBePath. Pass -MigrationBePath to a BE checkout that contains migrations."
}

if (-not $BackupDir) {
    $BackupDir = Join-Path $workspaceRoot 'worktrees\_db-backups'
}
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

if (-not $Yes) {
    Write-Host ""
    Write-Host "This will replace DB objects and data in slot $Slot ($($cfg.ContainerName), localhost,$($cfg.SqlPort)/$TargetDatabase)."
    Write-Host "Source data: $SourceServer,$SourcePort/$SourceDatabase"
    $confirm = Read-Host "Type 'yes' to continue"
    if ($confirm -ne 'yes') {
        Write-Host "Cancelled."
        exit 1
    }
}

& (Join-Path $PSScriptRoot 'init-db-slots.ps1') -Slots $Slot -SaPassword $SqlPassword
if ($LASTEXITCODE -ne 0) {
    throw "Failed to initialize DB slot $Slot."
}

Wait-SqlContainer -ContainerName $cfg.ContainerName -Password $SqlPassword

$createDbSql = "IF DB_ID(N'$TargetDatabase') IS NULL CREATE DATABASE [$TargetDatabase];"
Invoke-Checked docker @(
    'exec', $cfg.ContainerName,
    '/opt/mssql-tools18/bin/sqlcmd',
    '-S', 'localhost',
    '-U', $SqlUser,
    '-P', $SqlPassword,
    '-C',
    '-b',
    '-Q', $createDbSql
)

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupFile = Join-Path $BackupDir "backup-data-slot$Slot-$timestamp.sql"

Write-Host ""
Write-Host "Backing up source DB to $backupFile"
Invoke-WithEnvironment @{
    DB_SERVER   = $SourceServer
    DB_PORT     = $SourcePort
    DB_NAME     = $SourceDatabase
    DB_USER     = $SqlUser
    DB_PASSWORD = $SqlPassword
    OUTPUT_FILE = $backupFile
} {
    Invoke-Checked $Python @('Scripts/export_db_data.py') -WorkingDirectory $resolvedBePath
}

Write-Host ""
Write-Host "Clearing target DB objects in slot $Slot"
Invoke-WithEnvironment @{
    DB_SERVER   = 'localhost'
    DB_PORT     = $cfg.SqlPort
    DB_NAME     = $TargetDatabase
    DB_USER     = $SqlUser
    DB_PASSWORD = $SqlPassword
} {
    Invoke-Checked $Python @('Scripts/drop_db_objects.py') -WorkingDirectory $resolvedBePath
}

$targetConnectionString = Get-SqlConnectionString -Port $cfg.SqlPort -Database $TargetDatabase -User $SqlUser -Password $SqlPassword

Write-Host ""
Write-Host "Applying EF migrations to target DB"
if ($resolvedMigrationBePath -ne $resolvedBePath) {
    Write-Host "Migration source: $resolvedMigrationBePath"
}
Write-Host "Restoring .NET packages for migration source"
Invoke-Checked dotnet @('restore', 'MyHospital.sln') -WorkingDirectory $resolvedMigrationBePath
Invoke-WithEnvironment @{
    ASPNETCORE_ENVIRONMENT                 = 'Development'
    DOTNET_ENVIRONMENT                     = 'Development'
    ConnectionStrings__DefaultConnection   = $targetConnectionString
    ConnectionStrings__ReadOnlyConnection  = $targetConnectionString
} {
    Invoke-Checked dotnet @(
        'ef', 'database', 'update',
        '--connection', $targetConnectionString,
        '--project', 'MyHospital.ServiceInterface',
        '--startup-project', 'MyHospital'
    ) -WorkingDirectory $resolvedMigrationBePath
}

$tableCountSql = "SET NOCOUNT ON; SELECT COUNT(*) FROM sys.tables WHERE is_ms_shipped = 0 AND name <> N'__EFMigrationsHistory';"
$tableCountRaw = & docker @(
    'exec', $cfg.ContainerName,
    '/opt/mssql-tools18/bin/sqlcmd',
    '-S', 'localhost',
    '-U', $SqlUser,
    '-P', $SqlPassword,
    '-C',
    '-b',
    '-d', $TargetDatabase,
    '-h', '-1',
    '-W',
    '-Q', $tableCountSql
)
if ($LASTEXITCODE -ne 0) {
    throw "Failed to inspect target DB table count after EF migrations."
}

$tableCount = ($tableCountRaw | Where-Object { $_ -match '^\d+$' } | Select-Object -First 1)
if (-not $tableCount -or [int] $tableCount -le 0) {
    throw "EF migrations did not create any user tables in localhost,$($cfg.SqlPort)/$TargetDatabase. Use -MigrationBePath to point at a BE checkout that contains MyHospital.ServiceInterface\Migrations."
}

$backupTables = @(Get-BackupDataTables -BackupFile $backupFile)
if ($backupTables.Count -gt 0) {
    $clearFile = Join-Path $BackupDir "pre-import-clear-slot$Slot-$timestamp.sql"
    $clearLines = New-Object System.Collections.Generic.List[string]
    $clearLines.Add('SET QUOTED_IDENTIFIER ON;')
    $clearLines.Add('SET ANSI_NULLS ON;')
    $clearLines.Add('SET ANSI_WARNINGS ON;')
    $clearLines.Add('SET ANSI_PADDING ON;')
    $clearLines.Add('SET ARITHABORT ON;')
    $clearLines.Add('SET CONCAT_NULL_YIELDS_NULL ON;')
    $clearLines.Add('SET NUMERIC_ROUNDABORT OFF;')
    $clearLines.Add('SET NOCOUNT ON;')
    $clearLines.Add('SET XACT_ABORT ON;')
    $clearLines.Add("PRINT 'Disabling foreign key constraints before pre-import cleanup';")
    $clearLines.Add("DECLARE @fkSql NVARCHAR(MAX) = N'';")
    $clearLines.Add("SELECT @fkSql = @fkSql + N'ALTER TABLE '")
    $clearLines.Add("    + QUOTENAME(OBJECT_SCHEMA_NAME(parent_object_id)) + N'.' + QUOTENAME(OBJECT_NAME(parent_object_id))")
    $clearLines.Add("    + N' NOCHECK CONSTRAINT ' + QUOTENAME(name) + N';' + CHAR(10)")
    $clearLines.Add("FROM sys.foreign_keys;")
    $clearLines.Add("EXEC sp_executesql @fkSql;")
    $clearLines.Add('')
    $clearLines.Add("PRINT 'Clearing migration-seeded rows from tables present in source backup';")

    $seenTables = New-Object System.Collections.Generic.HashSet[string]
    for ($i = $backupTables.Count - 1; $i -ge 0; $i--) {
        $tableInfo = $backupTables[$i]
        $key = "$($tableInfo.Schema).$($tableInfo.Table)"
        if (-not $seenTables.Add($key)) {
            continue
        }

        $clearLines.Add("IF OBJECT_ID(N'$key', N'U') IS NOT NULL DELETE FROM [$($tableInfo.Schema)].[$($tableInfo.Table)];")
    }

    Write-Utf8NoBom -Path $clearFile -Lines $clearLines.ToArray()

    $containerClearFile = "/tmp/pre-import-clear-slot$Slot-$timestamp.sql"
    Write-Host ""
    Write-Host "Clearing migration-seeded rows before source data import"
    Invoke-Checked docker @('cp', $clearFile, "$($cfg.ContainerName):$containerClearFile")
    Invoke-Checked docker @(
        'exec', $cfg.ContainerName,
        '/opt/mssql-tools18/bin/sqlcmd',
        '-S', 'localhost',
        '-U', $SqlUser,
        '-P', $SqlPassword,
        '-C',
        '-b',
        '-d', $TargetDatabase,
        '-i', $containerClearFile
    )
    & docker 'exec' '-u' '0' $cfg.ContainerName 'rm' '-f' $containerClearFile *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Could not remove temporary SQL file inside $($cfg.ContainerName): $containerClearFile"
    }
}

Write-Host ""
Write-Host "Restoring source data into target DB"
Invoke-WithEnvironment @{
    DB_SERVER   = 'localhost'
    DB_PORT     = $cfg.SqlPort
    DB_NAME     = $TargetDatabase
    DB_USER     = $SqlUser
    DB_PASSWORD = $SqlPassword
} {
    Invoke-Checked $Python @('Scripts/import_db_data.py', $backupFile) -WorkingDirectory $resolvedBePath
}

Write-Host ""
Write-Host "DB sync complete."
Write-Host "Target: localhost,$($cfg.SqlPort)/$TargetDatabase"
Write-Host "Backup kept at: $backupFile"
