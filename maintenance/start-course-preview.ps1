param([switch]$Check)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$candidates = @(
    "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
)
$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
if ($nodeCommand) {
    $dependencyRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $nodeCommand.Source))
    $candidates += Join-Path $dependencyRoot 'python\python.exe'
}
$runtimeRoots = Get-ChildItem -LiteralPath 'C:\Program Files\WindowsApps' -Directory -Filter 'OpenAI.CodexPrimaryRuntime*' -ErrorAction SilentlyContinue | Sort-Object Name -Descending
foreach ($runtimeRoot in $runtimeRoots) {
    $candidates += Join-Path $runtimeRoot.FullName 'dependencies\python\python.exe'
}
$candidates += Get-ChildItem -Path "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand -and $pythonCommand.Source -notlike '*\Microsoft\WindowsApps\*') { $candidates += $pythonCommand.Source }
$pythonExe = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $pythonExe) { throw 'Python 3 was not found. Install Python 3.12 or newer, then run this file again.' }
if ($Check) { & $pythonExe --version; exit $LASTEXITCODE }
Set-Location -LiteralPath $projectRoot
$env:PYTHONUTF8 = '1'
$previewScript = Join-Path $PSScriptRoot 'serve-course-preview.py'
# Restart only preview processes from this project; other Python apps are unrelated.
$previewProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -like 'python*' -and $_.CommandLine -and $_.CommandLine.Contains($previewScript)
}
foreach ($previewProcess in $previewProcesses) {
    Write-Host 'Restarting the course preview with the current files...'
    Stop-Process -Id $previewProcess.ProcessId -ErrorAction SilentlyContinue
}
& $pythonExe $previewScript --open-browser
if ($LASTEXITCODE -ne 0) { throw "Preview stopped with code $LASTEXITCODE" }
