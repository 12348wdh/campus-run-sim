<#
  iOSRealRun 启动器：自提权 -> 杀旧进程 -> 按需挂载 DDI -> 跑 main.py（非缓冲）并 tee 日志。

  前置：$env:IOSRUN_ROOT 指向 iOSRealRun-cli-18 目录（不设则取本仓库上一级的同名目录）。
  可选：$env:IOSRUN_PYTHON 指定解释器；$env:IOSRUN_HOME 覆盖 pymobiledevice3 的状态目录。
#>
$ErrorActionPreference = 'Continue'

function Resolve-IosRunRoot {
    if ($env:IOSRUN_ROOT) { return (Resolve-Path $env:IOSRUN_ROOT).Path }
    $here = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
    foreach ($c in @((Join-Path $here '..\iOSRealRun-cli-18'), (Join-Path $here 'iOSRealRun-cli-18'))) {
        if (Test-Path (Join-Path $c 'main.py')) { return (Resolve-Path $c).Path }
    }
    throw '找不到 iOSRealRun-cli-18：设置 $env:IOSRUN_ROOT 指向它，或把本仓库放在它同级。'
}

$root = Resolve-IosRunRoot
if (-not (Test-Path (Join-Path $root 'main.py'))) { throw "$root 下没有 main.py" }

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

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',"$PSCommandPath" -Verb RunAs
    exit
}

$old = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'main\.py|pymobiledevice3' }
if ($old) { $old | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Start-Sleep -Seconds 2 }

$log = Join-Path $root ('run-' + (Get-Date -Format 'HHmmss') + '.log')
Start-Transcript -Path $log -Force | Out-Null

Write-Host "[*] python = $python"
Write-Host '[*] checking developer disk image mount state'
$mnt = & $python -m pymobiledevice3 mounter list 2>&1 | Out-String
Write-Host $mnt.Trim()
if ($mnt -notmatch 'build') {
    Write-Host '[*] DDI not mounted, auto-mount (60s budget)'
    $p = Start-Process $python -ArgumentList '-m','pymobiledevice3','mounter','auto-mount' -NoNewWindow -PassThru -RedirectStandardOutput "$root\mount.out" -RedirectStandardError "$root\mount.err"
    if (-not $p.WaitForExit(60000)) { Write-Host '[*] mount timed out, continuing'; $p.Kill() }
} else {
    Write-Host '[*] DDI already mounted, skipping'
}

Write-Host '[*] starting location simulation - Ctrl+C stops it and restores real GPS'
& $python -u main.py 2>&1 | Tee-Object -FilePath "$root\run.log"
Stop-Transcript | Out-Null
Write-Host '[*] exited'
Read-Host 'Press Enter to close'