# Contributing

1. `python scripts/selfcheck.py` 必须全通过（CI 也跑这一条）
2. 新增路线生成器请放在 `tools/`，复用 `make_route_rect.py` 里的 `wgs84_to_bd09()` 与 `m_per_deg()`，不要自带一套换算
3. 坐标一律"输入端 WGS-84 / GCJ-02，落盘 BD-09"，写文件前用 `scripts/selfcheck.py` 的区间断言自检
4. Windows 脚本只用 PowerShell 5.1 兼容语法（不要 `??`、三元运算符）

## 已知边界

- 计步/步频无法通过 pymobiledevice3 注入，属 iOS 侧限制，不要试图用改 app 或 hook 手机解决
- `route.txt` 必须是 BD-09，因为 run.py 还会再做一次 BD-09→WGS-84
