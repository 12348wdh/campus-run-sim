# campus-run-sim

把 iPhone 的定位仿真成校园跑路线：一键安装、网页画线、免 UAC 热重启。

本仓库是 [MTDickens/iOSRealRun-cli-18](https://github.com/MTDickens/iOSRealRun-cli-18) 的外围工具，不重复它的代码，只解决三件事：改坐标要手搓 JSON、重启要手动提权、路线画不直观。

## 三步上手

```powershell
git clone https://github.com/12348wdh/campus-run-sim
cd campus-run-sim
powershell -ExecutionPolicy Bypass -File setup.ps1     # 1. 建 .venv、装依赖、检查 Apple 服务
$env:IOSRUN_ROOT = 'D:\path\to\iOSRealRun-cli-18'   # 2. 指向已 clone 的 iOSRealRun 目录
powershell -ExecutionPolicy Bypass -File run.ps1       # 3. 启动定位模拟（弹一次 UAC）
powershell -ExecutionPolicy Bypass -File planner.ps1   # 4. 画线 http://127.0.0.1:8850/
```

`setup.ps1` 自动挑 Python 3.10–3.13、建 `.venv`、处理 hexdump 没有 wheel 的老问题、检查 `Apple Mobile Device Service`，最后用 `pymobiledevice3 usbmux list` 确认真的能看到 iPhone，再把下一步打印一遍。

还没 clone iOSRealRun 本体：`git clone https://github.com/MTDickens/iOSRealRun-cli-18`

## 它包含什么

| 文件 | 作用 |
|---|---|
| `setup.ps1`、`scripts/setup_deps.py` | 一键装依赖（venv + hexdump 兜底 + 服务检查） |
| `run.ps1` | 启动模拟，等价 `windows/start.ps1`（自提权、按需挂 DDI、tee 日志） |
| `planner.ps1` | 起规划器并打开浏览器 |
| `planner/route_plan.py` | 本地 HTTP 服务（默认 8850）：托管规划页、写 route.txt、触发重启 |
| `planner/planner.html` | Leaflet + 高德瓦片，点击画线、拖动微调、实时算长度 |
| `windows/start.ps1` | 提权启动器：杀旧进程 → 挂 DDI → 跑 main.py |
| `windows/restart_watch.ps1` | 提权守护：监听 `.restart`，规划器一键热重启免 UAC |
| `tools/make_route.py` | 椭圆环线，支持 `--campus` 地名地理编码 |
| `tools/make_route_loop.py` | 跑道型圆角矩形（标准操场形状） |
| `tools/make_route_rect.py` | 任意圆角矩形，附带 `wgs84_to_bd09()` / `m_per_deg()` |
| `tools/make_route_cover.py` | 蛇形扫场：线距 ≤ 2×判定半径，保证打卡点全覆盖 |
| `scripts/selfcheck.py` | 自检：导入、坐标、route.txt、规划器接口、页面资源 |

## 前置条件

1. Windows 10/11、数据线、iPhone（只能连一台）
2. iTunes 或 Apple Mobile Device Support（提供 usbmuxd），装完 `Apple Mobile Device Service` 应为 RUNNING
3. 手机上点「信任」，并打开 设置 → 隐私与安全性 → 开发者模式（重启生效）
4. Python 3.10–3.13（3.14 也能跑，装依赖会走源码兜底）

驱动、`usbmux list` 返回空这类问题的排查见「疑难排查」。

## 用法

### A. 网页画线（推荐）

```powershell
powershell -ExecutionPolicy Bypass -File planner.ps1
# 或： python planner\route_plan.py
```

1. 地图默认落在操场中心，点击加点，蓝线按顺序连线
2. 拖白边圆点微调，右键删点，可撤销/清空
3. 勾「首尾相接成环」画环线，面板实时显示点数、长度、1 km 需跑几圈
4. 「卫星/路网」切换高德卫星图看清跑道边界
5. 「保存并重启模拟」写 route.txt 并触发 `.restart`，守护进程 2 秒内热重启

> 热重启要先跑一次 `windows/restart_watch.ps1`（提权一次，之后一直有效）。不跑它时「保存」只写文件，需要重新执行 `run.ps1`。

### B. 命令行生成路线

```powershell
# 椭圆环线，一圈约 350 m
python tools\make_route.py --lat 30.9323325 --lng 121.7003788 --r 68 --ratio 0.62 --n 90 --out route.txt

# 400 m 标准田径场形状
python tools\make_route_loop.py --lat 30.9283099 --lng 121.6896685 --len 130 --wid 72 --corner-r 16 --out route.txt

# 扫场 150x100 m，线距 30 m，任意点在 15 m 内被压到
python tools\make_route_cover.py --lat 30.9283099 --lng 121.6896685 --len 150 --wid 100 --spacing 30 --out route.txt
```

`--lat/--lng` 一律填 WGS-84（OSM、Google 地图上的坐标），脚本内部转 BD-09。

### C. 启动与停止

```powershell
powershell -ExecutionPolicy Bypass -File run.ps1                     # 启动（弹 UAC）
powershell -ExecutionPolicy Bypass -File windows\restart_watch.ps1   # 常驻守护，之后保存即重启
```

速度在 `config.yaml` 的 `v`（米/秒）：`2.9` 约 5 分 45 秒每公里，适合校园跑判定；原仓库默认 `5.56` 是 3 分每公里，多半会被判异常。

停止：在模拟窗口按 Ctrl+C，等它把定位还原成真实 GPS 再关窗。直接杀进程会把手机定位留在最后一次写入的位置。

## 疑难排查

| 现象 | 原因与处理 |
|---|---|
| `pymobiledevice3 usbmux list` 返回 `[]` | 手机没点「信任」，或 Apple USB 驱动没绑上。微软更新目录里部分 cab（如 552.0.0.0）只有 `[Apple.NTamd64]`/`NTARM64` 段，x64 永远不绑定；用带 `NTamd64` 的 538a 包（GUID `0bc332b5-0655-4d9f-94a2-c338e31ea4b7`）。装好设备名变成 `Apple Mobile Device USB Composite Device`，`Service=usbccgp`，`LowerFilters=AppleLowerFilter` |
| `import win32security` 失败 | `pywin32` 的 DLL 要进 `PYTHONPATH`：`.pylibs;.pylibs\win32;.pylibs\win32\lib;.pylibs\pywin32_system32`。用 venv 时不涉及 |
| pip 卡在 hexdump 或 `Failed building wheel` | hexdump 3.3 只有 sdist。`scripts/setup_deps.py` 会从 PyPI 解出 `hexdump.py` 再重试 |
| `tempfile.mkdtemp` 报 `WinError 5` | 某些磁盘上 `os.mkdir(path, 0o700)` 会造出不可写目录。把 `TMP`/`TEMP` 指到 `%LOCALAPPDATA%\Temp` 下的可写目录 |
| app 里步频是 0 | 传感器不可注入，见「已知限制」 |
| `main.py` 启动后日志 0 字节、CPU 不动 | 上次实例没杀干净，两个进程互杀。提权 `Stop-Process` 所有 `main.py` 与 `pymobiledevice3`，等 4 秒再启动 |

## 坐标系约定（最容易踩的坑）

```
高德/腾讯底图 (GCJ-02)  --gcj_to_bd09()-->  BD-09  --写入-->  route.txt
route.txt (BD-09)  --run.py 内部 bd09Towgs84()-->  WGS-84  -->  DvtProvider 写入手机
```

- `route.txt` 每行是 `{"lng": "...", "lat": "..."}`，必须是 BD-09，run.py 会再做一次 BD-09 → WGS-84
- 从 OSM、photon 拿到的是 WGS-84，先 `wgs84_to_bd09()`
- 从高德底图点出来的是 GCJ-02，用 `gcj_to_bd09()`，`planner/route_plan.py` 已内置
- 往返误差小于 1e-5 度（约 1.5 m），可忽略；`scripts/selfcheck.py` 会核对落点范围

## 自检

```powershell
python scripts\selfcheck.py
```

覆盖：模块导入、坐标偏移合理、`route.txt` 可被 `[{...}]` 解析、规划器 `GET /` 与 `GET /state` 与 `POST /save` 与 `POST /restart`、页面含 Leaflet 与高德瓦片、保存结果落在 BD-09 合理区间、仓库示例路线格式。退出码 0 表示全通过，CI 在 `.github/workflows/selfcheck.yml`。

## 已知限制

- 计步与步频无法注入：iOS 只开放 `LocationSimulation`，加速度计数据不可远程伪造。定位在动但手机静止时 app 步频显示 0（多数校园跑要求 80–280 步/分）。只能靠硬件：手机摇步器调到 160–180 次/分，或手摇（节拍器 165 BPM、上下 5–10 cm）
- 打卡旗帜：判定半径通常 20–30 m，`make_route_cover.py` 扫场可确保不漏；已知旗点坐标时用 `--flags "lat,lng;lat,lng"` 插进轨迹
- 只能连一台设备，且必须先挂 DDI（`run.ps1` 会自动尝试）
- 别直接关窗口：`main.py` 的 `finally` 会 `location_simulation.clear()`，正常 Ctrl+C 才会把定位还原成真实 GPS

## 目录

```
campus-run-sim/
├─ setup.ps1  run.ps1  planner.ps1      入口
├─ planner/   route_plan.py  planner.html
├─ tools/     make_route*.py
├─ windows/   start.ps1  restart_watch.ps1
├─ scripts/   selfcheck.py  setup_deps.py
└─ examples/  route.sample.txt
```

## 许可

MIT。定位仿真的使用请遵守所在学校或平台的规则，风险与后果由使用者承担。
