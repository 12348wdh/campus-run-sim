#!/usr/bin/env python3
"""Patch `v:` (m/s) in iOSRealRun config.yaml without touching other keys."""
import argparse
import os
import re
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=os.environ.get('IOSRUN_ROOT', '.'))
    ap.add_argument('--speed', type=float, required=True, help='2.9 = 5 min 45 s per km')
    args = ap.parse_args()
    cfg = os.path.join(args.root, 'config.yaml')
    if not os.path.isfile(cfg):
        print('config.yaml not found under', args.root)
        return 1
    raw = open(cfg, encoding='utf-8-sig').read()
    new, n = re.subn(r'(?m)^(\s*v:\s*)[0-9.]+', lambda m: m.group(1) + ('%g' % args.speed), raw)
    if n == 0:
        print('no v: key in', cfg)
        return 1
    open(cfg, 'w', encoding='utf-8', newline='\n').write(new)
    old = re.search(r'(?m)^\s*v:\s*([0-9.]+)', raw)
    print('v: %s -> %g  (%s)' % (old.group(1) if old else '?', args.speed, cfg))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())