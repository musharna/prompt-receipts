"""Refresh the price table inside receipt.py from LiteLLM's model_prices_and_context_window.json.

usage: python3 tools/update_prices.py            download the newest copy and note its commit and date
       python3 tools/update_prices.py FILE LABEL  use a file you already have, labelled LABEL

Only Anthropic and OpenAI models are kept, and only the prices receipt.py uses."""

import datetime
import importlib.util
import json
import os
import pprint
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RECEIPT = os.path.join(HERE, "receipt.py")
REPO = "BerriAI/litellm"
NAME = "model_prices_and_context_window.json"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "prompt-receipts"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    if len(sys.argv) == 3:
        with open(sys.argv[1], encoding="utf-8") as f:
            litellm = json.load(f)
        label = sys.argv[2]
    elif len(sys.argv) == 1:
        commit = json.loads(
            get(f"https://api.github.com/repos/{REPO}/commits?path={NAME}&per_page=1")
        )[0]
        sha = commit["sha"]
        day = datetime.date.fromisoformat(commit["commit"]["committer"]["date"][:10])
        litellm = json.loads(
            get(f"https://raw.githubusercontent.com/{REPO}/{sha}/{NAME}")
        )
        label = f"LiteLLM {sha[:7]}, {day.day} {day:%b %Y}"
    else:
        sys.exit(__doc__)
    spec = importlib.util.spec_from_file_location("receipt", RECEIPT)
    receipt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(receipt)
    table = receipt.price_table(litellm)
    if not any(k.startswith("claude-") for k in table) or not any(
        k.startswith("gpt-") for k in table
    ):
        sys.exit(
            f"update_prices: no Claude or GPT prices found ({len(table)} models); not written"
        )
    with open(RECEIPT, encoding="utf-8") as f:
        src = f.read()
    block = (
        "# --- prices start ---\n"
        f"PRICES_FROM = {label!r}\n"
        f"PRICES = {pprint.pformat(table, width=110, sort_dicts=True)}\n"
        "# --- prices end ---"
    )
    new, n = re.subn(
        r"# --- prices start ---\n.*?# --- prices end ---",
        lambda _: block,
        src,
        count=1,
        flags=re.S,
    )
    if n != 1:
        sys.exit("update_prices: the price markers are missing from receipt.py")
    with open(RECEIPT, "w", encoding="utf-8", newline="\n") as f:
        f.write(new)
    print(f"update_prices: {len(table)} models, {label}")


if __name__ == "__main__":
    main()
