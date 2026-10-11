param([string]$ReleaseDirectory = '')
$ErrorActionPreference = 'Stop'
$taskProject = Split-Path -Parent $PSScriptRoot
$taskPython = Join-Path $env:LOCALAPPDATA 'SamtecLockers\venvs\dev\Scripts\python.exe'
$taskBuild = Join-Path $env:LOCALAPPDATA 'SamtecLockers\build'
$taskRelease = Join-Path $env:LOCALAPPDATA 'SamtecLockers\release'
if ($ReleaseDirectory) { $taskRelease = $ReleaseDirectory }
$taskOriginalPath = $env:PATH
# Keep bundled tool runtimes from supplying incompatible Windows CRT DLLs.
$env:PATH = (($env:PATH -split ';') | Where-Object { $_ -notmatch 'codex-runtimes' }) -join ';'
Push-Location $taskProject
try {
    & $taskPython -m PyInstaller --clean --noconfirm --windowed --name SamtecLockers --distpath $taskRelease --workpath $taskBuild --specpath $taskBuild --paths $taskProject --add-data "$taskProject\assets;assets" --add-data "$taskProject\migrations;migrations" --hidden-import sqlalchemy.dialects.postgresql.psycopg --hidden-import psycopg_binary --hidden-import uvicorn.logging --hidden-import uvicorn.loops.auto --hidden-import uvicorn.protocols.http.auto --hidden-import uvicorn.protocols.http.h11_impl --hidden-import uvicorn.lifespan.on launch.pyw
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el ejecutable.' }
    Write-Output (Join-Path $taskRelease 'SamtecLockers\SamtecLockers.exe')
} finally { Pop-Location; $env:PATH = $taskOriginalPath }
