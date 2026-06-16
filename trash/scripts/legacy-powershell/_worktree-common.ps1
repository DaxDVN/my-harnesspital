Set-StrictMode -Version Latest

function Get-WorkspaceRoot {
    $scriptDir = $PSScriptRoot
    if (-not $scriptDir -and $MyInvocation.ScriptName) {
        $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    }
    return (Resolve-Path (Join-Path $scriptDir '..')).Path
}

function Get-WorktreeSlotConfig {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet(1, 2, 3, 4)]
        [int] $Slot
    )

    [pscustomobject]@{
        Slot          = $Slot
        FePort        = 3000 + $Slot
        BePort        = 5000 + $Slot
        SqlPort       = 1433 + $Slot
        ContainerName = "mssql-hospital-wt$Slot"
        VolumeName    = "myhospital-mssql-wt$Slot"
        DatabaseName  = 'MyHospital'
    }
}

function ConvertTo-WorktreeSlug {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Slug
    )

    $value = $Slug.Trim().ToLowerInvariant()
    $value = $value -replace '[^a-z0-9._-]+', '-'
    $value = $value -replace '-{2,}', '-'
    $value = $value.Trim('-')

    if (-not $value) {
        throw "Slug '$Slug' does not contain a usable branch/path name."
    }

    return $value
}

function Assert-CommandExists {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Command
    )

    if (-not (Get-Command $Command -ErrorAction SilentlyContinue)) {
        throw "Required command '$Command' was not found on PATH."
    }
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string] $FilePath,

        [string[]] $Arguments = @(),

        [string] $WorkingDirectory
    )

    $display = @($FilePath) + $Arguments
    Write-Host "> $($display -join ' ')"

    if ($WorkingDirectory) {
        Push-Location $WorkingDirectory
    }

    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed with exit code $LASTEXITCODE`: $($display -join ' ')"
        }
    }
    finally {
        if ($WorkingDirectory) {
            Pop-Location
        }
    }
}

function Invoke-WithEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable] $Variables,

        [Parameter(Mandatory = $true)]
        [scriptblock] $ScriptBlock
    )

    $oldValues = @{}
    foreach ($key in $Variables.Keys) {
        $oldValues[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, [string] $Variables[$key], 'Process')
    }

    try {
        & $ScriptBlock
    }
    finally {
        foreach ($key in $Variables.Keys) {
            [Environment]::SetEnvironmentVariable($key, $oldValues[$key], 'Process')
        }
    }
}

function Set-EnvLine {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [AllowEmptyString()]
        [string[]] $Lines,

        [Parameter(Mandatory = $true)]
        [string] $Name,

        [Parameter(Mandatory = $true)]
        [string] $Value
    )

    $pattern = "^\s*$([regex]::Escape($Name))="
    $updated = New-Object System.Collections.Generic.List[string]
    $found = $false

    foreach ($line in $Lines) {
        if ($line -match $pattern) {
            $updated.Add("$Name=$Value")
            $found = $true
        }
        else {
            $updated.Add($line)
        }
    }

    if (-not $found) {
        $updated.Add("$Name=$Value")
    }

    return $updated.ToArray()
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path,

        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [AllowEmptyString()]
        [string[]] $Lines
    )

    [System.IO.File]::WriteAllLines($Path, $Lines, [System.Text.UTF8Encoding]::new($false))
}

function Get-BeMigrationsPath {
    param(
        [Parameter(Mandatory = $true)]
        [string] $BePath
    )

    return (Join-Path $BePath 'MyHospital.ServiceInterface\Migrations')
}

function Get-MigrationFolderStamp {
    param(
        [Parameter(Mandatory = $true)]
        [string] $MigrationsPath
    )

    $latestFile = Get-ChildItem -Path $MigrationsPath -File -Filter '*.cs' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1

    if ($latestFile) {
        return $latestFile.LastWriteTimeUtc
    }

    return (Get-Item $MigrationsPath).LastWriteTimeUtc
}

function Resolve-BeMigrationSource {
    param(
        [Parameter(Mandatory = $true)]
        [string] $WorkspaceRoot,

        [string] $BePath,

        [string] $PreferredPath
    )

    $candidates = New-Object System.Collections.Generic.List[object]
    $seen = New-Object System.Collections.Generic.HashSet[string]

    function Add-Candidate {
        param(
            [string] $Path,
            [string] $Label
        )

        if (-not $Path) {
            return
        }

        $resolved = $null
        try {
            $resolved = (Resolve-Path $Path -ErrorAction Stop).Path
        }
        catch {
            return
        }

        if (-not $seen.Add($resolved)) {
            return
        }

        $migrationsPath = Get-BeMigrationsPath -BePath $resolved
        if (Test-Path $migrationsPath) {
            $candidates.Add([pscustomobject]@{
                Path           = $resolved
                MigrationsPath = $migrationsPath
                Label          = $Label
                Stamp          = Get-MigrationFolderStamp -MigrationsPath $migrationsPath
            })
        }
    }

    if ($PreferredPath) {
        Add-Candidate -Path $PreferredPath -Label 'preferred'
        if ($candidates.Count -eq 0) {
            throw "Migration source does not contain MyHospital.ServiceInterface\Migrations: $PreferredPath"
        }
        return ($candidates | Select-Object -First 1)
    }

    Add-Candidate -Path $BePath -Label 'current BE'
    Add-Candidate -Path (Join-Path $WorkspaceRoot 'myhospital-be') -Label 'main BE'

    $worktreesRoot = Join-Path $WorkspaceRoot 'worktrees'
    if (Test-Path $worktreesRoot) {
        Get-ChildItem -Path $worktreesRoot -Directory |
            Where-Object { $_.Name -ne '_db-backups' } |
            ForEach-Object {
                Add-Candidate -Path (Join-Path $_.FullName 'be') -Label "worktree/$($_.Name)"
            }
    }

    if ($candidates.Count -eq 0) {
        throw "No BE migrations folder found. Expected MyHospital.ServiceInterface\Migrations in myhospital-be or an existing worktree."
    }

    return ($candidates | Sort-Object Stamp -Descending | Select-Object -First 1)
}

function Add-GitInfoExclude {
    param(
        [Parameter(Mandatory = $true)]
        [string] $RepoPath,

        [Parameter(Mandatory = $true)]
        [string] $Pattern
    )

    $excludePath = & git -C $RepoPath rev-parse --git-path info/exclude 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $excludePath) {
        Write-Warning "Could not resolve git info/exclude for $RepoPath"
        return
    }

    $excludeDir = Split-Path -Parent $excludePath
    New-Item -ItemType Directory -Force -Path $excludeDir | Out-Null

    $existing = if (Test-Path $excludePath) { @(Get-Content $excludePath) } else { @() }
    if ($existing -notcontains $Pattern) {
        $updated = @($existing) + $Pattern
        Write-Utf8NoBom -Path $excludePath -Lines $updated
    }
}

function Get-BackupDataTables {
    param(
        [Parameter(Mandatory = $true)]
        [string] $BackupFile
    )

    $tables = New-Object System.Collections.Generic.List[object]

    foreach ($line in Get-Content $BackupFile) {
        if ($line -match '^--\s*=+\s*([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\s*\((\d+)\s*rows\)') {
            $tables.Add([pscustomobject]@{
                Schema = $Matches[1]
                Table  = $Matches[2]
                Rows   = [int] $Matches[3]
            })
        }
    }

    return $tables
}

function Get-SqlConnectionString {
    param(
        [Parameter(Mandatory = $true)]
        [int] $Port,

        [string] $Database = 'MyHospital',

        [string] $User = 'sa',

        [string] $Password = 'Hospital123!'
    )

    return "Server=localhost,$Port;Initial Catalog=$Database;User ID=$User;Password=$Password;MultipleActiveResultSets=False;Encrypt=False;TrustServerCertificate=True;Connection Timeout=30;"
}

function Test-PortListening {
    param(
        [Parameter(Mandatory = $true)]
        [int] $Port
    )

    try {
        $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        return [bool] $connection
    }
    catch {
        return $false
    }
}

function Wait-SqlContainer {
    param(
        [Parameter(Mandatory = $true)]
        [string] $ContainerName,

        [Parameter(Mandatory = $true)]
        [string] $Password,

        [int] $TimeoutSeconds = 120
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $args = @(
        'exec', $ContainerName,
        '/opt/mssql-tools18/bin/sqlcmd',
        '-S', 'localhost',
        '-U', 'sa',
        '-P', $Password,
        '-C',
        '-b',
        '-Q', 'SELECT 1'
    )

    while ((Get-Date) -lt $deadline) {
        & docker @args *> $null
        if ($LASTEXITCODE -eq 0) {
            return
        }

        Start-Sleep -Seconds 3
    }

    throw "SQL Server container '$ContainerName' did not become ready within $TimeoutSeconds seconds."
}

function Assert-SafeSqlName {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Name
    )

    if ($Name -notmatch '^[A-Za-z0-9_]+$') {
        throw "Unsafe SQL identifier '$Name'. Use letters, numbers, and underscores only."
    }
}

function Remove-TelerikFromSolution {
    param(
        [Parameter(Mandatory = $true)]
        [string] $BePath
    )

    $slnFile = Get-ChildItem -Path $BePath -Filter '*.sln' -File | Select-Object -First 1
    if (-not $slnFile) {
        Write-Warning "No .sln file found in $BePath — skipping Telerik removal."
        return
    }

    $slnContent = Get-Content $slnFile.FullName -Raw
    $regex = [regex]'Project\("[^"]+"\)\s*=\s*"[^"]*",\s*"([^"]*[Tt]elerik[^"]*\.csproj)"'
    $matches = $regex.Matches($slnContent)

    if ($matches.Count -eq 0) {
        Write-Host "No Telerik projects found in $($slnFile.Name) — nothing to remove."
        return
    }

    foreach ($m in $matches) {
        $projRelPath = $m.Groups[1].Value
        Write-Host "Removing Telerik project: $projRelPath"
        & dotnet sln $slnFile.FullName remove $projRelPath
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "dotnet sln remove failed for '$projRelPath' — build may still fail."
        }
    }

    Write-Host "Telerik removal done."
}
