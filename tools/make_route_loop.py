"""Rounded-rectangle loop generator (stadium / running-track shaped closed loop).

Walks the perimeter in one consistent direction:
  NE arc -> north edge -> NW arc -> west edge -> SW arc -> south edge -> SE arc -> east edge
Coordinates in are WGS-84; route.txt is written in BD-09 (run.py applies bd09Towgs84).
"""
import argparse
import math

from make_route_rect import m_per_deg, wgs84_to_bd09


def loop_points(lat, lng, length, width, r, step):
    mlat, mlng = m_per_deg(lat)
    hl, hw = length / 2.0, width / 2.0
    r = min(r, hw - 1.0, hl - 1.0)
    a, b = hw - r, hl - r
    pts = []

    def emit(x, y):
        pts.append((lat + y / mlat, lng + x / mlng))

    def arc(cx, cy, a0, a1):
        n = max(4, int(abs(math.radians(a1 - a0)) * r / step))
        for i in range(n + 1):
            ang = math.radians(a0 + (a1 - a0) * i / n)
            emit(cx + r * math.cos(ang), cy + r * math.sin(ang))

    def line(x0, y0, x1, y1):
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) / step))
        for i in range(1, n + 1):
            t = i / n
            emit(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)

    arc(a, b, 0.0, 90.0)
    line(a, hl, -a, hl)
    arc(-a, b, 90.0, 180.0)
    line(-hw, b, -hw, -b)
    arc(-a, -b, 180.0, 270.0)
    line(-a, -hl, a, -hl)
    arc(a, -b, 270.0, 360.0)
    line(hw, -b, hw, b)
    return pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True, help="loop centre latitude (WGS-84)")
    ap.add_argument("--lng", type=float, required=True, help="loop centre longitude (WGS-84)")
    ap.add_argument("--len", type=float, default=130.0, help="north-south extent in metres")
    ap.add_argument("--wid", type=float, default=72.0, help="east-west extent in metres")
    ap.add_argument("--corner-r", type=float, default=16.0)
    ap.add_argument("--step", type=float, default=4.0)
    ap.add_argument("--flags", default="", help='waypoints "lat,lng;lat,lng" (WGS-84) spliced in, in order')
    ap.add_argument("--out", default="route.txt")
    a = ap.parse_args()

    pts = loop_points(a.lat, a.lng, a.len, a.wid, a.corner_r, a.step)
    for chunk in [c.strip() for c in a.flags.split(";") if c.strip()]:
        flat, flng = [float(v) for v in chunk.split(",")]
        mlat, mlng = m_per_deg(flat)
        idx = min(range(len(pts)), key=lambda i: math.hypot((pts[i][0] - flat) * mlat, (pts[i][1] - flng) * mlng))
        pts.insert(idx + 1, (flat, flng))

    bd = [wgs84_to_bd09(p[0], p[1]) for p in pts]
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(",\n".join('{"lng": "%s", "lat": "%s"}' % (f"{q[1]:.10f}", f"{q[0]:.10f}") for q in bd))

    mlat, mlng = m_per_deg(a.lat)
    lap = sum(math.hypot((pts[(i + 1) % len(pts)][0] - pts[i][0]) * mlat,
                         (pts[(i + 1) % len(pts)][1] - pts[i][1]) * mlng) for i in range(len(pts)))
    print(f"wrote {a.out}: {len(pts)} pts, lap {lap:.1f} m, 1km = {1000/lap:.2f} laps")


if __name__ == "__main__":
    main()
