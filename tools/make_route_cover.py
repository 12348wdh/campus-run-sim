"""Coverage (serpentine) route generator: sweeps the whole running zone so every flag inside is passed.

Flags in campus-run apps are hit when the track comes within a judgement radius (typically 20-30 m).
A lawn-mower sweep with lane spacing <= 2 x radius guarantees every flag inside the zone is touched
regardless of where it sits, and keeps cumulative distance growing evenly.

route.txt entries are BD-09 because run.py applies bd09Towgs84 before sending to the device.
"""
import argparse
import math

from make_route_rect import m_per_deg, wgs84_to_bd09


def serpentine(lat, lng, length, width, spacing, step):
    mlat, mlng = m_per_deg(lat)
    lanes = max(2, int(round(width / spacing)) + 1)
    pts = []

    def emit(y, x):
        pts.append((lat + y / mlat, lng + x / mlng))

    for i in range(lanes):
        x = -width / 2.0 + width * i / (lanes - 1)
        ys = [(-length / 2.0) + length * k / max(2, int(length / step)) for k in range(max(2, int(length / step)) + 1)]
        if i % 2 == 1:
            ys = list(reversed(ys))
        for y in ys:
            emit(y, x)
        if i < lanes - 1:
            nx = -width / 2.0 + width * (i + 1) / (lanes - 1)
            last_y = ys[-1]
            n = max(2, int(abs(nx - x) / step))
            for k in range(1, n):
                emit(last_y, x + (nx - x) * k / n)
    return pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lng", type=float, required=True)
    ap.add_argument("--len", type=float, default=140.0, help="north-south extent in metres")
    ap.add_argument("--wid", type=float, default=90.0, help="east-west extent in metres")
    ap.add_argument("--spacing", type=float, default=36.0, help="lane spacing in metres (<= 2x flag radius)")
    ap.add_argument("--step", type=float, default=4.0)
    ap.add_argument("--out", default="route.txt")
    a = ap.parse_args()

    pts = serpentine(a.lat, a.lng, a.len, a.wid, a.spacing, a.step)
    bd = [wgs84_to_bd09(p[0], p[1]) for p in pts]
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(",\n".join('{"lng": "%s", "lat": "%s"}' % (f"{b[1]:.10f}", f"{b[0]:.10f}") for b in bd))

    mlat, mlng = m_per_deg(a.lat)
    total = 0.0
    for i in range(len(pts) - 1):
        total += math.hypot((pts[i + 1][0] - pts[i][0]) * mlat, (pts[i + 1][1] - pts[i][1]) * mlng)
    print(f"wrote {a.out}: {len(pts)} pts, sweep {total:.0f} m, lanes {int(round(a.wid / a.spacing)) + 1}, spacing {a.spacing} m")


if __name__ == "__main__":
    main()
