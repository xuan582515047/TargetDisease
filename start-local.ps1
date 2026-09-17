param([int]$Port = 3001)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonRuntime = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (!(Test-Path $pythonRuntime)) { throw 'Create .venv and install backend/requirements.txt first.' }
$nodeRuntime = (Get-Command node).Source
$major = [int]((& $nodeRuntime -p 'process.versions.node.split(".")[0]') | Select-Object -Last 1)
if ($major -lt 22) {
  & npm exec --yes --package=node@22 -- node --version
  $npmCache = (& npm config get cache | Select-Object -Last 1).Trim()
  $nodeRuntime = Get-ChildItem (Join-Path $npmCache '_npx') -Filter node.exe -Recurse | Where-Object FullName -match 'node\\bin\\node.exe$' | Select-Object -First 1 -ExpandProperty FullName
}
if (!$nodeRuntime) { throw 'Node.js 22 or newer is required.' }
$env:NEXT_TELEMETRY_DISABLED = '1'
$env:NEXT_DIST_DIR = '.next-local'
$env:Path = (Split-Path $nodeRuntime) + ';' + $env:Path
if (!(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)) {
  Start-Process -FilePath $pythonRuntime -ArgumentList '-m','scripts.run_local' -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $projectRoot 'backend-dev.log') -RedirectStandardError (Join-Path $projectRoot 'backend-error.log')
}
if (!(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) {
  Start-Process -FilePath $nodeRuntime -ArgumentList 'node_modules/next/dist/bin/next','dev','--port',"$Port" -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $projectRoot 'frontend-dev.log') -RedirectStandardError (Join-Path $projectRoot 'frontend-error.log')
}
Write-Output "Frontend: http://localhost:$Port / Backend: http://127.0.0.1:8000/healthz"
