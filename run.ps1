<#
  启动定位模拟（一步）：解析 IOSRUN_ROOT -> 调 windows/start.ps1（自提权）。
  用法： powershell -ExecutionPolicy Bypass -File run.ps1
#>
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $PSCommandPath
& (Join-Path $here 'windows\start.ps1')