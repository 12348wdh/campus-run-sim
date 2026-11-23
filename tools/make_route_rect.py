"""Rounded-rectangle campus route generator with mandatory flag waypoints.

route.txt entry format: {"lng": "...", "lat": "..."}   (BD-09, because run.py applies bd09Towgs84)
Input coordinates are WGS-84 (what you read from OSM / Gaode "坐标拾取" needs BD09 so pass --in-bd09).
"""
import argparse
import json
import math

RC = 6378137.0


def wgs84_to_bd09(lat, lng):
    x_pi = math.pi * 3000.0 / 180.0
    a, ee = 6378245.0, 0.00669342162296594323

    def tlat(x, y):
        r = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
        r += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
        r += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
        r += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
        return r

    def tlng(x, y):
        r = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        r += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
        r += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
        r += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
        return r

    dlat = tlat(lng - 105.0, lat - 35.0)
    dlng = tlng(lng - 105.0, lat - 35.0)
    rad = lat / 180.0 * math.pi
    magic = 1 - ee * math.sin(rad) ** 2
    sq = math.sqrt(magic)
    dlat = dlat * 180.0 / ((a * (1 - ee)) / (magic * sq) * math.pi)
    dlng = dlng * 180.0 / (a / sq * math.cos(rad) * math.pi)
    glat, glng = lat + dlat, lng + dlng
    z = math.sqrt(glng * glng + glat * glat) + 0.00002 * math.sin(glat * x_pi)
    th = math.atan2(glat, glng) + 0.000003 * math.cos(glng * x_pi)
    return z * math.sin(th) + 0.006, z * math.cos(th) + 0.0065


def m_per_deg(lat):
    return (111320.0 * math.cos(math.radians(lat)), 110540.0)


def rounded_rect(lat, lng, length, width, r, step):
    """Vertices of a rounded rectangle centred on lat/lng, N-S = length, E-W = width."""
    mlat, mlng = m_per_deg(lat)
    hl, hw = length / 2.0, width / 2.0
    cx = [hl - r, hw - r, -hl + r, -hw + r]      # corners (y, x) sign pairs -> local metres
    pts = []
    # four straight edges + four quarter arcs, walking clockwise from north edge
    corners = [(hw - r, hl - r, 0.0), (-hl + r, hw - r, -90.0), (-hw + r, -hl + r, 180.0), (hl - r, -hw + r, 90.0)]

    def emit(x, y):
        pts.append((lat + y / mlat, lng + x / mlng))

    # start at north edge midpoint-ish, walk canonical order: N edge -> NE arc -> E edge -> SE arc -> S edge -> SW arc -> W edge -> NW arc
    steps_n = max(2, int(2 * (hw - r) / step))
    for i in range(steps_n):
        x = -(hw - r) + 2 * (hw - r) * i / steps_n
        emit(x, hl)
    for k, (sx, sy, base) in enumerate([(1, 1, 0), (1, -1, -90), (-1, -1, 180), (-1, 1, 90)]):
        cx_, cy_ = sx * (hw - r), sy * (hl - r)
        n_arc = max(3, int((math.pi / 2 * r) / step))
        for i in range(n_arc):
            ang = math.radians(base + 90.0 * i / n_arc)
            emit(cx_ + r * math.cos(ang), cy_ + r * math.sin(ang))
        if k < 3:
            nx, ny, nb = [(1, 1, 0), (1, -1, -90), (-1, -1, 180), (-1, 1, 90)][(k + 1) % 4]
            # straight edge after this arc
            ax1, ay1 = cx_ + r * math.cos(math.radians(base + 90)), cy_ + r * math.sin(math.radians(base + 90))
            ax2, ay2 = nx * (hw - r) + r * math.cos(math.radians(nb)), ny * (hl - r) + r * math.sin(math.radians(nb))
            n_edge = max(2, int(math.hypot(ax2 - ax1, ay2 - ay1) / step))
            for i in range(1, n_edge):
                t = i / n_edge
                emit(ax1 + (ax2 - ax1) * t, ay1 + (ay2 - ay1) * t)
    return pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True, help="centre latitude (WGS-84)")
    ap.add_argument("--lng", type=float, required=True, help="centre longitude (WGS-84)")
    ap.add_argument("--len", type=float, default=145.0, help="north-south length in metres")
    ap.add_argument("--wid", type=float, default=95.0, help="east-west width in metres")
    ap.add_argument("--corner-r", type=float, default=18.0, help="corner radius in metres")
    ap.add_argument("--step", type=float, default=4.0, help="sampling step in metres")
    ap.add_argument("--flags", default="", help='mandatory waypoints "lat,lng;lat,lng" (WGS-84), inserted in order')
    ap.add_argument("--out", default="route.txt")
    a = ap.parse_args()

    pts = rounded_rect(a.lat, a.lng, a.len, a.wid, a.corner_r, a.step)
    flags = []
    for chunk in [c.strip() for c in a.flags.split(";") if c.strip()]:
        flat, flng = [float(v) for v in chunk.split(",")]
        flags.append((flat, flng))

    # rotate the loop so it starts nearest the first flag, then splice each flag in at its closest point
    if flags:
        def dist_m(p, q):
            mlat, mlng = m_per_deg(p[0])
            return math.hypot((p[0] - q[0]) * mlat, (p[1] - q[1]) * mlng)
        best = min(range(len(pts)), key=lambda i: dist_m(pts[i], flags[0]))
        pts = pts[best:] + pts[:best]
        for f in flags:
            idx = min(range(len(pts)), key=lambda i: dist_m(pts[i], f))
            pts.insert(idx + 1, f)

    bd = [wgs84_to_bd09(p[0], p[1]) for p in pts]
    body = ",\n".join('{"lng": "%s", "lat": "%s"}' % (f"{b[1]:.10f}", f"{b[0]:.10f}") for b in bd)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(body)

    lap = 0.0
    mlat, mlng = m_per_deg(a.lat)
    for i in range(len(pts)):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        lap += math.hypot((q[0] - p[0]) * mlat, (q[1] - p[1]) * mlng)
    print(f"wrote {a.out}: {len(pts)} pts, flags {len(flags)}, lap {lap:.1f} m, 1km = {1000/lap:.2f} laps")


if __name__ == "__main__":
    main()
