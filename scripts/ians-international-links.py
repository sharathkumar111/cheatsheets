#!/usr/bin/env python3
"""List IANS Live international story links published in a time window (IST).

Reads https://ianslive.in/category/international/<page> and keeps only the
main category listing (entry-title links), not sidebar stories. IANS article
URLs end in a YYYYMMDDHHMMSS timestamp in IST, which is used for the window.

Usage:
  python3 scripts/ians-international-links.py                  # today, 14:00 -> now (Sun 06:00 -> now)
  python3 scripts/ians-international-links.py --start 06:00 --end 21:00
  python3 scripts/ians-international-links.py --date 2026-11-21 --start 14:00 --end 21:00
  python3 scripts/ians-international-links.py --extra URL [URL ...]   # append same-day links not found

Output: one link per line, a blank line between links, latest first.
Links passed with --extra (same-day ones not found) go at the end.
"""
import argparse
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
BASE = "https://ianslive.in/category/international/{}"
LINK = re.compile(
    r'class="entry-title"[^>]*>\s*<a[^>]+href="(https://ianslive\.in/[a-z0-9-]+-(\d{14}))"'
)
STAMP = re.compile(r"-(\d{14})/?$")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (links-digest)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def main():
    now = datetime.now(IST)
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="YYYY-MM-DD in IST (default: today)")
    p.add_argument("--start", help="HH:MM IST (default: 06:00 on Sunday, else 14:00)")
    p.add_argument("--end", help="HH:MM IST (default: now)")
    p.add_argument("--max-pages", type=int, default=10)
    p.add_argument("--extra", nargs="*", default=[], help="links to append if same-day and missing")
    a = p.parse_args()

    day = datetime.strptime(a.date, "%Y-%m-%d").date() if a.date else now.date()
    start = a.start or ("06:00" if day.weekday() == 6 else "14:00")
    end = a.end or now.strftime("%H:%M")
    ymd = day.strftime("%Y%m%d")
    lo = ymd + start.replace(":", "") + "00"
    hi = ymd + end.replace(":", "") + "59"

    found = {}
    for page in range(1, a.max_pages + 1):
        stamps = []
        for url, ts in LINK.findall(fetch(BASE.format(page))):
            stamps.append(ts)
            if lo <= ts <= hi:
                found[url] = ts
        if not stamps or min(stamps) < lo:
            break

    links = [u for u, _ in sorted(found.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)]
    extras = []
    for u in a.extra:
        m = STAMP.search(u.strip())
        if m and m.group(1).startswith(ymd) and u.strip() not in found:
            extras.append(u.strip())

    out = links + extras
    if not out:
        print(f"No IANS international links between {start} and {end} IST on {day}.", file=sys.stderr)
        return 1
    print("\n\n".join(out))
    print(f"\n{len(links)} links, {start}-{end} IST, {day}"
          + (f"; {len(extras)} added at the end" if extras else ""), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
