# Mimir MVP - one command. Creates the venv on first run, then serves.
#
# No Docker, no Databricks, no database, no API key. Plain Python.
#
# This file is deliberately PURE ASCII. Windows PowerShell 5.1 reads a UTF-8
# file with no byte-order mark as cp1252, so a single em dash in a comment
# corrupts the bytes after it and the parser reports a missing string
# terminator a hundred lines away. An earlier version of this script had em
# dashes and failed exactly that way on 5.1 while working on 7.x. Keep it ASCII.
#
# Finding Python is also not as simple as `Get-Command python`. The Microsoft
# Store build installs an App Execution Alias under WindowsApps that
# Get-Command frequently does not enumerate, even though the executable runs
# perfectly when invoked by path. On a machine with only the Store build the
# naive check reports "Python not found" with Python sitting right there, so
# every candidate below is probed by actually running it.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Test-Python($exe) {
    if (-not $exe) { return $null }
    try {
        $out = & $exe -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $out) { return $null }
        $parts = "$out".Trim().Split(".")
        $major = [int]$parts[0]
        $minor = [int]$parts[1]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
            Write-Host "  found Python $out at $exe - too old, need 3.11+" -ForegroundColor DarkYellow
            return $null
        }
        return @{ Path = $exe; Version = "$out" }
    } catch {
        return $null
    }
}

$candidates = @("python", "python3", "py")
# The Store alias, which Get-Command frequently misses.
$candidates += (Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\python.exe")
# Ordinary per-user and machine installs.
$roots = @((Join-Path $env:LOCALAPPDATA "Programs\Python"),
           "$env:ProgramFiles\Python313", "$env:ProgramFiles\Python312",
           "$env:ProgramFiles\Python311", "C:\Python313", "C:\Python312",
           "C:\Python311")
foreach ($root in $roots) {
    if (Test-Path $root) {
        $found = Get-ChildItem -Path $root -Filter "python.exe" -Recurse -ErrorAction SilentlyContinue |
                 Select-Object -First 4 -ExpandProperty FullName
        if ($found) { $candidates += $found }
    }
}

$py = $null
foreach ($c in $candidates) {
    $hit = Test-Python $c
    if ($hit) { $py = $hit; break }
}

if (-not $py) {
    Write-Host ""
    Write-Host "Python 3.11 or newer was not found." -ForegroundColor Red
    Write-Host "Install it, then open a NEW terminal and run .\run.ps1 again:"
    Write-Host "    winget install Python.Python.3.13" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Already installed? Print the path and send me what this says:"
    Write-Host "    Get-Command python, python3, py | Select-Object Name, Source" -ForegroundColor Cyan
    exit 1
}

Write-Host ("Python " + $py.Version + " - " + $py.Path) -ForegroundColor DarkGray

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "Creating .venv (first run only)..." -ForegroundColor Cyan
    & $py.Path -m venv .venv
    if (-not (Test-Path $venvPy)) {
        Write-Host "venv creation failed. On the Store build this can mean the venv" -ForegroundColor Red
        Write-Host "module is missing; install Python from python.org instead." -ForegroundColor Red
        exit 1
    }
    & $venvPy -m pip install --quiet --upgrade pip
    Write-Host "Installing five dependencies (about a minute)..." -ForegroundColor Cyan
    & $venvPy -m pip install --quiet -r requirements.txt
}

# Verify before serving, so a half-finished install fails here with a clear
# message rather than as a blank page in the browser.
& $venvPy -c "import fastapi, uvicorn, pandas, numpy, openpyxl" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "The virtual environment is incomplete - the first install was" -ForegroundColor Red
    Write-Host "probably interrupted. Delete .venv and run .\run.ps1 again." -ForegroundColor Red
    exit 1
}

$port = "8000"
if ($env:MIMIR_PORT) { $port = $env:MIMIR_PORT }

$url = "http://127.0.0.1:" + $port
Write-Host ""
Write-Host "  Mimir MVP - Denmark, September 2026" -ForegroundColor Magenta
Write-Host ("  " + $url + "    (Ctrl+C to stop)") -ForegroundColor Magenta
Write-Host ""
& $venvPy -m uvicorn app.main:app --host 127.0.0.1 --port $port
