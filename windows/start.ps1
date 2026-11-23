<#
  iOSRealRun-cli-18 launcher (Windows).

  Requires env IOSRUN_ROOT = the directory that contains main.py / route.txt / .pylibs.
  Self-elevates (UAC), kills any previous simulation, mounts the Developer Disk Image only
  when needed, then runs main.py unbuffered and tees output to run.log.
#>
$ErrorActionPreference = 'Continue'

$root = $env:IOSRUN_ROOT
if (-not $root) {
    Write-Host 'IOSRUN_ROOT is not set. Example:'
    Write-Host '  $env:IOSRUN_ROOT = "D:\path\to\iOSRealRun-cli-18"'
    Read-Host 'Press Enter to close'
    exit 1
}
$env:PYTHONPATH = "$root\.pylibs;$root\.pylibs\win32;$root\.pylibs\win32\lib;$root\.pylibs\pywin32_system32"
$env:USERPROFILE = Join-Path $root 'pymd_home'
$env:PYTHONUNBUFFERED = '1'
Set-Location $root

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    $q = '"' + $PSCommandPath + '"'
    Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',$PSCommandPath -Verb RunAs
    exit
}

$old = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'main\.py|pymobiledevice3' }
if ($old) { $old | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Start-Sleep -Seconds 2 }

$log = Join-Path $root ('run-' + (Get-Date -Format 'HHmmss') + '.log')
Start-Transcript -Path $log -Force | Out-Null

Write-Host '[*] checking Developer Disk Image mount state'
$mnt = & python -m pymobiledevice3 mounter list 2>&1 | Out-String
Write-Host $mnt.Trim()
if ($mnt -notmatch 'build') {
    Write-Host '[*] DDI not mounted, auto-mount (60 s budget)'
    $p = Start-Process python -ArgumentList '-m','pymobiledevice3','mounter','auto-mount' -NoNewWindow -PassThru `
        -RedirectStandardOutput "$root\mount.out" -RedirectStandardError "$root\mount.err"
    if (-not $p.WaitForExit(60000)) { Write-Host '[*] mount timed out, continuing'; $p.Kill() }
} else {
    Write-Host '[*] DDI already mounted, skipping'
}

Write-Host '[*] starting location simulation - Ctrl+C stops it and restores real GPS'
& python -u main.py 2>&1 | Tee-Object -FilePath (Join-Path $root 'run.log')
Stop-Transcript | Out-Null
Write-Host '[*] exited'
Read-Host 'Press Enter to close'
