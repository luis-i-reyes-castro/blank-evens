# Install Python 3.11+ for the current user when it is missing, then install blank-evens.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Test-Python311 {
    param(
        [string] $File,
        [string[]] $Extra
    )
    if ($File -ne "py" -and -not (Test-Path -LiteralPath $File)) {
        return $false
    }
    & $File @Extra -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
    return $LASTEXITCODE -eq 0
}

function Get-PythonCommand {
    $launcher = Join-Path $env:LocalAppData "Programs\Python\Launcher\py.exe"
    if (Test-Python311 -File $launcher -Extra @("-3")) {
        return @{ File = $launcher; Extra = @("-3") }
    }
    if (Get-Command py -ErrorAction SilentlyContinue) {
        if (Test-Python311 -File "py" -Extra @("-3")) {
            return @{ File = "py"; Extra = @("-3") }
        }
    }
    foreach ($ver in @("313", "314", "312", "311")) {
        $candidate = Join-Path $env:LocalAppData "Programs\Python\Python$ver\python.exe"
        if (Test-Python311 -File $candidate -Extra @()) {
            return @{ File = $candidate; Extra = @() }
        }
    }
    return $null
}

$python = Get-PythonCommand
if (-not $python) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw @"
winget is not available, and Python 3.11+ was not found.
Install Python from https://www.python.org/downloads/windows/ and run this installer again.
"@
    }
    Write-Host "Installing Python 3.13 for the current user (no administrator account required)..."
    & winget install --id Python.Python.3.13 -e --scope user --accept-package-agreements --accept-source-agreements
    $python = Get-PythonCommand
}
if (-not $python) {
    throw @"
Python 3.11+ is still not available.
Install it from https://www.python.org/downloads/windows/ and run this installer again.
"@
}

$venv    = Join-Path $PSScriptRoot ".venv"
$venvPy  = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPy)) {
    & $python.File @($python.Extra) -m venv $venv
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the virtual environment in $venv."
    }
}

& $venvPy -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Could not upgrade pip."
}
& $venvPy -m pip install $PSScriptRoot
if ($LASTEXITCODE -ne 0) {
    throw "Could not install blank-evens and pypdf."
}

& $venvPy -m pip install pywin32
if ($LASTEXITCODE -ne 0) {
    Write-Warning "pywin32 was not installed. PDF files still work. Word and PowerPoint need pywin32 or LibreOffice."
}

Write-Host ""
Write-Host "Installed. Drag documents onto blank_evens_in_pdf.bat."
Write-Host "PDF files need only this install. Word and PowerPoint also need Microsoft Office or LibreOffice."
