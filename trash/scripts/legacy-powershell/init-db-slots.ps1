[CmdletBinding()]
param(
    [ValidateSet(1, 2, 3, 4)]
    [int[]] $Slots = @(1, 2, 3),

    [string] $Image = 'mcr.microsoft.com/mssql/server:2022-latest',

    [string] $SaPassword = $(if ($env:MYHOSPITAL_SQL_PASSWORD) { $env:MYHOSPITAL_SQL_PASSWORD } else { 'Hospital123!' }),

    [switch] $Pull
)

. (Join-Path $PSScriptRoot '_worktree-common.ps1')

Assert-CommandExists docker

if ($Pull) {
    Invoke-Checked docker @('pull', $Image)
}

foreach ($slot in $Slots) {
    $cfg = Get-WorktreeSlotConfig -Slot $slot
    Write-Host ""
    Write-Host "== Slot ${slot}: $($cfg.ContainerName) localhost:$($cfg.SqlPort) =="

    $containerId = (& docker ps -aq --filter "name=^$($cfg.ContainerName)$")
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to inspect Docker containers."
    }

    if ($containerId) {
        $runningId = (& docker ps -q --filter "name=^$($cfg.ContainerName)$")
        if ($runningId) {
            Write-Host "Container already running."
        }
        else {
            Invoke-Checked docker @('start', $cfg.ContainerName)
        }
    }
    else {
        $runArgs = @(
            'run', '-d',
            '--name', $cfg.ContainerName,
            '-e', 'ACCEPT_EULA=Y',
            '-e', "MSSQL_SA_PASSWORD=$SaPassword",
            '-e', 'MSSQL_PID=Developer',
            '-p', "$($cfg.SqlPort):1433",
            '-v', "$($cfg.VolumeName):/var/opt/mssql",
            $Image
        )
        Invoke-Checked docker $runArgs
    }

    Wait-SqlContainer -ContainerName $cfg.ContainerName -Password $SaPassword
    Write-Host "Ready: SQL Server slot $slot on localhost,$($cfg.SqlPort)"
}

Write-Host ""
Write-Host "DB slots are ready."
