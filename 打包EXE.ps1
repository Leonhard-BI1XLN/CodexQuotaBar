$ErrorActionPreference = 'Stop'

$projectRoot = $PSScriptRoot
$buildRoot = Join-Path $env:TEMP 'CodexQuotaBar-build'
$venvRoot = Join-Path $env:TEMP 'CodexQuotaBar-build-venv'
$pythonPath = Join-Path $venvRoot 'Scripts\python.exe'

if (-not (Test-Path -LiteralPath $pythonPath)) {
    & py -3.13 -m venv $venvRoot
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not create the build environment. Install Python 3.13 and ensure py.exe is available.'
    }
}

$pipArgs = @('-m', 'pip', 'install', '--disable-pip-version-check', 'pyinstaller==6.22.3', 'pillow==12.3.0')
& $pythonPath @pipArgs
if ($LASTEXITCODE -ne 0) {
    throw 'PyInstaller installation failed.'
}

New-Item -ItemType Directory -Force -Path $buildRoot | Out-Null
$buildArgs = @(
    '-m', 'PyInstaller',
    '--clean',
    '--noconfirm',
    '--onefile',
    '--windowed',
    '--name', 'CodexQuotaBar',
    '--manifest', (Join-Path $projectRoot 'CodexQuotaBar.manifest'),
    '--distpath', $projectRoot,
    '--workpath', (Join-Path $buildRoot 'work'),
    '--specpath', $buildRoot,
    (Join-Path $projectRoot 'CodexQuotaBar.pyw')
)
& $pythonPath @buildArgs
if ($LASTEXITCODE -ne 0) {
    throw 'EXE packaging failed.'
}

Write-Host ('Created: ' + (Join-Path $projectRoot 'CodexQuotaBar.exe'))
