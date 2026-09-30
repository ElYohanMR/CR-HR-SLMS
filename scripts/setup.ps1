$ErrorActionPreference = 'Stop'
$taskProject = Split-Path -Parent $PSScriptRoot
$taskEnvironment = Join-Path $env:LOCALAPPDATA 'SamtecLockers\venvs\dev'
$taskPython = Join-Path $taskEnvironment 'Scripts\python.exe'

if (-not (Test-Path -LiteralPath $taskPython)) {
    & py -3.13 -m venv $taskEnvironment
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno Python 3.13.' }
}

& $taskPython -m pip install -r (Join-Path $taskProject 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias.' }

& $taskPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Se detectaron dependencias incompatibles.' }

Write-Output "Entorno preparado: $taskPython"
