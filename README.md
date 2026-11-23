# campus-run-sim — iOSRealRun-cli-18 增强工具集

在 Windows 上把 iPhone 的定位仿真成校园跑路线，并配套一个**网页画线规划器**、**免 UAC 的热重启守护**、**三种路线生成器**。

基于 [MTDickens/iOSRealRun-cli-18](https://github.com/MTDickens/iOSRealRun-cli-18)：本仓库不重复它的代码，只放**外围工具**——把"改坐标要手搓 JSON、重启要手动提权、路线画不直观"这三件事解决掉。

## 组成

| 文件 | 作用 |
|---|---|
| `planner/route_plan.py` | 本地 HTTP 服务（默认 8850）：托管规划页、写 route.txt、触发重启 |
| `planner/planner.html` | Leaflet + 高德瓦片，点击画线、拖动微调、实时算长度的规划页 |
| `tools/make_route.py` | 椭圆环线生成器，支持 `--campus` 地名地理编码（photon.komoot.io） |
| `tools/make_route_loop.py` | 跑道型圆角矩形环线（标准操场形状） |
| `tools/make_route_rect.py` | 任意圆角矩形，并提供 `wgs84_to_bd09()` / `m_per_deg()` 公共函数 |
| `tools/make_route_cover.py` | 蛇形扫场路线：线间距 ≤ 2×判定半径，保证区域内每个打卡点都被压到 |
| `windows/start.ps1` | 自提权启动器：杀旧进程 → 按需挂载 DDI → 跑 main.py 并 tee 日志 |
| `windows/restart_watch.ps1` | 提权守护：监听 `.restart` 文件，实现规划器一键热重启 |
| `scripts/selfcheck.py` | 自检：模块导入、坐标换算、route.txt 可解析、规划器 5 个接口、页面资源 |

## 坐标系约定（最容易踩的坑）

```
高德/腾讯底图 (GCJ-02)  --gcj_to_bd09()-->  BD-09  --写入-->  route.txt
route.txt (BD-09)  --run.py 内部 bd09Towgs84()-->  WGS-84  -->  DvtProvider 写入手机
```

- `route.txt` 的每行是 `{"lng": "...", "lat": "..."}`，**必须是 BD-09**，因为 run.py 会再做一次 BD-09→WGS-84
- 从 OSM / photon 拿到的是 WGS-84，要先 `wgs84_to_bd09()`
- 从高德底图上点出来的是 GCJ-02，用 `gcj_to_bd09()`（`planner/route_plan.py` 已内置）
- 往返误差 < 1e-5 度（≈1.5 m），可忽略；`scripts/selfcheck.py` 会核对落点范围

## 前置条件（Windows）

1. **iTunes 或 Apple Mobile Device Support**（必需，提供 usbmuxd）。Windows 版 iTunes 装完 `Apple Mobile Device Service` 应为 RUNNING，`127.0.0.1:27015` 在听
2. **Apple USB 驱动**：微软更新目录里的 “Apple Mobile Device USB Device” 包必须带 `[Apple.NTamd64]` 段。2026 年部分 cab（如 552.0.0.0）只有 `NTARM64`，在 x64 上永远不绑定，表现为 `pymobiledevice3 usbmux list` 一直返回 `[]`。可用 538a 包（GUID `0bc332b5-0655-4d9f-94a2-c338e31ea4b7`），装完设备名变成 `Apple Mobile Device USB Composite Device`，`Service=usbccgp`，`LowerFilters=AppleLowerFilter`
3. **iPhone 侧**：数据线连接 → 手机上点“信任” → 打开「开发者模式」（设置 → 隐私与安全性 → 开发者模式，重启生效）。`C:\ProgramData\Apple\Lockdown\<UDID>.plist` 出现即配对成功
4. **Python 3.12+**，以及 `pymobiledevice3==9.12.0`、`PyYAML`、`geopy`、`geographiclib`
5. **DDI**：`python -m pymobiledevice3 mounter auto-mount`（首次要联网下载 personalized image）

## 安装依赖（避开已知坑）

```powershell
# 1) 不要用 uv：AppData 缓存目录在某些机器上不可写
# 2) hexdump 3.3 只有 sdist，无 cp314 wheel，pip 构建会失败 —— 直接从 PyPI 解出单文件
python -c "import urllib.request,json,io,zipfile;d=json.load(urllib.request.urlopen('https://pypi.org/pypi/hexdump/json'));u=[f['url'] for f in d['releases']['3.3'] if f['packagetype']=='sdist'][0];open('hexdump.zip','wb').write(urllib.request.urlopen(u).read());z=zipfile.ZipFile('hexdump.zip');open('.pylibs/hexdump.py','wb').write(z.read('hexdump-3.3/hexdump.py'))"

# 3) 其余依赖 only-binary 装到 .pylibs（不要装进全局）
python -m pip install --only-binary=:all: --target .pylibs -r _deps.txt
python -m pip install --only-binary=:all: --target .pylibs pywin32==312 geographiclib==2.1
```

运行时 `PYTHONPATH` 必须是四段（`win32` 下要放 DLL，否则 `import win32security` 失败）：

```
.pylibs;.pylibs\win32;.pylibs\win32\lib;.pylibs\pywin32_system32
```

> 若 `os.mkdir(path, 0o700)` 在你的磁盘上造出不可写目录（`tempfile.mkdtemp` 直接 WinError 5），把 `TMP`/`TEMP` 指到 `%LOCALAPPDATA%\Temp` 下的可写目录，或用一个 `sitecustomize.py` 覆写 `os.mkdir` 忽略 mode。`windows/start.ps1` 会把 `USERPROFILE` 指到 `$root\pymd_home`，避免 pymobiledevice3 往不可写的家目录写状态。

## 用法

### A. 网页画线（推荐）

```powershell
$env:IOSRUN_ROOT = "D:\path\to\iOSRealRun-cli-18"
python planner\route_plan.py           # http://127.0.0.1:8850
```

1. 地图默认落在操场中心，点击加点，蓝线按顺序连线
2. 拖白边圆点微调，右键删点，「撤销 / 清空」
3. 勾「首尾相接成环」→ 环线；面板实时显示点数、长度、1 km 需跑几圈
4. 「卫星/路网」切换高德卫星图看清跑道边界
5. 「保存并重启模拟」→ 写 route.txt + 触发 `.restart` → 守护进程 2 秒内热重启模拟

### B. 命令行生成

```powershell
# 椭圆环线（一圈 350 m 左右）
python tools\make_route.py --lat 30.9323325 --lng 121.7003788 --r 68 --ratio 0.62 --n 90 --out route.txt

# 跑道型环线（400 m 标准场）
python tools\make_route_loop.py --lat 30.9283099 --lng 121.6896685 --len 130 --wid 72 --corner-r 16 --out route.txt

# 扫场：覆盖 150×100 m，线距 30 m，任意点在 15 m 内被压到
python tools\make_route_cover.py --lat 30.9283099 --lng 121.6896685 --len 150 --wid 100 --spacing 30 --out route.txt
```

`--lat/--lng` 一律填 **WGS-84**（OSM 上的田径场、Google 地图坐标），脚本内部转 BD-09。

### C. 启动模拟

```powershell
$env:IOSRUN_ROOT = "D:\path\to\iOSRealRun-cli-18"
powershell -ExecutionPolicy Bypass -File windows\start.ps1        # 一次性启动（会弹 UAC）
powershell -ExecutionPolicy Bypass -File windows\restart_watch.ps1 # 或启动常驻守护，之后热重启免 UAC
```

速度在 `config.yaml` 的 `v`（米/秒）：`2.9` ≈ 5'45"/km，适合校园跑判定；`5.56` 是原仓库默认（3'00"/km，多半会被判异常）。

## 自检

```powershell
python scripts\selfcheck.py
```

覆盖：模块可导入 → 坐标偏移合理 → route.txt 可被 `[{...}]` 解析 → 规划器 `GET /` / `GET /state` / `POST /save` / `POST /restart` → 页面含 Leaflet 与高德瓦片模板 → 保存结果落在 BD-09 合理区间。退出码 0 表示全通过。

## 已知限制

- **计步/步频无法注入**：iOS 只开放了 `LocationSimulation`，加速度计数据不可远程伪造。定位在动但手机静止时，app 的步频会显示 0（多数校园跑要求 80–280 步/分）。解决办法是硬件：手机摇步器调到 160–180 次/分，或手摇（节拍器 165 BPM，上下 5–10 cm）
- **打卡旗帜（旗帜/点位）**：判定半径通常 20–30 m，用 `make_route_cover.py` 扫场可确保不漏；若已知旗点坐标，用 `--flags "lat,lng;lat,lng"` 直接插入轨迹
- **只能连一台设备**，且必须先 mount DDI
- **不可直接关窗口**：main.py 的 `finally` 里会 `location_simulation.clear()`，正常退出（Ctrl+C）才会把定位还原成真实 GPS

## 目录

```
campus-run-sim/
├─ planner/   route_plan.py  planner.html
├─ tools/     make_route.py  make_route_loop.py  make_route_rect.py  make_route_cover.py
├─ windows/   start.ps1  restart_watch.ps1
├─ scripts/   selfcheck.py
└─ examples/  route.sample.txt
```

## 许可

MIT。定位仿真的使用请遵守所在学校/平台的规则，风险与后果由使用者承担。
