$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$localPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$preparedPython = Join-Path $PSScriptRoot '..\..\work\.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $localPython) {
    $runtimePython = $localPython
} elseif (Test-Path -LiteralPath $preparedPython) {
    $runtimePython = (Resolve-Path -LiteralPath $preparedPython).Path
} else {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required.' }
    $runtimePython = $localPython
    & $runtimePython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
& $runtimePython -m streamlit run app.py --server.headless true
