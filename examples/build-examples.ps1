$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$Cli = Join-Path $ProjectDir ".venv\Scripts\telc-audio.exe"
$Cover = Join-Path $ScriptDir "cover-small.jpg"

if (-not (Test-Path $Cli -PathType Leaf)) {
    throw "Missing CLI: $Cli. Create .venv and run: .venv\Scripts\pip.exe install -e ."
}

if (-not (Get-Command lame -ErrorAction SilentlyContinue)) {
    throw "lame must be installed and available on PATH."
}

& $Cli build `
    (Join-Path $ScriptDir "01_Geburtstag\01_Geburtstag.md") `
    --cover $Cover

& $Cli build `
    (Join-Path $ScriptDir "05_Touristeninformation\05_Touristeninformation.md") `
    --cover $Cover

Write-Host "Generated both example MP3 files."

