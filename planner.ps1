<#
  打开网页画线规划器，默认 http://127.0.0.1:8850/
  用法： powershell -ExecutionPolicy Bypass -File planner.ps1 [-Port 8850] [-NoBrowser]
#>
param([int]$Port = 8850, [switch]$NoBrowser)
$ErrorActionPreference = 'Continue'
$here = Split-Path -Parent $PSCommandPath

function Resolve-IosRunRoot {
    if ($env:IOSRUN_ROOT) { return (Resolve-Path $env:IOSRUN_ROOT).Path }
    foreach ($c in @((Join-Path $here '..\iOSRealRun-cli-18'), (Join-Path $here 'iOSRealRun-cli-18'))) {
        if (Test-Path (Join-Path $c 'main.py')) { return (Resolve-Path $c).Path }
    }
    throw '找不到 iOSRealRun-cli-18：设置 IOSRUN_ROOT，或把本仓库放在它同级'
}

$root = Resolve-IosRunRoot
$python = if ($env:IOSRUN_PYTHON) { $env:IOSRUN_PYTHON } elseif (Test-Path (Join-Path $root '.venv\Scripts\python.exe')) { Join-Path $root '.venv\Scripts\python.exe' } else { 'python' }
$env:IOSRUN_ROOT = $root
$env:PLAN_PORT = $Port
if (-not $NoBrowser) { Start-Process ('http://127.0.0.1:' + $Port + '/') }
& $python (Join-Path $here 'planner\route_plan.py')