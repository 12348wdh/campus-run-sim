#!/usr/bin/env python3
"""Install pymobiledevice3 deps into the active interpreter, tolerating hexdump 3.3 (sdist only)."""
import importlib.util, json, os, re, subprocess, sys, urllib.request, zipfile, io

REQ = [
    ("pymobiledevice3", "9.12.0"),
    ("PyYAML", "6.0.3"),
    ("geopy", "2.4.1"),
    ("geographiclib", "2.1"),
    ("pywin32", "312"),
]


def pip(*args: str) -> int:
    print("  pip", " ".join(args), flush=True)
    return subprocess.call([sys.executable, "-m", "pip", *args])


def have_hexdump() -> bool:
    return importlib.util.find_spec("hexdump") is not None


def install_hexdump() -> bool:
    """hexdump 3.3 ships no wheel; drop the pure-python module in place."""
    try:
        meta = json.load(urllib.request.urlopen("https://pypi.org/pypi/hexdump/json", timeout=30))
        url = [f["url"] for f in meta["releases"]["3.3"] if f["packagetype"] == "sdist"][0]
        blob = urllib.request.urlopen(url, timeout=60).read()
        zf = zipfile.ZipFile(io.BytesIO(blob))
        src = [n for n in zf.namelist() if n.endswith("hexdump.py")][0]
        site = [p for p in sys.path if p.endswith("site-packages")][0]
        with open(os.path.join(site, "hexdump.py"), "wb") as fh:
            fh.write(zf.read(src))
        d = os.path.join(site, "hexdump-3.3.dist-info")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "METADATA"), "w", encoding="utf-8") as fh:
            fh.write("Metadata-Version: 2.1\nName: hexdump\nVersion: 3.3\n")
        with open(os.path.join(d, "INSTALLER"), "w", encoding="utf-8") as fh:
            fh.write("manual\n")
        with open(os.path.join(d, "RECORD"), "w", encoding="utf-8") as fh:
            fh.write("")
        print("  hexdump 3.3 installed from sdist (no wheel for this CPython)")
        return True
    except Exception as exc:  # noqa: BLE001
        print("  hexdump bootstrap failed:", exc)
        return False


def main() -> int:
    req = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "requirements.txt")
    print("[1/3] hexdump (sdist only, install before pip resolver)")
    if not have_hexdump():
        install_hexdump()
    print("[2/3] requirements")
    ok = pip("install", "--disable-pip-version-check", "-r", req) == 0
    if not ok:
        print("  retry with --no-build-isolation")
        ok = pip("install", "--disable-pip-version-check", "--no-build-isolation", "-r", req) == 0
    print("[3/3] verify imports")
    probe = subprocess.run(
        [sys.executable, "-c", "import pymobiledevice3, yaml, geopy, geographiclib, hexdump; print('imports ok')"],
        capture_output=True, text=True)
    print("  " + (probe.stdout.strip() or probe.stderr.strip().splitlines()[-1]))
    return 0 if probe.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
