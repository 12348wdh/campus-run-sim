<#
  Elevated simulator supervisor.

  Runs once with UAC, then restarts main.py whenever <IOSRUN_ROOT>\.restart is touched, so the
  planner page can switch routes without another UAC prompt.

  Start it once:  powershell -ExecutionPolicy Bypass -File windows\restart_watch.ps1
#>
$ErrorActionPreference = 'Continue'

$root = $env:IOSRUN_ROOT
if (-not $root) { throw 'set IOSRUN_ROOT to the iOSRealRun-cli-18 directory before running this script' }
$env:PYTHONPATH = "$root\.pylibs;$root\.pylibs\win32;$root\.pylibs\win32\lib;$root\.pylibs\pywin32_system32"
$env:USERPROFILE = Join-Path $root 'pymd_home'
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
    $p = Start-Process python -ArgumentList '-u','main.py' -WorkingDirectory $root -PassThru `
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
