"""Tally Prompt Receipts form responses from the Sheet's CSV export.

usage: python3 tools/tally.py <responses.csv> [--days 30] [--visits bare=N receipt=M]

Download the CSV from the responses Sheet (File > Download > CSV). Rows whose name or
prompt text starts with "TEST" are skipped. --visits takes GoatCounter visit counts per
page version so each version's report rate can be compared."""

import argparse
import collections
import csv
import datetime
import sys

PROMPT = "Which prompt did you run?"
MODEL = "Which tool and model?"
WORKED = "Did it work?"
TEXT = "Your prompt, exactly as you ran it"
NAME = "Name to credit you by"
ARM = "Page version (filled in for you, leave as is)"
OK = "Can we show your prompt and result on the site under CC BY 4.0?"

ap = argparse.ArgumentParser()
ap.add_argument("csv")
ap.add_argument("--days", type=int, default=30)
ap.add_argument("--visits", nargs="*", default=[])
a = ap.parse_args()

with open(a.csv, newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))
if rows:
    missing = [c for c in (PROMPT, MODEL, WORKED, TEXT, ARM) if c not in rows[0]]
    if missing:
        sys.exit(f"CSV is missing columns {missing}; got {list(rows[0])}")

real = [r for r in rows if not (r.get(NAME, "").startswith("TEST") or r.get(TEXT, "").startswith("TEST"))]
print(f"{len(rows)} rows, {len(rows) - len(real)} test rows skipped, {len(real)} reports")


def when(r):
    return datetime.datetime.strptime(r["Timestamp"], "%m/%d/%Y %H:%M:%S")


cut = datetime.datetime.now() - datetime.timedelta(days=a.days)
recent = [r for r in real if when(r) >= cut]
print(f"last {a.days} days: {len(recent)} reports (stop rule: fewer than 3 in a month)")


def table(title, key, rs):
    print(f"\n{title}")
    for k, n in collections.Counter(key(r) for r in rs).most_common():
        print(f"  {n:4d}  {k or '(blank)'}")


table("by page version", lambda r: r[ARM].strip(), real)
table("by prompt", lambda r: r[PROMPT], real)
table("by model", lambda r: r[MODEL], real)
table("did it work", lambda r: r[WORKED], real)

by_arm = collections.defaultdict(collections.Counter)
for r in real:
    by_arm[r[ARM].strip() or "(blank)"][r[WORKED]] += 1
print("\nworked, by page version")
for arm, c in sorted(by_arm.items()):
    print(f"  {arm:10s} " + ", ".join(f"{k}: {n}" for k, n in c.most_common()))

if a.visits:
    print("\nreports per 100 visits")
    for kv in a.visits:
        arm, n = kv.split("=")
        got = sum(1 for r in real if r[ARM].strip() == arm)
        print(f"  {arm:10s} {got} reports / {n} visits = {100 * got / int(n):.1f}")

shown = [r for r in real if r.get(OK, "").startswith("Yes")]
print(f"\n{len(shown)} reports agreed to be shown on the site")
for r in shown:
    print(f"  {r[PROMPT]} | {r[MODEL]} | {r[WORKED]} | {r.get(NAME) or '(no name)'}")
