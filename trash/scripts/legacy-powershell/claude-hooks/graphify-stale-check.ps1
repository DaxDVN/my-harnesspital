# SessionStart hook — graphify staleness detector.
# Compares docs/+specs against the last-built graph manifest (scoped by the root
# .graphifyignore) and prints a directive to stdout ONLY when something changed,
# so Claude is told to refresh the knowledge graph. Silent + exit 0 when fresh or
# not yet built, so it never blocks session start. The detection logic lives in
# graphify_stale_check.py (called by path — avoids PowerShell 5.1's broken
# multi-line `python -c` argument passing).

$ErrorActionPreference = 'SilentlyContinue'

$root = $env:CLAUDE_PROJECT_DIR
if (-not $root) { $root = 'D:\arabica\roast' }

$manifest = Join-Path $root 'graphify-out\manifest.json'
if (-not (Test-Path $manifest)) { exit 0 }  # no graph built yet

# Resolve the interpreter that actually has graphify. [IO.File]::ReadAllText
# strips the UTF-8 BOM that PowerShell 5.1's Get-Content -Raw would leave in.
$pyFile = Join-Path $root 'graphify-out\.graphify_python'
$py = 'python'
if (Test-Path $pyFile) {
    $py = ([IO.File]::ReadAllText($pyFile)).TrimStart([char]0xFEFF).Trim()
}
if (-not (Test-Path $py)) { $py = 'python' }

$probe = Join-Path $root '.claude\hooks\graphify_stale_check.py'
if (-not (Test-Path $probe)) { exit 0 }

& $py $probe $root 2>$null
exit 0
