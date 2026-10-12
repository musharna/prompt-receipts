"""The gallery of receipts people send in (SITE/g/): checks the receipt link in a GitHub issue, and adds it to
gallery.json when the repo's owner labels the issue `gallery`. Standard library only.

  python3 tools/gallery.py check EVENT.json                print the issue's preview, or why it can't go in (exit 1)
  python3 tools/gallery.py add EVENT.json gallery.json     check it again and add it (exit 1 if it can't go in)
  python3 tools/gallery.py seed index.html gallery.json    the site's own runs

EVENT.json is the issue event GitHub Actions saves at $GITHUB_EVENT_PATH. A receipt's text can't show whether
someone edited it, so the gallery shows each one as sent."""

import base64
import binascii
import datetime
import json
import os
import re
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from receipt import SITE, parts  # noqa: E402

MAX_LINK = 20_000  # characters after r1.; receipt.py warns past 2,000
MAX_TEXT = 64_000  # bytes a link may unpack to
FIELD = 200  # characters kept of each field
LINK = re.compile(r"#?(r1\.[A-Za-z0-9_-]+)")
HEAD = re.compile(r"(Receipt|Reported) v(\d+(?:\.\d+)*) · (.+)")


class Refused(Exception):
    """why a receipt can't go in, in words for the person who sent it"""


def decode(token):
    """r1.<base64url of raw deflate> -> the receipt's text"""
    if not token.startswith("r1."):
        raise Refused("the link has no `r1.` receipt in it")
    b64 = token[3:]
    if len(b64) > MAX_LINK:
        raise Refused(f"the link is longer than {MAX_LINK:,} characters")
    if len(b64) % 4 == 1:
        raise Refused("the link is cut off")
    try:
        raw = base64.urlsafe_b64decode(b64 + "=" * (-len(b64) % 4))
    except (binascii.Error, ValueError):
        raise Refused("the link is not in the expected form") from None
    d = zlib.decompressobj(-15)
    try:
        data = d.decompress(raw, MAX_TEXT + 1)
    except zlib.error:
        raise Refused("the link does not unpack; it may be cut off") from None
    if len(data) > MAX_TEXT or d.unconsumed_tail:
        raise Refused(f"the receipt unpacks to more than {MAX_TEXT:,} bytes")
    if not d.eof:
        raise Refused("the link is cut off")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise Refused("the receipt is not UTF-8 text") from None
    if re.search(r"[\x00-\x09\x0b-\x1f\x7f]", text):
        raise Refused("the receipt has control characters in it")
    if not HEAD.fullmatch(text.split("\n")[0]):
        raise Refused(
            "it isn't a receipt: the first line should start `Receipt v` or `Reported v`"
        )
    return text


def find_link(body):
    """-> the one r1. token in an issue's text"""
    found = list(dict.fromkeys(LINK.findall(body or "")))
    if not found:
        raise Refused(
            "there's no receipt link in the issue (one made with `receipt.py --link`)"
        )
    if len(found) > 1:
        raise Refused(
            "there's more than one receipt link in the issue; send one per issue"
        )
    return found[0]


def cut(s):
    s = " ".join(s.split())
    return s if len(s) <= FIELD else s[: FIELD - 1] + "…"


def entry(token):
    """a receipt link -> what the gallery shows of it"""
    text = decode(token)
    head, asked, made, took = parts(text)
    kind, version, rest = HEAD.fullmatch(head).groups()
    bits = rest.split(" · ")
    if bits[0] == "Comparison":
        raise Refused("it's a comparison of several runs; send each run's own receipt")
    tool, tool_version = re.fullmatch(r"(.*?)(?: (\d[\w.+-]*))?", bits[0]).groups()
    date = next((b for b in bits[1:] if not b.startswith("no. ")), "")
    said = {}
    for label, values in asked + made + took:
        said.setdefault(label.strip(), " ".join(v.strip() for v in values))
    model = said.get("model", "").split(" · ")[0].split(" (")[0]
    cost = said.get("cost", "")
    usd = re.match(r"\$([\d,]+(?:\.\d+)?)", cost)
    prompt = said.get("prompt") or said.get("prompts") or ""
    return {
        "link": token,
        "kind": "reported" if kind == "Reported" else "sent",
        "receipt": version,
        "tool": cut(tool),
        "tool_version": tool_version or "",
        "date": cut(date),
        "model": cut(model),
        "cost": cut(cost.split(" (")[0]),
        "usd": float(usd.group(1).replace(",", "")) if usd else None,
        "time": cut(said.get("time", "").split(" · ")[0].split(" (")[0]),
        "prompt": cut(prompt),
    }


def from_issue(event):
    """an issue event -> (the issue, its entry)"""
    issue = event["issue"]
    e = entry(find_link(issue.get("body")))
    e.update(issue=issue["number"], by=issue["user"]["login"])
    return issue, e


def fence(text):
    """a code fence longer than any run of backticks in text, so the text can't close it"""
    run = max((len(m) for m in re.findall(r"`+", text)), default=0)
    return "`" * max(3, run + 1)


def preview(e):
    text = decode(e["link"])
    f = fence(text)
    kind = (
        "a reported receipt: what someone's post says, stamped REPORTED"
        if e["kind"] == "reported"
        else "a receipt, shown as sent: the gallery can't check it against the log"
    )
    return (
        f"Thanks! This can go in [the gallery]({SITE}g/) once the repo's owner adds the `gallery` label. "
        f"It's {kind}. Everything in it will be public, so check there's nothing private in the prompt.\n\n"
        f"{f}\n{text}\n{f}\n\n[Open it as a link]({SITE}r/#{e['link']})"
    )


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(path, entries):
    """one entry per line, so each addition is a one-line diff"""
    rows = ",\n".join(
        json.dumps(e, ensure_ascii=False, sort_keys=True) for e in entries
    )
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("[\n" + rows + "\n]\n")


def add(event, path, today=None):
    issue, e = from_issue(event)
    entries = load(path)
    for old in entries:
        if old["link"] == e["link"]:
            where = (
                f"issue #{old['issue']}" if old.get("issue") else "the site's own runs"
            )
            raise Refused(f"this receipt is in the gallery already (from {where})")
        if old.get("issue") == e["issue"]:
            raise Refused(f"issue #{e['issue']} is in the gallery already")
    e["added"] = (today or datetime.date.today()).isoformat()
    entries.append(e)
    save(path, entries)
    return e


def seed(index_html, path):
    """the site's own runs, one entry per receipt link on its cards"""
    with open(index_html, encoding="utf-8") as fh:
        html = fh.read()
    entries = []
    for card in html.split("<article ")[1:]:
        card_id = re.match(r'id="([\w-]+)"', card).group(1)
        for token in re.findall(r'href="[^"]*/r/#(r1\.[A-Za-z0-9_-]+)"', card):
            e = entry(token)
            e.update(kind="site", card=card_id, by="Prompt Receipts")
            entries.append(e)
    save(path, entries)
    return entries


def main(argv):
    # Windows writes pipes in its old code page, which has no "·" for most of it; the receipt is UTF-8
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    if len(argv) < 2 or argv[0] not in ("check", "add", "seed"):
        sys.exit(__doc__)
    try:
        if argv[0] == "seed":
            print(
                f"gallery: {len(seed(argv[1], argv[2]))} receipts from {argv[1]}",
                file=sys.stderr,
            )
            return 0
        with open(argv[1], encoding="utf-8") as fh:
            event = json.load(fh)
        if argv[0] == "check":
            print(preview(from_issue(event)[1]))
        else:
            e = add(event, argv[2])
            print(f"Added to [the gallery]({SITE}g/#i{e['issue']}). Thanks!")
    except Refused as why:
        print(f"This can't go in the gallery: {why}.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
