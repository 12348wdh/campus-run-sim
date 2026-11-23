# -*- coding: utf-8 -*-
"""Build route.txt for iOSRealRun-cli-18.

route.txt points must be BD-09 (run.py converts BD-09 -> WGS-84 before pushing).

Examples
  python make_route.py --lat 31.0308 --lng 121.4420 --r 90 --n 80 --out route.txt
  python make_route.py --campus "上海交通大学闵行校区" --r 90 --n 80 --out route.txt
  python make_route.py --lat 31.0308 --lng 121.4420 --from-wgs84 --r 90 --n 80 --out route.txt
"""
import argparse, math, json, urllib.parse, urllib.request

PI = math.pi
AA = 6378245.0
EE = 0.00669342162296594323
XPI = PI * 3000.0 / 180.0

def _tlat(x, y):
    r = -100.0 + 2.0*x + 3.0*y + 0.2*y*y + 0.1*x*y + 0.2*math.sqrt(abs(x))
    r += (20.0*math.sin(6.0*x*PI) + 20.0*math.sin(2.0*x*PI)) * 2.0/3.0
    r += (20.0*math.sin(y*PI) + 40.0*math.sin(y/3.0*PI)) * 2.0/3.0
    r += (160.0*math.sin(y/12.0*PI) + 320*math.sin(y*PI/30.0)) * 2.0/3.0
    return r

def _tlon(x, y):
    r = 300.0 + x + 2.0*y + 0.1*x*x + 0.1*x*y + 0.1*math.sqrt(abs(x))
    r += (20.0*math.sin(6.0*x*PI) + 20.0*math.sin(2.0*x*PI)) * 2.0/3.0
    r += (20.0*math.sin(x*PI) + 40.0*math.sin(x/3.0*PI)) * 2.0/3.0
    r += (150.0*math.sin(x/12.0*PI) + 300.0*math.sin(x/30.0*PI)) * 2.0/3.0
    return r

def wgs84_to_bd09(lat, lng):
    dlat = _tlat(lng - 105.0, lat - 35.0)
    dlng = _tlon(lng - 105.0, lat - 35.0)
    rad = lat / 180.0 * PI
    magic = 1 - EE * math.sin(rad) ** 2
    sq = math.sqrt(magic)
    dlat = (dlat * 180.0) / (AA * (1 - EE) / (magic * sq) * PI)
    dlng = (dlng * 180.0) / (AA / sq * math.cos(rad) * PI)
    glat, glng = lat + dlat, lng + dlng
    z = math.sqrt(glng*glng + glat*glat) + 0.00002 * math.sin(glat * XPI)
    th = math.atan2(glat, glng) + 0.000003 * math.cos(glng * XPI)
    return z * math.sin(th) + 0.006, z * math.cos(th) + 0.0065

def geocode(name):
    q = urllib.parse.urlencode({"q": name, "format": "json", "limit": 1})
    req = urllib.request.Request("https://nominatim.openstreetmap.org/search?" + q,
                                 headers={"User-Agent": "iOSRealRun-route/1.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    if not data:
        raise SystemExit("geocode failed: " + name)
    return float(data[0]["lat"]), float(data[0]["lon"])

def ellipse(lat, lng, r_m, n, ratio):
    dlat = r_m / 111320.0
    dlng = r_m / (111320.0 * max(0.2, math.cos(math.radians(lat))))
    return [(lat + dlat*ratio*math.sin(2*PI*i/n), lng + dlng*math.cos(2*PI*i/n)) for i in range(n)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lng", type=float)
    ap.add_argument("--campus", help="place name to geocode (WGS-84 result, auto-converted)")
    ap.add_argument("--from-wgs84", action="store_true", help="given lat/lng are WGS-84")
    ap.add_argument("--r", type=float, default=80.0)
    ap.add_argument("--ratio", type=float, default=0.62)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--out", default="route.txt")
    a = ap.parse_args()

    if a.campus:
        lat, lng = geocode(a.campus)
        a.from_wgs84 = True
        print(f"geocoded {a.campus} -> WGS84 {lat},{lng}")
    elif a.lat is not None and a.lng is not None:
        lat, lng = a.lat, a.lng
    else:
        raise SystemExit("need --campus or --lat/--lng")

    if a.from_wgs84:
        lat, lng = wgs84_to_bd09(lat, lng)
        print(f"BD-09 center: {lat:.7f},{lng:.7f}")

    pts = ellipse(lat, lng, a.r, a.n, a.ratio)
    body = ",".join('{"lng":"%.15f","lat":"%.15f"}' % (lng_, lat_) for lat_, lng_ in pts)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"wrote {a.out}: {len(pts)} pts, center=({lat:.6f},{lng:.6f}), r={a.r}m")

if __name__ == "__main__":
    main()
