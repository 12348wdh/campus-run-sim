"""Route planner server for iOSRealRun-cli-18.

Draw a polyline on an Amap (GCJ-02) basemap in the browser, save it as route.txt in BD-09
(what run.py expects, because run.py applies bd09Towgs84 before pushing to the device),
then ask the elevated supervisor (windows/restart_watch.ps1) to restart the simulation.

Endpoints
  GET  /         planner page
  GET  /state    {"points": n} of the current route.txt
  POST /save     {"points": [[lat,lng],...], "closed": true, "densify_m": 4}
  POST /restart  touches <root>/.restart so the supervisor restarts main.py

Environment
  IOSRUN_ROOT  directory that holds route.txt / main.py (default: current working directory)
  PLAN_PORT    listen port (default 8850)
"""
import json
import math
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.abspath(os.environ.get("IOSRUN_ROOT") or os.getcwd())
ROUTE = os.path.join(ROOT, "route.txt")
FLAG = os.path.join(ROOT, ".restart")
HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "planner.html")
PORT = int(os.environ.get("PLAN_PORT", "8850"))


def gcj_to_bd09(lat, lng):
    """GCJ-02 (Amap) -> BD-09 (Baidu), the convention used by route.txt."""
    x_pi = math.pi * 3000.0 / 180.0
    z = math.sqrt(lng * lng + lat * lat) + 0.00002 * math.sin(lat * x_pi)
    th = math.atan2(lat, lng) + 0.000003 * math.cos(lng * x_pi)
    return z * math.sin(th) + 0.006, z * math.cos(th) + 0.0065


def dist_m(a, b):
    mlat = 110540.0
    mlng = 111320.0 * math.cos(math.radians((a[0] + b[0]) / 2.0))
    return math.hypot((b[0] - a[0]) * mlat, (b[1] - a[1]) * mlng)


def densify(points, step):
    out = []
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        n = max(1, int(dist_m(a, b) / step))
        for k in range(n):
            t = k / n
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    out.append(points[-1])
    return out


def write_route(points, closed, step):
    pts = list(points)
    if closed and len(pts) > 2:
        pts.append(pts[0])
    dense = densify(pts, step)
    bd = [gcj_to_bd09(p[0], p[1]) for p in dense]
    body = ",\n".join('{"lng": "%s", "lat": "%s"}' % (f"{b[1]:.10f}", f"{b[0]:.10f}") for b in bd)
    with open(ROUTE, "w", encoding="utf-8") as fh:
        fh.write(body)
    lap = sum(dist_m(dense[i], dense[i + 1]) for i in range(len(dense) - 1))
    return len(dense), lap


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(HTML, "rb") as fh:
                self._send(200, fh.read(), "text/html; charset=utf-8")
        elif self.path == "/state":
            try:
                with open(ROUTE, encoding="utf-8") as fh:
                    n = fh.read().count('"lng"')
                self._send(200, json.dumps({"points": n, "root": ROOT}))
            except OSError as exc:
                self._send(200, json.dumps({"points": 0, "root": ROOT, "error": str(exc)}))
        else:
            self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            payload = {}
        if self.path == "/save":
            points = [(float(p[0]), float(p[1])) for p in payload.get("points", [])]
            if len(points) < 2:
                self._send(400, json.dumps({"ok": False, "error": "need at least 2 points"}))
                return
            n, lap = write_route(points, bool(payload.get("closed")), float(payload.get("densify_m", 4.0)))
            self._send(200, json.dumps({"ok": True, "points": n, "lap": round(lap, 1), "file": ROUTE}))
        elif self.path == "/restart":
            with open(FLAG, "w", encoding="utf-8") as fh:
                fh.write(str(time.time()))
            self._send(200, json.dumps({"ok": True, "triggered": True, "flag": FLAG}))
        else:
            self._send(404, json.dumps({"error": "not found"}))


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"planner on http://127.0.0.1:{PORT}  root={ROOT}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
