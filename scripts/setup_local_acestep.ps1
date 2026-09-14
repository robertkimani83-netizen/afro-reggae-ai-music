$ErrorActionPreference = 'Stop'

$aceDir = Join-Path $env:USERPROFILE 'ACE-Step-1.5'

Write-Host '=== Local ACE-Step setup ==='
Write-Host "Install location: $aceDir"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'Git is required. Install Git for Windows first.'
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host 'Installing uv...'
    powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

if (-not (Test-Path $aceDir)) {
    Write-Host 'Downloading ACE-Step 1.5...'
    git clone https://github.com/ACE-Step/ACE-Step-1.5.git $aceDir
}
else {
    Write-Host 'ACE-Step folder already exists.'
}

Set-Location $aceDir

if (-not (Test-Path (Join-Path $aceDir '.venv'))) {
    Write-Host 'Installing ACE-Step dependencies. This can take a while on first run...'
    uv sync
}
else {
    Write-Host 'ACE-Step environment already installed.'
}

Write-Host 'Local ACE-Step is ready.'
