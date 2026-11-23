<#
  campus-run-sim 一键安装：建 .venv、装依赖、检查 Apple 服务，打印下一步。
  用法： powershell -ExecutionPolicy Bypass -File setup.ps1
#>
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSCommandPath
Set-Location $root
Write-Host '=== campus-run-sim setup ===' -ForegroundColor Cyan

$pyExe = $null; $pyVer = $null
foreach ($v in @('3.13','3.12','3.11','3.10')) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py ('-' + $v) -c 'import sys' 2>$null
        if ($LASTEXITCODE -eq 0) { $pyExe = 'py'; $pyVer = $v; break }
    }
}
if (-not $pyExe) {
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host '找不到 Python，装 3.12 或 3.13： https://www.python.org/downloads/' -ForegroundColor Red
        exit 1
    }
    $pyExe = 'python'
    $fallback = & python -c "import sys;print('%d.%d' % sys.version_info[:2])"
    Write-Host ('[*] 回退到 python ' + $fallback)
    if ($fallback -eq '3.14') {
        Write-Host '    3.14 没有 hexdump 的 wheel，安装脚本会改走源码方式。' -ForegroundColor Yellow
    }
} else {
    Write-Host ('[*] 使用 py -' + $pyVer)
}

$venv = Join-Path $root '.venv'
if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
    Write-Host '[*] 创建 .venv'
    if ($pyExe -eq 'py') { & py ('-' + $pyVer) -m venv $venv } else { & python -m venv $venv }
}
$vpy = Join-Path $venv 'Scripts\python.exe'
& $vpy -m pip install --disable-pip-version-check -q --upgrade pip

Write-Host '[*] 安装依赖（首次 1-3 分钟）'
& $vpy (Join-Path $root 'scripts\setup_deps.py')
if ($LASTEXITCODE -ne 0) {
    Write-Host '依赖安装失败，把上面的报错发到 issue。' -ForegroundColor Red
    exit 1
}

Write-Host '[*] 检查 Apple Mobile Device Service'
$svc = Get-Service 'Apple Mobile Device Service' -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Host '    未安装：先装 iTunes 或 Apple Mobile Device Support。' -ForegroundColor Yellow
} elseif ($svc.Status -ne 'Running') {
    Write-Host ('    状态 ' + $svc.Status + '，尝试启动') -ForegroundColor Yellow
    try { Start-Service 'Apple Mobile Device Service' } catch { Write-Host '    启动失败，用管理员权限重试。' -ForegroundColor Yellow }
} else {
    Write-Host '    RUNNING'
}

Write-Host '[*] 检查 usbmux 能否看到 iPhone'
$oldHome = $env:USERPROFILE
$env:USERPROFILE = Join-Path $root 'pymd_home'
New-Item -ItemType Directory -Force $env:USERPROFILE | Out-Null
$dev = & $vpy -m pymobiledevice3 usbmux list 2>&1 | Out-String
$devCode = $LASTEXITCODE
$env:USERPROFILE = $oldHome
if ($devCode -ne 0) {
    Write-Host '    命令执行失败，看 README 的疑难排查（多为家目录不可写或 Apple 驱动没装）' -ForegroundColor Yellow
} elseif ($dev -match 'DeviceID') {
    Write-Host '    已发现设备' -ForegroundColor Green
} else {
    Write-Host '    未发现设备：连数据线、手机上点信任、安装带 NTamd64 段的 Apple USB 驱动' -ForegroundColor Yellow
}

Write-Host ''
Write-Host '=== 完成，下一步 ===' -ForegroundColor Cyan
Write-Host '  1) 连数据线，手机上点“信任”，并打开 设置-隐私与安全性-开发者模式'
Write-Host '  2) $env:IOSRUN_ROOT = "D:\path\to\iOSRealRun-cli-18"    # 已 clone 的 iOSRealRun 目录'
Write-Host '  3) powershell -ExecutionPolicy Bypass -File run.ps1       # 启动定位模拟（弹一次 UAC）'
Write-Host '  4) powershell -ExecutionPolicy Bypass -File planner.ps1   # 打开网页画线规划器'
