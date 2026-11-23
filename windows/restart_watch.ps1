<#
  提权守护：跑一次 UAC 后常驻，<IOSRUN_ROOT>\.restart 时间戳一变就重启 main.py，
  这样规划器的「保存并重启模拟」无需再弹 UAC。

  用法： powershell -ExecutionPolicy Bypass -File windows\restart_watch.ps1
#>
$ErrorActionPreference = 'Continue'

function Resolve-IosRunRoot {
    if ($env:IOSRUN_ROOT) { return (Resolve-Path $env:IOSRUN_ROOT).Path }
    $here = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
    foreach ($c in @((Join-Path $here '..\iOSRealRun-cli-18'), (Join-Path $here 'iOSRealRun-cli-18'))) {
        if (Test-Path (Join-Path $c 'main.py')) { return (Resolve-Path $c).Path }
    }
    throw '找不到 iOSRealRun-cli-18：设置 $env:IOSRUN_ROOT，或把本仓库放在它同级。'
}

$root = Resolve-IosRunRoot
$python = if ($env:IOSRUN_PYTHON) { $env:IOSRUN_PYTHON }
          elseif (Test-Path (Join-Path $root '.venv\Scripts\python.exe')) { Join-Path $root '.venv\Scripts\python.exe' }
          else { 'python' }
$paths = @()
foreach ($p in @('.pylibs', '.pylibs\win32', '.pylibs\win32\lib', '.pylibs\pywin32_system32')) {
    $full = Join-Path $root $p
    if (Test-Path $full) { $paths += $full }
}
if ($paths.Count -gt 0) { $env:PYTHONPATH = ($paths -join ';') }
$env:USERPROFILE = if ($env:IOSRUN_HOME) { $env:IOSRUN_HOME } else { Join-Path $root 'pymd_home' }
$env:PYTHONUNBUFFERED = '1'
Set-Location $root
$flag = Join-Path $root '.restart'

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',$PSCommandPath -Verb RunAs
    exit
}

function Stop-Sim {
    $old = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -match 'main\.py|pymobiledevice3' }
    if ($old) { $old | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } }
    Start-Sleep -Seconds 2
}

function Start-Sim {
    Stop-Sim
    $stamp = Get-Date -Format 'HHmmss'
    $out = Join-Path $root "run-$stamp.log"
    $err = Join-Path $root "run-$stamp.err"
    $p = Start-Process $python -ArgumentList '-u','main.py' -WorkingDirectory $root -PassThru `
        -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden
    "$(Get-Date -Format 'HH:mm:ss') started main.py pid=$($p.Id) log=$out" |
        Out-File -Append -Encoding utf8 (Join-Path $root 'watch.log')
}

$last = [datetime]'2000-01-01'
Start-Sim
while ($true) {
    if (Test-Path $flag) {
        $t = (Get-Item $flag).LastWriteTime
        if ($t -gt $last) { $last = $t; Start-Sim }
    }
    Start-Sleep -Seconds 2
}