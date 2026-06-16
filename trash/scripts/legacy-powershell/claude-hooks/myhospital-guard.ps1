$ErrorActionPreference = 'Stop'

function Deny([string]$Message) {
  [Console]::Error.WriteLine($Message)
  exit 2
}

function Normalize-PathText([string]$PathText) {
  if ([string]::IsNullOrWhiteSpace($PathText)) {
    return ''
  }
  return ($PathText -replace '\\', '/')
}

function Get-NewEditText($ToolInput) {
  $parts = New-Object System.Collections.Generic.List[string]

  foreach ($name in @('content', 'new_string')) {
    if ($ToolInput.PSObject.Properties.Name -contains $name -and $null -ne $ToolInput.$name) {
      [void]$parts.Add([string]$ToolInput.$name)
    }
  }

  if ($ToolInput.PSObject.Properties.Name -contains 'edits' -and $null -ne $ToolInput.edits) {
    foreach ($edit in $ToolInput.edits) {
      foreach ($name in @('new_string')) {
        if ($edit.PSObject.Properties.Name -contains $name -and $null -ne $edit.$name) {
          [void]$parts.Add([string]$edit.$name)
        }
      }
    }
  }

  return ($parts -join "`n")
}

function Matches([string]$Text, [string]$Pattern) {
  if ([string]::IsNullOrEmpty($Text)) {
    return $false
  }
  return [regex]::IsMatch($Text, $Pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
}

$raw = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($raw)) {
  exit 0
}

try {
  $event = $raw | ConvertFrom-Json -ErrorAction Stop
} catch {
  exit 0
}

$toolName = [string]$event.tool_name
$toolInput = $event.tool_input

if ($toolName -eq 'Bash') {
  $command = [string]$toolInput.command

  if (Matches $command '(^|\s)(git\s+reset\s+--hard|git\s+checkout\s+--|git\s+clean\s+-|git\s+commit|git\s+push)(\s|$)') {
    Deny 'BLOCKED_RULE: git-history-operation. This project does not allow commit/push/reset/checkout cleanups from the agent.'
  }

  if (Matches $command '(^|\s)(npm\s+(install|i)\s+\S+|pnpm\s+add\s+\S+|yarn\s+add\s+\S+|bun\s+add\s+\S+|dotnet\s+add\s+package)(\s|$)') {
    Deny 'BLOCKED_RULE: dependency-change. New packages require explicit human approval and harness update.'
  }

  if (Matches $command '(^|\s)(rm\s+-rf|Remove-Item\s+.*-Recurse)(\s|$)') {
    Deny 'BLOCKED_RULE: destructive-delete. Recursive deletion requires explicit user approval.'
  }

  exit 0
}

if ($toolName -notin @('Write', 'Edit', 'MultiEdit')) {
  exit 0
}

$filePath = ''
foreach ($name in @('file_path', 'path')) {
  if ($toolInput.PSObject.Properties.Name -contains $name -and $null -ne $toolInput.$name) {
    $filePath = Normalize-PathText ([string]$toolInput.$name)
    break
  }
}

$editText = Get-NewEditText $toolInput

if (Matches $filePath 'myhospital-fe/src/lib/(dtos|server)/(generated-dtos|generated-api-client|Constants)\.ts$') {
  Deny 'BLOCKED_RULE: generated-fe-file. Regenerate DTO/client artifacts instead of editing generated files.'
}

if (Matches $filePath 'myhospital-be/MyHospital\.ServiceInterface/Migrations/.*\.cs$') {
  Deny 'BLOCKED_RULE: migration-hand-edit. Change the model and generate a new migration with dotnet ef migrations add.'
}

if (Matches $filePath 'myhospital-fe/src/.*\.(ts|tsx)$') {
  if (Matches $editText '\bfetch\s*\(|from\s+[''"]axios[''"]|\baxios\.|Authorization\s*:\s*[''"]Bearer|[''"]use client[''"]|from\s+[''"](zustand|jotai|redux|mobx|react-icons|react-modal)[''"]') {
    Deny 'BLOCKED_RULE: fe-forbidden-pattern. Use module adapters/generated hooks, existing state/context, lucide icons, and Vite-compatible code.'
  }
}

if (Matches $filePath 'myhospital-be/.*\.cs$') {
  if (Matches $editText 'BeginTransactionAsync|IDbContextTransaction|IProcessLockService|Db\.Remove\s*\(|\.SaveChangesAsync\s*\(|throw\s+new\s+Exception|return\s+null\s*;|AllowAnonymous|JObject|Dictionary\s*<\s*string\s*,\s*object\s*>|dynamic\s+') {
    Deny 'BLOCKED_RULE: be-forbidden-pattern. Follow BaseService, BusinessException, typed DTOs, auth, and no transaction/lock conventions.'
  }
}

exit 0
