#!/usr/bin/env python3
"""List IANS Live international story links published in a time window (IST).

Reads https://ianslive.in/category/international/<page> and keeps only the
main category listing (entry-title links), not sidebar stories. The window and
the order use each article's own publication time (its article:published_time
tag). The YYYYMMDDHHMMSS stamp at the end of an IANS URL is when the story was
created, which can be hours before it was published, so it isn't used.

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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
BASE = "https://ianslive.in/category/international/{}"
LINK = re.compile(
    r'class="entry-title"[^>]*>\s*<a[^>]+href="(https://ianslive\.in/[a-z0-9-]+-(\d{14}))"'
)
PUBLISHED = re.compile(r'article:published_time"\s+content="([^"]+)"')


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (links-digest)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def published_ist(url):
    """Return the article's publication time in IST, or None if it can't be read."""
    try:
        m = PUBLISHED.search(fetch(url))
    except Exception:
        return None
    if not m:
        return None
    return datetime.fromisoformat(m.group(1)).astimezone(IST)


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
    def at(hhmm, sec):
        h, m = map(int, hhmm.split(":"))
        return datetime(day.year, day.month, day.day, h, m, sec, tzinfo=IST)

    lo, hi = at(start, 0), at(end, 59)
    day_lo, day_hi = at("00:00", 0), at("23:59", 59)

    found, seen = {}, set()
    with ThreadPoolExecutor(max_workers=8) as pool:
        for page in range(1, a.max_pages + 1):
            urls = [u for u, _ in LINK.findall(fetch(BASE.format(page))) if u not in seen]
            seen.update(urls)
            if not urls:
                break
            times = dict(zip(urls, pool.map(published_ist, urls)))
            for u, t in times.items():
                if t and lo <= t <= hi:
                    found[u] = t
            # The listing runs newest-published first: stop once a whole page is older.
            known = [t for t in times.values() if t]
            if known and max(known) < lo:
                break

        links = [u for u, _ in sorted(found.items(), key=lambda kv: kv[1], reverse=True)]
        extras = []
        wanted = [u.strip() for u in a.extra if u.strip() and u.strip() not in found]
        for u, t in zip(wanted, pool.map(published_ist, wanted)):
            if t and day_lo <= t <= day_hi:
                extras.append(u)

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
