<#
  启动定位模拟。
    默认：前台跑 main.py，Ctrl+C 退出并把定位还原成真实 GPS。
    -Watch ：改用常驻守护（后台跑，规划器的“保存并重启模拟”直接生效）。
    -Speed ：先把 iOSRealRun 的 config.yaml 里 v（米/秒）改掉。2.9 约 5'45"/km。
  用法： powershell -ExecutionPolicy Bypass -File run.ps1 [-Speed 2.9] [-Watch]
#>
param([double]$Speed = 0, [switch]$Watch)
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
if ($Speed -gt 0) {
    & $python (Join-Path $here 'tools\set_speed.py') --root $root --speed $Speed
}
$env:IOSRUN_ROOT = $root
if ($Watch) {
    & (Join-Path $here 'windows\restart_watch.ps1')
} else {
    & (Join-Path $here 'windows\start.ps1')
}