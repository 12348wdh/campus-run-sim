"""Self-check: validates tooling, coordinate math, planner HTTP surface and page assets.

Run:  python scripts/selfcheck.py
Exit code 0 = all checks passed.
"""
import json
import os
import subprocess
import sys
import shutil
import tempfile
import threading
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, os.path.join(REPO, "planner"))

FAILS = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (("  " + detail) if detail else ""))
    if not ok:
        FAILS.append(name)


def main():
    import make_route_loop
    import make_route_rect
    import make_route_cover
    import make_route
    check("import route generators", True)

    lat, lng = 30.9283099, 121.6896685
    bd = make_route_rect.wgs84_to_bd09(lat, lng)
    check("wgs84->bd09 offset sane", 30.93 < bd[0] < 30.94 and 121.69 < bd[1] < 121.71, str(bd))

    loop = make_route_loop.loop_points(lat, lng, 130, 72, 16, 4)
    check("loop point count", len(loop) > 50, str(len(loop)))

    tmpdir = tempfile.mkdtemp()
    try:
        tmp = os.path.join(tmpdir, "route_check.txt")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(",\n".join('{"lng": "%s", "lat": "%s"}' % (f"{p[1]:.10f}", f"{p[0]:.10f}") for p in loop))
        text = open(tmp, encoding="utf-8").read()
        parsed = json.loads("[" + text + "]")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    check("route.txt parses as json list", len(parsed) == len(loop))
    raw_sample = open(os.path.join(REPO, "examples", "route.sample.txt"), "rb").read()
    rows = json.loads("[" + raw_sample.decode("utf-8").strip() + "]")
    check("example route parses, LF only, BD-09 range",
          len(rows) > 100 and b"\r" not in raw_sample
          and (float(rows[0]["lat"]), float(rows[0]["lng"])) != (float(rows[-1]["lat"]), float(rows[-1]["lng"]))
          and all(30.9 < float(r["lat"]) < 30.95 and 121.68 < float(r["lng"]) < 121.72 for r in rows),
          str(len(rows)) + " pts")

    port = 8951
    env = dict(os.environ, IOSRUN_ROOT=REPO, PLAN_PORT=str(port))
    proc = subprocess.Popen([sys.executable, os.path.join(REPO, "planner", "route_plan.py")],
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        ok = False
        for _ in range(40):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1) as resp:
                    page = resp.read().decode("utf-8")
                    ok = resp.status == 200
                break
            except Exception:
                time.sleep(0.25)
        check("planner GET /", ok)
        check("page loads leaflet + amap tiles",
              "leaflet" in page.lower() and "autonavi.com" in page, str(len(page)) + " bytes")

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/state", timeout=2) as resp:
            state = json.loads(resp.read().decode("utf-8"))
        check("planner GET /state", "points" in state, str(state.get("points")))

        body = json.dumps({"points": [[lat, lng], [lat + 0.001, lng + 0.001], [lat + 0.001, lng - 0.001]],
                           "closed": True, "densify_m": 4}).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{port}/save", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            saved = json.loads(resp.read().decode("utf-8"))
        check("planner POST /save", saved.get("ok") and saved.get("points", 0) > 10, str(saved.get("lap")))

        rows = json.loads("[" + open(os.path.join(REPO, "route.txt"), encoding="utf-8").read() + "]")
        check("saved route.txt in BD-09 range",
              all(30.9 < float(r["lat"]) < 30.95 and 121.68 < float(r["lng"]) < 121.72 for r in rows),
              str(len(rows)))

        req = urllib.request.Request(f"http://127.0.0.1:{port}/restart", data=b"{}",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            rst = json.loads(resp.read().decode("utf-8"))
        check("planner POST /restart writes trigger", rst.get("ok") and os.path.exists(os.path.join(REPO, ".restart")))
    finally:
        proc.terminate()
        proc.wait(timeout=5)
        try:
            os.remove(os.path.join(REPO, "route.txt"))
            os.remove(os.path.join(REPO, ".restart"))
        except OSError:
            pass

    print("\n%d checks failed" % len(FAILS) if FAILS else "\nall checks passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
