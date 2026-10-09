"""Make a receipt for your own Claude Code, Codex or OpenCode run: what ran, how long, what it cost, what was switched on.

usage: python3 receipt.py [SESSION] [options]

  no SESSION       the newest Claude Code session for the current folder
  --codex          use Codex sessions instead; --opencode for OpenCode
  --list           list this folder's recent sessions; then --pick N to choose one
  --all            with --list or --pick: sessions from every folder, not just this one
  --last N         only your last N prompts
  --turns          one line per prompt: when, how long, what it cost, tool calls, files
  --turns 3-5      cover only prompts 3 to 5 (also 3, 3- or -5), and list them

  leaving things out (check the receipt before you share it):
  --hide a,b       drop parts: version, date, model, time, cost, items, billing, tokens, work, files, addons, hooks,
                   memory, settings
  --counts         numbers instead of names for skills, MCP servers, plugins, subagent types and memory files
  --rename a=b     show name a as b (repeatable); fails if a isn't on the receipt, so a typo can't leak it
  --prompt         also print your prompts (home folders become ~; stops if one holds an email address or a key)
  --reply          also print the model's last reply, checked the same way
  --recipe         also print the commands that rerun your prompts with the same model and effort
  --outcome TEXT   add your own words on how it went ("worked first try")
  --redact         replace email addresses and keys with [email] and [key] instead of stopping
  --prompt-id      add a short fingerprint of the prompt (not the prompt), so --compare can tell runs of one prompt
  --file-names     name the files the run wrote (off by default: only their count and types)

  output:
  --md, --json     wrap it for GitHub or Discord, or print it as JSON (hidden parts stay out)
  --out PATH       save it to a file (.txt, .md, .json or .png) or into a folder
  --png            with --out: draw it as a picture, for posting where text gets mangled
  --link           also print a link that shows the receipt on the site; the receipt is inside the link, so
                   nothing is uploaded
  --report         also print a link to the Prompt Receipts form with this receipt filled in
  --hook           read a Claude Code hook's input from stdin (for a SessionEnd hook; needs --out)
  --combine A B    add several --json receipts into one (one task spread over sessions)
  --compare A B    put several --json receipts side by side (one prompt on several models or efforts)
  --prices FILE    price the lines with another copy of LiteLLM's model_prices_and_context_window.json

  a record of what went in and came out:
  --record FILE    also save fingerprints (sha256) of every prompt, the system prompt, instruction files as
                   loaded, everything the tools showed the model, and the files it wrote: no text, only hashes
  --sign KEY       sign each saved file with your SSH key (ssh-keygen -Y sign), next to it as FILE.sig
  --verify FILE    check a signature, or with a record: say which of the other files given came in or out of it
  --signers FILE   with --verify: an allowed_signers file, to check whose key it was
  --bundle F.zip   save one zip (an RO-Crate) with the receipt, the record and the files the run wrote
  --shot           with --bundle: add a screenshot of the page the run made (needs Chrome, Edge or Chromium)

Paths, your email and account ids never print, and file contents only go in a --bundle. Standard library only.
Prompts and page text: https://musharna.github.io/prompt-receipts/ (CC BY 4.0)."""

import argparse
import base64
import bisect
import collections
import datetime
import glob
import functools
import hashlib
import html
import http.server
import itertools
import json
import mimetypes
import os
import re
import shlex
import shutil
import signal
import sqlite3
import struct
import subprocess
import sys
import tempfile
import textwrap
import threading
import unicodedata
import urllib.parse
import zipfile
import zlib

VERSION = "5.0"
ISSUES = "https://github.com/musharna/prompt-receipts/issues"
SITE = "https://musharna.github.io/prompt-receipts/"
LINK_BUDGET = 2000  # Discord cuts messages at 2,000 characters
FORM = (
    "https://docs.google.com/forms/d/e/1FAIpQLSfo7LHk0Ljj2NES_qAX3-OMIbxbql9fhCsSNSzVLF_bEXoXNA/viewform"
    "?usp=pp_url&entry.349092046=tool&entry.1393206370="
)
TOOLS = {"claude": "Claude Code", "codex": "Codex CLI", "opencode": "OpenCode"}
LOCAL = {"ollama", "lmstudio", "oss", "llama.cpp", "llamacpp", "local", "vllm"}
PLANS = {
    "claude_max": "Max plan",
    "claude_pro": "Pro plan",
    "claude_team": "Team plan",
    "claude_enterprise": "Enterprise plan",
}

PARTS = [
    "version",
    "date",
    "model",
    "time",
    "cost",
    "items",
    "billing",
    "tokens",
    "work",
    "files",
    "addons",
    "hooks",
    "memory",
    "settings",
]

# ---------- prices ----------

# API list prices in dollars per million tokens: input, cache read, cache write (5 min), cache write (1 h), output.
# An optional last item holds multipliers ("fast": fast mode, "us": US-only processing) and "above": [tokens,
# the five prices] for a call whose prompt is bigger than that. Made from LiteLLM's model_prices_and_context_window.json
# (MIT; the source ccusage, tokscale and codeburn use) by tools/update_prices.py: don't edit by hand.
# --- prices start ---
PRICES_FROM = "LiteLLM 05166e2, 9 Oct 2026"
PRICES = {
    "claude-fable-5": [10, 1, 12.5, 20, 50, {"us": 1.1}],
    "claude-fable-5-1": [10, 0.25, 12.5, 20, 50, {"us": 1.1}],
    "claude-haiku-4-5": [1, 0.1, 1.25, 2, 5],
    "claude-haiku-4-5-20251001": [1, 0.1, 1.25, 2, 5],
    "claude-haiku-5-5": [
        0.1,
        0.01,
        0.125,
        0.2,
        0.5,
        {"above": [100000, 0.5, 0.05, 0.625, 1, 2.5], "us": 1.1},
    ],
    "claude-mythos-5": [10, 1, 12.5, 20, 50, {"us": 1.1}],
    "claude-mythos-5-1": [10, 0.25, 12.5, 20, 50, {"us": 1.1}],
    "claude-mythos-preview": [10, 1, 12.5, 20, 50, {"us": 1.1}],
    "claude-opus-4-5": [5, 0.5, 6.25, 10, 25],
    "claude-opus-4-5-20251101": [5, 0.5, 6.25, 10, 25],
    "claude-opus-4-6": [5, 0.5, 6.25, 10, 25, {"us": 1.1}],
    "claude-opus-4-6-20260205": [5, 0.5, 6.25, 10, 25, {"us": 1.1}],
    "claude-opus-4-7": [5, 0.5, 6.25, 10, 25, {"us": 1.1}],
    "claude-opus-4-7-20260416": [5, 0.5, 6.25, 10, 25, {"us": 1.1}],
    "claude-opus-4-8": [5, 0.5, 6.25, 10, 25, {"fast": 2.0, "us": 1.1}],
    "claude-opus-5": [5, 0.5, 6.25, 10, 25, {"fast": 2.0, "us": 1.1}],
    "claude-opus-5-5": [4, 0.2, 5, 8, 20, {"fast": 2, "us": 1.1}],
    "claude-sonnet-4-5": [
        3,
        0.3,
        3.75,
        6,
        15,
        {"above": [200000, 6, 0.6, 7.5, 12, 22.5]},
    ],
    "claude-sonnet-4-5-20250929": [
        3,
        0.3,
        3.75,
        6,
        15,
        {"above": [200000, 6, 0.6, 7.5, 12, 22.5]},
    ],
    "claude-sonnet-4-6": [3, 0.3, 3.75, 6, 15, {"us": 1.1}],
    "claude-sonnet-5": [2, 0.2, 2.5, 4, 10, {"us": 1.1}],
    "claude-sonnet-5-5": [2, 0.1, 2.5, 4, 10, {"us": 1.1}],
    "gpt-5": [1.25, 0.125, 1.25, 1.25, 10],
    "gpt-5-2025-08-07": [1.25, 0.125, 1.25, 1.25, 10],
    "gpt-5-chat": [1.25, 0.125, 1.25, 1.25, 10],
    "gpt-5-chat-latest": [1.25, 0.125, 1.25, 1.25, 10],
    "gpt-5-codex": [1.25, 0.125, 1.25, 1.25, 10],
    "gpt-5-mini": [0.25, 0.025, 0.25, 0.25, 2],
    "gpt-5-mini-2025-08-07": [0.25, 0.025, 0.25, 0.25, 2],
    "gpt-5-nano": [0.05, 0.005, 0.05, 0.05, 0.4],
    "gpt-5-nano-2025-08-07": [0.05, 0.005, 0.05, 0.05, 0.4],
    "gpt-5-pro": [15, 15, 15, 15, 120],
    "gpt-5-pro-2025-10-06": [15, 15, 15, 15, 120],
    "gpt-5-search-api": [1.25, 0.125, 1.25, 1.25, 10],
    "gpt-5-search-api-2025-10-14": [1.25, 0.125, 1.25, 1.25, 10],
    "gpt-5.1": [1.25, 0.125, 1.25, 1.25, 10],
    "gpt-5.1-2025-11-13": [1.25, 0.125, 1.25, 1.25, 10],
    "gpt-5.1-chat-latest": [1.25, 0.125, 1.25, 1.25, 10],
    "gpt-5.1-codex": [1.25, 0.125, 1.25, 1.25, 10],
    "gpt-5.1-codex-max": [1.25, 0.125, 1.25, 1.25, 10],
    "gpt-5.1-codex-mini": [0.25, 0.025, 0.25, 0.25, 2],
    "gpt-5.2": [1.75, 0.175, 1.75, 1.75, 14],
    "gpt-5.2-2025-12-11": [1.75, 0.175, 1.75, 1.75, 14],
    "gpt-5.2-chat-latest": [1.75, 0.175, 1.75, 1.75, 14],
    "gpt-5.2-codex": [1.75, 0.175, 1.75, 1.75, 14],
    "gpt-5.2-pro": [21, 21, 21, 21, 168],
    "gpt-5.2-pro-2025-12-11": [21, 21, 21, 21, 168],
    "gpt-5.3-chat-latest": [1.75, 0.175, 1.75, 1.75, 14],
    "gpt-5.3-codex": [1.75, 0.175, 1.75, 1.75, 14],
    "gpt-5.4": [2.5, 0.25, 2.5, 2.5, 15, {"above": [272000, 5, 0.5, 5, 5, 22.5]}],
    "gpt-5.4-2026-03-05": [
        2.5,
        0.25,
        2.5,
        2.5,
        15,
        {"above": [272000, 5, 0.5, 5, 5, 22.5]},
    ],
    "gpt-5.4-mini": [0.75, 0.075, 0.75, 0.75, 4.5],
    "gpt-5.4-mini-2026-03-17": [0.75, 0.075, 0.75, 0.75, 4.5],
    "gpt-5.4-nano": [0.2, 0.02, 0.2, 0.2, 1.25],
    "gpt-5.4-nano-2026-03-17": [0.2, 0.02, 0.2, 0.2, 1.25],
    "gpt-5.4-pro": [30, 30, 30, 30, 180, {"above": [272000, 60, 60, 60, 60, 270]}],
    "gpt-5.4-pro-2026-03-05": [
        30,
        30,
        30,
        30,
        180,
        {"above": [272000, 60, 60, 60, 60, 270]},
    ],
    "gpt-5.5": [5, 0.5, 5, 5, 30, {"above": [272000, 10, 1, 10, 10, 45]}],
    "gpt-5.5-2026-04-23": [5, 0.5, 5, 5, 30, {"above": [272000, 10, 1, 10, 10, 45]}],
    "gpt-5.5-cyber": [12.5, 1.25, 12.5, 12.5, 75],
    "gpt-5.5-pro": [30, 30, 30, 30, 180, {"above": [272000, 60, 60, 60, 60, 270]}],
    "gpt-5.5-pro-2026-04-23": [
        30,
        30,
        30,
        30,
        180,
        {"above": [272000, 60, 60, 60, 60, 270]},
    ],
    "gpt-5.6": [4, 0.4, 5, 5, 20, {"above": [272000, 8, 0.8, 10, 10, 30]}],
    "gpt-5.6-cyber": [
        12.5,
        1.25,
        15.625,
        15.625,
        75,
        {"above": [272000, 25, 2.5, 31.25, 31.25, 112.5]},
    ],
    "gpt-5.6-luna": [
        0.2,
        0.02,
        0.25,
        0.25,
        1.2,
        {"above": [272000, 0.4, 0.04, 0.5, 0.5, 1.8]},
    ],
    "gpt-5.6-sol": [4, 0.4, 5, 5, 20, {"above": [272000, 8, 0.8, 10, 10, 30]}],
    "gpt-5.6-terra": [2, 0.2, 2.5, 2.5, 12, {"above": [272000, 4, 0.4, 5, 5, 18]}],
    "gpt-6-astra": [10, 1, 12.5, 12.5, 50, {"above": [272000, 20, 2, 25, 25, 75]}],
    "gpt-6-luna": [
        0.1,
        0.01,
        0.125,
        0.125,
        0.5,
        {"above": [272000, 0.2, 0.02, 0.25, 0.25, 0.75]},
    ],
    "gpt-6-sol": [2, 0.2, 2.5, 2.5, 10, {"above": [272000, 4, 0.4, 5, 5, 15]}],
    "gpt-6.1-sol": [2, 0.1, 2.5, 2.5, 10, {"above": [272000, 4, 0.2, 5, 5, 15]}],
    "o3": [2, 0.5, 2, 2, 8],
    "o3-2025-04-16": [2, 0.5, 2, 2, 8],
    "o3-deep-research": [10, 2.5, 10, 10, 40],
    "o3-mini": [1.1, 0.55, 1.1, 1.1, 4.4],
    "o3-mini-2025-01-31": [1.1, 0.55, 1.1, 1.1, 4.4],
    "o3-pro": [20, 20, 20, 20, 80],
    "o3-pro-2025-06-10": [20, 20, 20, 20, 80],
    "o4-mini": [1.1, 0.275, 1.1, 1.1, 4.4],
    "o4-mini-2025-04-16": [1.1, 0.275, 1.1, 1.1, 4.4],
    "o4-mini-deep-research": [2, 0.5, 2, 2, 8],
}
# --- prices end ---
CLASSES = ["input", "cache read", "cache write", "cache write (1 h)", "output"]
SEARCH = 0.01  # dollars per web search, Anthropic's and OpenAI's list price


def price_table(litellm):
    """LiteLLM's price file -> PRICES (also how --prices reads a newer copy)"""

    def per_m(x):
        x = round(x * 1e6, 6)
        return int(x) if x == int(x) else x

    def five(v, sfx):
        i = v.get("input_cost_per_token" + sfx)
        if i is None:
            return None
        read = v.get("cache_read_input_token_cost" + sfx)
        write = v.get("cache_creation_input_token_cost" + sfx)
        # cache_creation_input_token_cost_above_1hr, or ..._above_1hr_above_100k_tokens for the big tier
        hour = v.get("cache_creation_input_token_cost_above_1hr" + sfx)
        out = v.get("output_cost_per_token" + sfx)
        if out is None:
            return None
        read = (
            i if read is None else read
        )  # no cache discount listed: cached tokens cost as input
        write = (
            i if write is None else write
        )  # OpenAI charges no extra for writing the cache
        hour = write if hour is None else hour
        return [per_m(x) for x in (i, read, write, hour, out)]

    table = {}
    for name, v in litellm.items():
        if (
            not isinstance(v, dict)
            or "/" in name
            or v.get("litellm_provider") not in ("anthropic", "openai")
            or not re.match(r"(claude-|gpt-[56]|o[34]|codex-)", name)
        ):
            continue
        row = five(v, "")
        if not row:
            continue
        extra = {
            k: x
            for k, x in (v.get("provider_specific_entry") or {}).items()
            if k in ("fast", "us") and isinstance(x, (int, float))
        }
        for key in v:
            m = re.fullmatch(r"input_cost_per_token(_above_(\d+)k_tokens)", key)
            if m and five(v, m.group(1)):
                extra["above"] = [int(m.group(2)) * 1000] + five(v, m.group(1))
        table[name] = row + ([extra] if extra else [])
    return table


def rates_for(model):
    """-> a PRICES row for a model as a log names it (claude-opus-5-5[1m], anthropic/claude-…, …-20251001), else None"""
    name = re.sub(r"\[.*\]$", "", model or "").split("/")[-1].lower()
    for n in (
        name,
        re.sub(r"-\d{8}$", "", name),
        re.sub(r"-\d{4}-\d{2}-\d{2}$", "", name),
    ):
        if n in PRICES:
            return PRICES[n]
    return None


class Bill:
    """line items: tokens of each kind at each price, per model"""

    def __init__(self):
        self.lines = {}  # (model, kind, $ per million) -> tokens, or searches for "web search"
        self.unpriced = (
            collections.Counter()
        )  # model -> tokens, for models with no price
        self.given = {}  # model -> $, calls the log shows only as the tool's own figure
        self.fast = self.us = 0  # calls in fast mode / processed in the US only

    def add(self, model, n, fast=False, us=False, searches=0):
        """n: tokens of each kind, in CLASSES' order"""
        model = re.sub(r"\[.*\]$", "", model or "?")
        row = rates_for(model)
        if row is None:
            if sum(n):
                self.unpriced[model] += sum(n)
            return
        extra = row[5] if len(row) > 5 else {}
        rates, mult = row[:5], 1
        if extra.get("above") and sum(n[:4]) > extra["above"][0]:
            rates = extra["above"][1:]
        if fast:
            self.fast += 1
            mult *= extra.get("fast", 1)
        if us:
            self.us += 1
            mult *= extra.get("us", 1)
        for kind, k, rate in zip(CLASSES, n, rates):
            if k:
                key = (model, kind, round(rate * mult, 6))
                self.lines[key] = self.lines.get(key, 0) + k
        if searches:
            key = (model, "web search", SEARCH * 1e6)
            self.lines[key] = self.lines.get(key, 0) + searches

    def items(self):
        order = {m: i for i, m in enumerate(dict.fromkeys(m for m, _, _ in self.lines))}
        kinds = CLASSES + ["web search"]
        out = [
            {"model": m, "kind": k, "count": n, "rate": r, "usd": round(n * r / 1e6, 6)}
            for (m, k, r), n in sorted(
                self.lines.items(),
                key=lambda x: (order[x[0][0]], kinds.index(x[0][1]), x[0][2]),
            )
        ]
        out += [
            {"model": m, "kind": "own figure", "usd": round(u, 6)}
            for m, u in self.given.items()
        ]
        out += [
            {"model": m, "kind": "no price", "count": n}
            for m, n in self.unpriced.items()
        ]
        return out

    def total(self):
        return sum(i.get("usd", 0) for i in self.items())


def priced(r, bill, own=None):
    """put a bill's lines on a receipt, and say whether they add up to the tool's own total"""
    r["items"] = bill.items()
    r["prices"] = PRICES_FROM
    extras = {}
    if bill.fast:
        extras["fast_calls"] = bill.fast
    if bill.us:
        extras["us_only_calls"] = bill.us
    r["extras"] = {**r.get("extras", {}), **extras}
    if own is not None and any("usd" in i for i in r["items"]):
        r["cost_check"] = {
            "lines_usd": round(bill.total(), 6),
            "own_usd": round(own, 6),
        }


def lines(path):
    """one log entry at a time: a session log can be a gigabyte, so it is never read whole"""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def when(ts):
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()


def iso(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).isoformat()


def mins(ms):
    s = ms / 1000
    return (
        "<1 s"
        if 0 < s < 0.5
        else f"{s:.0f} s"
        if s < 90
        else f"{s / 60:.0f} min"
        if s < 5400
        else f"{s / 3600:.1f} h"
    )


def many(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def toks(n):
    for size, unit in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
        if n >= size:
            return f"{n / size:.1f}{unit}" if unit != "k" else f"{n / size:.0f}k"
    return str(n)


def span(vals):
    vals = [v for v in dict.fromkeys(vals) if v]
    return " → ".join(vals) if vals else "not recorded"


def pick(n, part):
    """part: None, ("last", N) or ("turns", A, B or None) -> (first, end) prompt indices (end exclusive) or
    None for the whole session, and the part's name"""
    if part is None:
        return None, "whole session"
    if part[0] == "last":
        k = part[1]
        if k > n:
            sys.exit(
                f"receipt: --last {k}, but this session has only {many(n, 'prompt')}"
            )
        return (n - k, n), ("last prompt" if k == 1 else f"last {k} prompts")
    a, b = part[1], part[2] or n
    if a > n or b > n or a > b:
        asked = str(a) if part[2] == a else f"{a}-{part[2] or ''}"
        sys.exit(f"receipt: --turns {asked}, but this session has {many(n, 'prompt')}")
    if (a, b) == (1, n):
        return None, "whole session"
    return (a - 1, b), (f"prompt {a}" if a == b else f"prompts {a}-{b}")


def bounds(marks, sel):
    """-> (from, to) for within(): the first picked prompt's mark and the mark of the prompt after the part"""
    if sel is None:
        return None
    first, end = sel
    return marks[first], (marks[end] if end < len(marks) else None)


def within(x, win):
    """is a time (or a line number) inside the part the receipt covers? win None is the whole session"""
    if win is None:
        return True
    if x is None or x == "":
        return False
    return x >= win[0] and (win[1] is None or x < win[1])


def home():
    return os.path.expanduser("~")


def tilde(p):
    h = home()
    return "~" + p[len(h) :] if p.startswith(h) else p


def heres():
    """the current folder as a tool may have logged it (macOS logs /private/var for /var, say)"""
    here = os.getcwd()
    return {here, os.path.realpath(here)}


def same_folder(cwd):
    return bool(cwd) and (
        cwd in heres()
        or os.path.realpath(cwd) in {os.path.realpath(h) for h in heres()}
    )


def base_name(p):
    return re.split(r"[\\/]", p.rstrip("\\/"))[-1]


def files_part(r, paths, deleted=0):
    names_ = [base_name(p) for p in paths]
    r["files_written"] = len(paths)
    r["files_deleted"] = deleted
    r["file_types"] = dict(
        collections.Counter(os.path.splitext(n)[1].lower() or "no type" for n in names_)
    )
    r["file_names"] = sorted(set(names_))


# ---------- where each tool keeps its logs ----------


def claude_dir():
    return os.path.expanduser(
        os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(home(), ".claude")
    )


def codex_dir():
    return os.path.expanduser(
        os.environ.get("CODEX_HOME") or os.path.join(home(), ".codex")
    )


def opencode_db():
    data = os.environ.get("XDG_DATA_HOME") or os.path.join(home(), ".local", "share")
    return os.path.join(os.path.expanduser(data), "opencode", "opencode.db")


def slug(path):
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def claude_cwd(path):
    for i, d in enumerate(lines(path)):
        if d.get("cwd"):
            return d["cwd"]
        if i > 50:
            break
    return ""


def codex_cwd(path):
    for i, d in enumerate(lines(path)):
        if d.get("type") == "session_meta":
            return (d.get("payload") or {}).get("cwd") or ""
        if i > 20:
            break
    return ""


_OC = None


def oc():
    """OpenCode's database, opened read-only"""
    global _OC
    if _OC is None:
        db = opencode_db()
        if not os.path.exists(db):
            sys.exit(f"receipt: no OpenCode database at {tilde(db)}")
        # file:///home/me/... or file:///C:/Users/me/...; mode=ro so a receipt can never change it
        path = os.path.abspath(db).replace("\\", "/").lstrip("/")
        _OC = sqlite3.connect(
            "file:///" + urllib.parse.quote(path, safe="/:") + "?mode=ro", uri=True
        )
    return _OC


def oc_rows():
    """-> [(session id, folder, last change in ms)], newest first; subagent sessions left out"""
    if not os.path.exists(opencode_db()):
        return []
    return (
        oc()
        .execute(
            "select id, directory, time_updated from session where parent_id is null order by time_updated desc"
        )
        .fetchall()
    )


def sessions(tool, everywhere=False):
    """-> session keys (a log path, or an OpenCode session id), newest first"""
    if tool == "opencode":
        return [i for i, d, _ in oc_rows() if everywhere or same_folder(d)]
    if tool == "codex":
        fs = glob.glob(
            os.path.join(codex_dir(), "sessions", "*", "*", "*", "rollout-*.jsonl")
        )
        fs.sort(key=os.path.getmtime, reverse=True)
        return fs if everywhere else [f for f in fs if same_folder(codex_cwd(f))]
    fs = glob.glob(os.path.join(claude_dir(), "projects", "*", "*.jsonl"))
    if not everywhere:
        slugs = {slug(h) for h in heres()}
        fs = [f for f in fs if os.path.basename(os.path.dirname(f)) in slugs]
    fs.sort(key=os.path.getmtime, reverse=True)
    return fs


def where(tool):
    return {
        "claude": tilde(os.path.join(claude_dir(), "projects", slug(os.getcwd()))),
        "codex": tilde(os.path.join(codex_dir(), "sessions")) + " (matched on folder)",
        "opencode": tilde(opencode_db()) + " (matched on folder)",
    }[tool]


def folder_of(tool, key):
    if tool == "opencode":
        return next((d for i, d, _ in oc_rows() if i == key), "")
    return codex_cwd(key) if tool == "codex" else claude_cwd(key)


def changed(tool, key):
    if tool == "opencode":
        ms = next((t for i, _, t in oc_rows() if i == key), 0)
        return datetime.datetime.fromtimestamp(ms / 1000)
    return datetime.datetime.fromtimestamp(os.path.getmtime(key))


def first_prompt_of(tool, key):
    if tool == "opencode":
        for text in oc_prompts(key):
            return text.strip().replace("\n", " ")
        return ""
    for d in lines(key):
        t = codex_prompt(d) if tool == "codex" else claude_prompt(d)
        if t is not None:
            return t.strip().replace("\n", " ")
    return ""


def elsewhere(tool):
    """-> why nothing was found here, and where to look instead"""
    hints = []
    if tool == "claude":
        fs = sessions("claude", True)
        others = {os.path.basename(os.path.dirname(f)) for f in fs} - {
            slug(h) for h in heres()
        }
        n = sum(1 for f in fs if os.path.basename(os.path.dirname(f)) in others)
    elif tool == "codex":
        cwds = [codex_cwd(f) for f in sessions("codex", True)]
        others = {c for c in cwds if not same_folder(c)}
        n = sum(1 for c in cwds if c in others)
    else:
        rows = oc_rows()
        others = {d for _, d, _ in rows if not same_folder(d)}
        n = sum(1 for _, d, _ in rows if d in others)
    if n:
        hints.append(
            f"{TOOLS[tool]} has {many(n, 'session')} from {many(len(others), 'other folder')}: "
            "run this from the folder you worked in, or see them all with --list --all"
        )
    for other in TOOLS:
        if other == tool:
            continue
        if other == "opencode" and not os.path.exists(opencode_db()):
            continue
        k = len(sessions(other))
        if k:
            how = (
                "leave out --codex and --opencode"
                if other == "claude"
                else f"add --{other}"
            )
            hints.append(f"this folder has {many(k, TOOLS[other] + ' session')}: {how}")
    return hints


# ---------- Claude Code ----------


def claude_text(d):
    """-> the text of a user entry you typed (or that stands for you), else None"""
    if d.get("type") != "user" or d.get("isSidechain") or d.get("isMeta"):
        return None
    if (d.get("origin") or {}).get("kind", "human") != "human":
        return None
    c = (d.get("message") or {}).get("content")
    if isinstance(c, str):
        return c
    if (
        isinstance(c, list)
        and c
        and all(isinstance(b, dict) and b.get("type") == "text" for b in c)
    ):
        return "\n".join(b.get("text", "") for b in c)
    return None


def claude_prompt(d):
    """-> your prompt text if this entry is one, else None"""
    text = claude_text(d)
    if (
        text
        and not text.startswith("<")
        and not text.startswith("This session is being continued")
        and not text.startswith(
            "[Request interrupted"
        )  # Claude Code's note that you pressed Esc
    ):
        return text
    return None


def claude_billing():
    files = [os.path.join(home(), ".claude.json")]
    if os.environ.get("CLAUDE_CONFIG_DIR"):
        files.insert(0, os.path.join(claude_dir(), ".claude.json"))
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        oa = (
            d.get("oauthAccount") or {}
        )  # read for the plan only; it also holds your email
        if oa:
            plan = PLANS.get(oa.get("organizationType")) or "subscription"
            extra = "; extra usage on" if oa.get("hasExtraUsageEnabled") else ""
            return (
                f"{plan}: a flat fee, not charged per run (your account today{extra})"
            )
        if d.get("primaryApiKey") or os.environ.get("ANTHROPIC_API_KEY"):
            return "API key: charged per token, so the cost above is close to what you paid"
        return "not found in Claude Code's settings"
    return "not found (no Claude Code settings file)"


def claude_bill(calls):
    """(model, usage) per call -> a Bill; the 1-hour cache writes are priced apart from the 5-minute ones"""
    bill = Bill()
    for model, u in calls:
        hour = (u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens") or 0
        bill.add(
            model,
            [
                u.get("input_tokens") or 0,
                u.get("cache_read_input_tokens") or 0,
                max((u.get("cache_creation_input_tokens") or 0) - hour, 0),
                hour,
                u.get("output_tokens") or 0,
            ],
            fast=u.get("speed") == "fast",
            us=u.get("inference_geo") == "us",
            searches=(u.get("server_tool_use") or {}).get("web_search_requests") or 0,
        )
    return bill


EDIT_TOOLS = {
    "Write": "file_path",
    "Edit": "file_path",
    "MultiEdit": "file_path",
    "NotebookEdit": "notebook_path",
}


def claude_window(path, part):
    marks = (
        [d.get("timestamp") or "" for d in lines(path) if claude_prompt(d) is not None]
        if part
        else []
    )
    sel, name = pick(len(marks), part)
    return bounds(marks, sel), name


def claude(path, part=None):
    win, name = claude_window(path, part)
    r = {"tool": "Claude Code", "part": name}
    versions, models, efforts, perms, stamps = [], [], [], [], []
    tools, skills, mcp, agents, hooks = (collections.Counter() for _ in range(5))
    memory, mcp_servers, skill_names = {}, set(), set()
    invoked_before, invoked_after = set(), set()
    skill_count, prompts, first_prompt, cost = None, 0, None, None
    usage_by_msg, server_web, context_hooks = {}, 0, 0
    edits, failed, errors, interrupted = {}, set(), 0, 0
    # every model call, main conversation and subagents, priced one by one; Claude Code writes a running total
    # per process, and a resumed session starts a new one, so the totals are kept per process and added up
    procs, calls, thinking, key = {}, {}, {}, None
    for i, d in enumerate(lines(path)):
        t, ts = d.get("type"), d.get("timestamp") or ""
        inside = within(ts, win)
        key = key or d.get("sessionId")
        # what was loaded: whole session, whatever part the receipt covers
        if t == "cost-state":
            procs[d.get("startTime")] = d
        elif t == "attachment":
            a = d.get("attachment") or {}
            at = a.get("type")
            if at == "nested_memory":
                memory[os.path.basename(a.get("path", ""))] = (
                    a.get("content") or {}
                ).get("type", "?")
            elif at == "instructions":
                for f in a.get("files", []):
                    memory[os.path.basename(f.get("path", ""))] = f.get("type", "?")
            elif at == "skill_listing":
                if a.get("skillCount") is not None:
                    skill_count = a["skillCount"]
                skill_names |= set(a.get("names") or [])
            elif at == "mcp_instructions_delta":
                mcp_servers |= {
                    re.sub(r"[^A-Za-z0-9]", "_", n) for n in a.get("addedNames", [])
                }
            elif at == "deferred_tools_delta":
                mcp_servers |= {
                    n.split("__")[1]
                    for n in a.get("addedNames", [])
                    if n.startswith("mcp__")
                }
            elif (
                at == "invoked_skills"
            ):  # skills you started yourself (/name) are listed here, cumulatively
                names = {s.get("name", "?") for s in a.get("skills", [])}
                (invoked_after if inside else invoked_before).update(names)
            elif at in ("hook_success", "hook_additional_context") and inside:
                if at == "hook_success":
                    hooks[a.get("hookEvent") or "?"] += 1
                else:
                    context_hooks += 1
        if not inside:
            continue
        # what happened: only inside the part the receipt covers
        if ts:
            stamps.append(ts)
        if d.get("version"):
            versions.append(d["version"])
        if d.get("effort"):
            efforts.append(str(d["effort"]))
        if d.get("permissionMode"):
            perms.append(d["permissionMode"])
        if t == "assistant":
            m = d.get("message") or {}
            if m.get("usage") and m.get("model") and not m["model"].startswith("<"):
                calls[m.get("id") or i] = (m["model"], m["usage"])
            if d.get("thinkingDurationMs"):
                thinking[m.get("id") or i] = d["thinkingDurationMs"]
        text = claude_prompt(d)
        if text is not None:
            prompts += 1
            first_prompt = first_prompt or text
        elif t == "user" and not d.get("isSidechain"):
            if (claude_text(d) or "").startswith("[Request interrupted"):
                interrupted += 1
            c = (d.get("message") or {}).get("content")
            for b in c if isinstance(c, list) else []:
                if (
                    isinstance(b, dict)
                    and b.get("type") == "tool_result"
                    and b.get("is_error")
                ):
                    errors += 1
                    failed.add(b.get("tool_use_id"))
        elif t == "assistant" and not d.get("isSidechain"):
            m = d.get("message") or {}
            if m.get("model") and not m["model"].startswith("<"):
                models.append(m["model"])
            if m.get("usage"):
                usage_by_msg[m.get("id") or i] = m[
                    "usage"
                ]  # one reply is logged as several entries
            for b in m.get("content") or []:
                if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                    continue
                n = b.get("name", "?")
                tools[n] += 1
                inp = b.get("input") or {}
                if n == "Skill":
                    skills[inp.get("skill", "?")] += 1
                elif n in ("Agent", "Task"):
                    agents[inp.get("subagent_type") or "general-purpose"] += 1
                elif n.startswith("mcp__"):
                    mcp[n.split("__")[1]] += 1
                    mcp_servers.add(n.split("__")[1])
                elif n in EDIT_TOOLS and inp.get(EDIT_TOOLS[n]):
                    edits[b.get("id")] = inp[EDIT_TOOLS[n]]
    if not stamps:
        sys.exit(
            f"receipt: {path} has no timestamped entries; is it a Claude Code session log?"
        )
    for u in usage_by_msg.values():
        stu = u.get("server_tool_use") or {}
        server_web += (stu.get("web_search_requests") or 0) + (
            stu.get("web_fetch_requests") or 0
        )
    for name in invoked_after - invoked_before:
        skills[name] = max(skills[name], 1)
    # the subagents/ folder also holds subagents' own subagents; its .meta.json files carry each one's
    # type but no time, so they count only for the whole session
    metas = glob.glob(
        os.path.join(os.path.splitext(path)[0], "subagents", "*.meta.json")
    )
    if win is None and len(metas) > sum(agents.values()):
        agents = collections.Counter()
        for f in metas:
            try:
                with open(f, encoding="utf-8") as fh:
                    agents[json.load(fh).get("agentType") or "general-purpose"] += 1
            except (OSError, ValueError):
                agents["general-purpose"] += 1
    r["version"] = span(versions[:1] + versions[-1:])
    r["models"] = list(dict.fromkeys(models))
    r["effort"] = span(efforts)
    r["permissions"] = span(perms)
    r["started"], r["ended"] = min(stamps), max(stamps)
    r["prompts"] = prompts
    r["session_key"] = key or os.path.splitext(os.path.basename(path))[0]
    # subagents' calls are in their own logs (older Claude Code put them in this one, marked sidechain)
    for f in glob.glob(os.path.join(os.path.splitext(path)[0], "subagents", "*.jsonl")):
        for j, d in enumerate(lines(f)):
            m, ts = d.get("message") or {}, d.get("timestamp") or ""
            if (
                d.get("type") == "assistant"
                and m.get("usage")
                and m.get("model")
                and not m["model"].startswith("<")
                and within(ts, win)
            ):
                calls[m.get("id") or f"{f}:{j}"] = (m["model"], m["usage"])
            if within(ts, win):  # files subagents wrote count too
                if d.get("type") == "assistant":
                    for b in m.get("content") or []:
                        if isinstance(b, dict) and b.get("type") == "tool_use":
                            claude_edit(b, edits)
                elif d.get("type") == "user":
                    claude_failed(d, failed)
    bill = claude_bill(calls.values())
    mu = {}  # Claude Code's own figures per model, added up over its processes
    for p in procs.values():
        for m, v in (p.get("modelUsage") or {}).items():
            mu.setdefault(re.sub(r"\[.*\]$", "", m), collections.Counter()).update(
                {k: x for k, x in v.items() if isinstance(x, (int, float))}
            )
    own = sum(p.get("totalCostUSD") or 0 for p in procs.values()) if procs else None
    main = {re.sub(r"\[.*\]$", "", m) for m in models}
    r["background_models"] = sorted(set(mu) - main)
    r["extras"] = {}
    if thinking:
        r["extras"]["thinking_ms"] = sum(thinking.values())
    if win is None and procs:
        called = {re.sub(r"\[.*\]$", "", m) for m, _ in calls.values()}
        for (
            m,
            v,
        ) in (
            mu.items()
        ):  # background calls (titles, summaries) log only Claude Code's figure
            if m not in called and v.get("costUSD"):
                bill.given[m] = v["costUSD"]
        retry = sum(
            (p.get("totalAPIDuration") or 0)
            - (
                p.get("totalAPIDurationWithoutRetries")
                or p.get("totalAPIDuration")
                or 0
            )
            for p in procs.values()
        )
        if retry > 0:
            r["extras"]["retry_ms"] = retry
        r["cost_usd"] = round(own, 6)
        r["cost_note"] = "Claude Code's own total at API prices"
        if len(procs) > 1:
            r["cost_note"] += f", added up over the {len(procs)} times it was opened"
        priced(r, bill, own)
        r["model_time_ms"] = sum(p.get("totalAPIDuration") or 0 for p in procs.values())
        r["lines_changed"] = [
            sum(p.get("totalLinesAdded") or 0 for p in procs.values()),
            sum(p.get("totalLinesRemoved") or 0 for p in procs.values()),
        ]
        r["tokens_in"] = sum(
            v["inputTokens"] + v["cacheReadInputTokens"] + v["cacheCreationInputTokens"]
            for v in mu.values()
        )
        r["tokens_cached"] = sum(v["cacheReadInputTokens"] for v in mu.values())
        r["tokens_out"] = sum(v["outputTokens"] for v in mu.values())
    elif calls:
        r["cost_usd"] = round(bill.total(), 6)
        r["cost_note"] = "worked out from the logged calls at API prices" + (
            f"; Claude Code's own total covers the whole session only: ${own:.2f}"
            if own is not None
            else "; this Claude Code version logs no total"
        )
        priced(r, bill)
    else:
        r["cost_note"] = "not in this log (older Claude Code versions don't write it)"
    if any(p.get("hasUnknownModelCost") for p in procs.values()):
        r["cost_note"] += "; some model costs unknown"
    if "cost_usd" in r and models and not any("claude" in m.lower() for m in models):
        r["cost_note"] += "; the model isn't Anthropic's, so the estimate doesn't apply"
    r["billing"] = claude_billing()
    if win is not None or "tokens_in" not in r:
        us = usage_by_msg.values()
        r["tokens_in"] = sum(
            u.get("input_tokens", 0)
            + u.get("cache_read_input_tokens", 0)
            + u.get("cache_creation_input_tokens", 0)
            for u in us
        )
        r["tokens_cached"] = sum(u.get("cache_read_input_tokens", 0) for u in us)
        r["tokens_out"] = sum(u.get("output_tokens", 0) for u in us)
        r["tokens_note"] = "main conversation only"
    r["tool_calls"] = sum(tools.values())
    r["shell_commands"] = tools.get("Bash", 0)
    r["web"] = tools.get("WebSearch", 0) + tools.get("WebFetch", 0) + server_web
    r["tool_errors"] = errors
    r["interrupted"] = interrupted
    files_part(r, sorted({p for i, p in edits.items() if i not in failed}))
    r["skills_used"] = dict(skills)
    r["skills_available"] = skill_count
    r["mcp_used"] = dict(mcp)
    r["mcp_connected"] = len(mcp_servers)
    plugins_avail = {n.split(":")[0] for n in skill_names if ":" in n} | {
        s.split("_")[1]
        for s in mcp_servers
        if s.startswith("plugin_") and s.count("_") >= 2
    }
    r["plugins_used"] = sorted(
        {n.split(":")[0] for n in skills if ":" in n}
        | {
            s.split("_")[1]
            for s in mcp
            if s.startswith("plugin_") and s.count("_") >= 2
        }
    )
    r["plugins_available"] = len(plugins_avail)
    r["subagents"] = dict(agents)
    r["hooks"] = dict(hooks)
    r["hooks_added_context"] = context_hooks
    r["memory"] = sorted(
        f"{name} ({kind.lower()})" for name, kind in memory.items() if name
    )
    r["first_prompt"] = first_prompt
    return r


# ---------- Codex ----------


def codex_prompt(d):
    """-> your prompt text if this entry is one, else None. A message holds several blocks (plugin list,
    AGENTS.md, environment, image tags, your text): judge each block, not the joined text."""
    p = d.get("payload") or {}
    if (
        d.get("type") != "response_item"
        or p.get("type") != "message"
        or p.get("role") != "user"
    ):
        return None
    blocks = [
        b.get("text", "")
        for b in p.get("content") or []
        if isinstance(b, dict) and b.get("type") == "input_text"
    ]
    mine = [
        b
        for b in blocks
        if b.strip() and not b.lstrip().startswith(("<", "# AGENTS.md"))
    ]
    return "\n".join(mine) if mine else None


def codex_billing(providers):
    if providers and all(p in LOCAL for p in providers):
        return "none: the model ran on this computer"
    other = [p for p in providers if p != "openai"]
    if other:
        return f"through {', '.join(other)}, not your ChatGPT plan"
    try:
        with open(os.path.join(codex_dir(), "auth.json"), encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, ValueError):
        return "not found (no Codex login file)"
    mode = d.get("auth_mode") or (
        "chatgpt" if d.get("tokens") else "apikey" if d.get("OPENAI_API_KEY") else ""
    )
    if mode == "chatgpt":
        plan = ""
        parts = ((d.get("tokens") or {}).get("id_token") or "").split(".")
        if len(parts) == 3:  # read for the plan only; the login also holds your email
            try:
                claims = json.loads(
                    base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4))
                )
                plan = (claims.get("https://api.openai.com/auth") or {}).get(
                    "chatgpt_plan_type"
                ) or ""
            except ValueError:
                plan = ""
        plan = f"ChatGPT {plan.capitalize()} plan" if plan else "ChatGPT plan"
        return f"{plan}: a flat fee, not charged per run (your account today)"
    if mode:
        return "API key: charged per token"
    return "not found in Codex's login file"


def codex_window(path, part):
    """-> line numbers bounding the picked prompts' turns, and the part's name"""
    if not part:
        return None, "whole session"
    prompt_at, starts = [], []
    for i, d in enumerate(lines(path)):
        if codex_prompt(d) is not None:
            prompt_at.append(i)
        elif (
            d.get("type") == "event_msg"
            and (d.get("payload") or {}).get("type") == "task_started"
        ):
            starts.append(i)
    # a turn's settings are logged just before its prompt: each part starts where its turn starts
    marks = [max([s for s in starts if s <= i], default=i) for i in prompt_at]
    sel, name = pick(len(marks), part)
    return bounds(marks, sel), name


def codex_call(bill, model, u):
    # input_tokens counts the cached and cache-written tokens too; output_tokens counts reasoning
    cached, wrote = (
        u.get("cached_input_tokens") or 0,
        u.get("cache_write_input_tokens") or 0,
    )
    bill.add(
        model,
        [
            max((u.get("input_tokens") or 0) - cached - wrote, 0),
            cached,
            wrote,
            0,
            u.get("output_tokens") or 0,
        ],
    )


SHELL_TOOLS = ("exec", "shell", "exec_command")


def codex(path, part=None):
    win, name = codex_window(path, part)
    r = {"tool": "Codex CLI", "part": name}
    versions, models, efforts, sandboxes, approvals, stamps = [], [], [], [], [], []
    providers = []
    calls, skills, mcp = (
        collections.Counter(),
        collections.Counter(),
        collections.Counter(),
    )
    prompts, first_prompt, agents_md, web, images, busy = 0, None, False, 0, 0, 0
    errors, interrupted, call_names = 0, 0, {}
    written, deleted, patched_by_event, patch_inputs = set(), set(), False, []
    # Codex's running total restarts with each process (every `codex exec resume`), so add up each
    # model call's own usage instead; the same event is often logged twice, so skip unchanged totals
    usage, last_total = collections.Counter(), None
    bill, model_now, key = (
        Bill(),
        None,
        None,
    )  # each call priced at the model its turn used
    for i, d in enumerate(lines(path)):
        t, p, ts = d.get("type"), d.get("payload") or {}, d.get("timestamp") or ""
        inside = within(i, win)
        if t == "session_meta":
            versions.append(p.get("cli_version"))
            providers.append(p.get("model_provider"))
            key = key or p.get("id")
        elif t == "turn_context":
            model_now = p.get("model") or model_now
        elif t == "event_msg" and p.get("type") == "token_count" and p.get("info"):
            total = p["info"].get("total_token_usage")
            if inside and total != last_total:
                u = p["info"].get("last_token_usage") or {}
                usage.update(u)
                codex_call(bill, model_now, u)
            last_total = total
        if (
            t == "response_item"
            and p.get("type") == "message"
            and p.get("role") == "user"
        ):
            for b in p.get("content") or []:
                if isinstance(b, dict) and (b.get("text") or "").startswith(
                    "# AGENTS.md instructions"
                ):
                    agents_md = True
        if not inside:
            continue
        if ts:
            stamps.append(ts)
        if t == "turn_context":
            models.append(p.get("model"))
            efforts.append(p.get("effort") or "not set")
            sp = p.get("sandbox_policy") or {}
            net = "network on" if sp.get("network_access") else "network off"
            sandboxes.append(
                f"{sp.get('type', '?')}, {net}"
                if sp.get("type") != "danger-full-access"
                else "no sandbox"
            )
            approvals.append(p.get("approval_policy"))
        elif t == "event_msg":
            et = p.get("type")
            if et == "task_complete":
                busy += p.get("duration_ms") or 0
            elif et == "turn_aborted" and p.get("reason") == "interrupted":
                interrupted += 1
            elif et == "exec_command_end" and p.get("exit_code") not in (0, None):
                errors += 1
            elif et == "patch_apply_end":
                patched_by_event = True
                if not p.get("success"):
                    errors += 1
                elif isinstance(p.get("changes"), dict):
                    for f, ch in p["changes"].items():
                        kind = (ch or {}).get("type") if isinstance(ch, dict) else None
                        (deleted if kind == "delete" else written).add(f)
        elif t == "response_item":
            pt = p.get("type")
            text = codex_prompt(d)
            if text is not None:
                prompts += 1
                first_prompt = first_prompt or text
            if pt == "message" and p.get("role") == "user":
                for b in p.get("content") or []:
                    for s in re.findall(
                        r"<skill>\s*<name>([^<]+)</name>", (b or {}).get("text") or ""
                    ):
                        skills[s] += 1
            elif pt in ("function_call", "custom_tool_call"):
                n = p.get("name", "?")
                calls[n] += 1
                call_names[p.get("call_id")] = n
                if "mcp" in n or "__" in n:
                    mcp[n] += 1
                arg = json.dumps(p.get("input") or p.get("arguments") or "")
                for s in re.findall(r"skills/(?:\.system/)?([\w.-]+)/SKILL\.md", arg):
                    skills[s] += 1
                if n == "apply_patch":
                    patch_inputs.append(p.get("input") or p.get("arguments") or "")
            elif pt in ("function_call_output", "custom_tool_call_output"):
                # the `exec` tool runs a script and reports "Script failed" instead of an exit code
                if call_names.get(p.get("call_id")) == "exec":
                    o = p.get("output")
                    first = (
                        o
                        if isinstance(o, str)
                        else (o[0] or {}).get("text", "")
                        if isinstance(o, list) and o and isinstance(o[0], dict)
                        else ""
                    )
                    if first.startswith("Script failed"):
                        errors += 1
            elif pt == "web_search_call":
                web += 1
            elif pt == "image_generation_call":
                images += 1
    if not stamps:
        sys.exit(
            f"receipt: {path} has no timestamped entries; is it a Codex session log?"
        )
    if not patched_by_event:  # older Codex logs the patch text but no result event
        for s in patch_inputs:
            s = s if isinstance(s, str) else json.dumps(s)
            written |= set(re.findall(r"\*\*\* (?:Add|Update) File: ([^\n\\]+)", s))
            deleted |= set(re.findall(r"\*\*\* Delete File: ([^\n\\]+)", s))
    providers = list(dict.fromkeys(p for p in providers if p))
    r["version"] = span(versions)
    r["models"] = list(dict.fromkeys(m for m in models if m))
    r["providers"] = providers
    r["effort"] = span(efforts)
    r["permissions"] = f"sandbox {span(sandboxes)} · approvals {span(approvals)}"
    r["started"], r["ended"] = min(stamps), max(stamps)
    r["prompts"] = prompts
    r["model_time_ms"] = busy or None
    r["session_key"] = key or os.path.basename(path)
    if providers and all(p in LOCAL for p in providers):
        r["cost_note"] = "none: the model ran on this computer"
    elif bill.lines:
        r["cost_usd"] = round(bill.total(), 6)
        r["cost_note"] = (
            "worked out from the logged calls at API prices; Codex logs no price"
        )
        priced(r, bill)
    else:
        r["cost_note"] = "Codex logs no price" + (
            f", and the price table has none for {', '.join(bill.unpriced)}"
            if bill.unpriced
            else ""
        )
    r["billing"] = codex_billing(providers)
    if last_total is not None:
        r["tokens_in"] = usage["input_tokens"]
        r["tokens_cached"] = usage["cached_input_tokens"]
        r["tokens_out"] = usage["output_tokens"]
    r["tool_calls"] = sum(calls.values())
    r["shell_commands"] = sum(calls.get(n, 0) for n in SHELL_TOOLS)
    r["web"] = web
    r["images_made"] = images
    r["tool_errors"] = errors
    r["interrupted"] = interrupted
    files_part(r, sorted(written - deleted), len(deleted))
    r["skills_used"] = dict(skills)
    r["mcp_used"] = dict(mcp)
    r["hooks"] = None  # Codex session logs don't record hook runs
    r["memory"] = ["AGENTS.md"] if agents_md else []
    r["first_prompt"] = first_prompt
    return r


# ---------- OpenCode ----------

OC_BUILTIN = {
    "bash", "read", "write", "edit", "multiedit", "patch", "glob", "grep", "list", "ls",
    "todowrite", "todoread", "task", "webfetch", "websearch", "codesearch", "skill",
    "question", "batch", "invalid", "lsp",
}  # fmt: skip


def oc_prompts(sid, with_time=False):
    """-> your prompts in one OpenCode session, oldest first (text OpenCode adds itself is marked synthetic)"""
    out = []
    for mid, created, data in oc().execute(
        "select id, time_created, data from message where session_id = ? order by time_created",
        (sid,),
    ):
        if json.loads(data).get("role") != "user":
            continue
        texts = [
            p.get("text", "")
            for (pd,) in oc().execute(
                "select data from part where message_id = ? order by time_created",
                (mid,),
            )
            for p in [json.loads(pd)]
            if p.get("type") == "text" and not p.get("synthetic")
        ]
        text = "\n".join(t for t in texts if t.strip())
        if text:
            out.append((created, text) if with_time else text)
    return out


def opencode(sid, part=None):
    row = (
        oc()
        .execute("select version, agent, permission from session where id = ?", (sid,))
        .fetchone()
    )
    if not row:
        sys.exit(f"receipt: no OpenCode session {sid!r} (see --opencode --list)")
    version, agent, permission = row
    prompts_t = oc_prompts(sid, with_time=True)
    sel, name = pick(len(prompts_t), part)
    win = bounds([t for t, _ in prompts_t], sel)
    r = {"tool": "OpenCode", "part": name, "version": version or "not recorded"}
    models, providers, efforts, stamps = [], [], [], []
    tools, skills, mcp, agents = (collections.Counter() for _ in range(4))
    cost, tin, tcached, tout, busy = 0.0, 0, 0, 0, 0
    bill = Bill()
    errors, model_errors, interrupted, written = 0, 0, 0, set()
    # subagents run in child sessions: their cost and tokens count, as in Claude Code's totals
    children = []
    for c, kind in oc().execute(
        "select id, agent from session where parent_id = ?", (sid,)
    ):
        children.append(c)
        agents[kind or "general"] += 1
    for s in [sid] + children:
        for created, data in oc().execute(
            "select time_created, data from message where session_id = ? order by time_created",
            (s,),
        ):
            if not within(created, win):
                continue
            m = json.loads(data)
            tm = m.get("time") or {}
            for k in ("created", "completed"):
                if tm.get(k):
                    stamps.append(tm[k])
            if m.get("variant"):
                efforts.append(str(m["variant"]))
            if m.get("role") != "assistant":
                continue
            cost += m.get("cost") or 0
            tk = m.get("tokens") or {}
            cache = tk.get("cache") or {}
            if (m.get("providerID") or "?") not in LOCAL:
                bill.add(
                    m.get("modelID"),
                    [
                        tk.get("input") or 0,
                        cache.get("read") or 0,
                        cache.get("write") or 0,
                        0,
                        (tk.get("output") or 0) + (tk.get("reasoning") or 0),
                    ],
                )
            tin += (
                (tk.get("input") or 0)
                + (cache.get("read") or 0)
                + (cache.get("write") or 0)
            )
            tcached += cache.get("read") or 0
            tout += (tk.get("output") or 0) + (tk.get("reasoning") or 0)
            if s != sid:
                continue
            if m.get(
                "modelID"
            ):  # one session can switch providers, so each model names its own
                pid = m.get("providerID") or "?"
                where_ = ", on this computer" if pid in LOCAL else ""
                models.append(f"{m['modelID']} ({pid}{where_})")
                providers.append(pid)
            if tm.get("created") and tm.get("completed"):
                busy += tm["completed"] - tm["created"]
            err = (m.get("error") or {}).get("name")
            if err == "MessageAbortedError":
                interrupted += 1
            elif err:
                model_errors += 1
    for mcreated, pdata in oc().execute(
        "select m.time_created, p.data from part p join message m on m.id = p.message_id where p.session_id = ?",
        (sid,),
    ):
        if not within(mcreated, win):
            continue
        p = json.loads(pdata)
        if p.get("type") == "patch":
            written |= set(p.get("files") or [])
        if p.get("type") != "tool":
            continue
        n, st = p.get("tool", "?"), p.get("state") or {}
        tools[n] += 1
        inp = st.get("input") or {}
        if st.get("status") == "error":
            errors += 1
        elif n in ("write", "edit", "multiedit") and inp.get("filePath"):
            written.add(inp["filePath"])
        if n == "skill":
            skills[inp.get("name") or "?"] += 1
        elif n not in OC_BUILTIN and "_" in n:  # MCP tools are named server_tool
            mcp[n.split("_")[0]] += 1
    if not stamps:
        sys.exit(f"receipt: OpenCode session {sid} has no messages")
    prompts_in = [t for t, _ in prompts_t if within(t, win)]
    providers = list(dict.fromkeys(p for p in providers if p))
    r["models"] = list(dict.fromkeys(models))
    r["providers"] = providers
    r["effort"] = span(efforts) if efforts else "not set"
    r["permissions"] = f"agent {agent or '?'}" + (
        " · own permission rules" if permission else ""
    )
    r["started"], r["ended"] = iso(min(stamps)), iso(max(stamps))
    r["prompts"] = len(prompts_in)
    r["model_time_ms"] = busy or None
    r["session_key"] = sid
    sub = "; includes subagents" if children else ""
    if (
        not cost and bill.lines
    ):  # OpenCode can record a cost of 0 for providers it has no price for
        r["cost_usd"] = round(bill.total(), 6)
        r["cost_note"] = (
            "worked out from the logged calls at API prices; OpenCode recorded $0" + sub
        )
        priced(r, bill)
    else:
        r["cost_usd"] = round(cost, 6)
        r["cost_note"] = "as OpenCode recorded it" + sub
        if bill.lines:
            priced(r, bill, cost)
    r["billing"] = (
        "none: the model ran on this computer"
        if providers and all(p in LOCAL for p in providers)
        else f"through {', '.join(providers) or 'an unrecorded provider'}"
    )
    r["tokens_in"], r["tokens_cached"], r["tokens_out"] = tin, tcached, tout
    r["tool_calls"] = sum(tools.values())
    r["shell_commands"] = tools.get("bash", 0)
    r["web"] = tools.get("websearch", 0) + tools.get("webfetch", 0)
    r["tool_errors"] = errors
    r["interrupted"] = interrupted
    r["model_errors"] = model_errors
    files_part(r, sorted(written))
    r["skills_used"] = dict(skills)
    r["mcp_used"] = dict(mcp)
    r["subagents"] = dict(agents)
    r["hooks"] = None
    r["memory"] = None
    r["first_prompt"] = next((t for c, t in prompts_t if within(c, win)), None)
    return r


# ---------- one line per prompt ----------


def new_turn(at, prompt):
    return {"at": at, "end": at, "prompt": prompt, "ms": 0, "bill": Bill(), "calls": {}, "tools": 0,
            "shell": 0, "edits": {}, "files": set(), "texts": {}, "reply_of": None, "reply": None, "own": 0,
            "model": None, "effort": None}  # fmt: skip


def turn_at(rows, marks, x):
    """-> the turn that was running at time x (subagents' and child sessions' entries), or None"""
    i = bisect.bisect_right(marks, x) - 1
    return rows[i] if i >= 0 else None


def done_turns(rows, failed=(), priced=True):
    """-> the public form of each turn: no Bill, no ids"""
    out = []
    for n, t in enumerate(rows, 1):
        if t["calls"]:
            t["bill"] = claude_bill(t["calls"].values())
        if t["reply"] is None and t["reply_of"] is not None:
            t["reply"] = "\n\n".join(t["texts"].get(t["reply_of"], []))
        files = t["files"] | {p for i, p in t["edits"].items() if i not in failed}
        ms = t["ms"] or max(
            round((when(t["end"]) - when(t["at"])).total_seconds() * 1000), 0
        )
        row = {"n": n, "started": t["at"], "time_ms": ms, "tool_calls": t["tools"],
               "shell_commands": t["shell"], "files": len(files),
               "prompt": t["prompt"], "reply": t["reply"] or None, "model": t["model"],
               "effort": t["effort"]}  # fmt: skip
        if priced:
            row["cost_usd"] = round(t["own"] or t["bill"].total(), 6)
        out.append(row)
    return out


def claude_turns(path):
    """-> one row per prompt: when, how long, its calls priced (subagents' too), tool calls, files, last reply"""
    rows, failed = [], set()
    for i, d in enumerate(lines(path)):
        t, ts = d.get("type"), d.get("timestamp") or ""
        text = claude_prompt(d)
        if text is not None:
            rows.append(new_turn(ts, text))
            rows[-1]["effort"] = d.get("effort")
            continue
        if not rows:
            continue
        cur = rows[-1]
        cur["end"] = max(cur["end"], ts)
        if t == "system" and d.get("subtype") == "turn_duration":
            cur["ms"] += d.get("durationMs") or 0
        elif t == "assistant":
            m = d.get("message") or {}
            mid = m.get("id") or i
            if m.get("usage") and m.get("model") and not m["model"].startswith("<"):
                cur["calls"][mid] = (m["model"], m["usage"])
                if not d.get("isSidechain"):
                    cur["model"] = cur["model"] or m["model"]
            if d.get("isSidechain"):
                continue
            for b in m.get("content") or []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text" and b.get("text", "").strip():
                    cur["texts"].setdefault(mid, []).append(b["text"])
                    cur["reply_of"] = mid  # the last message with text is the reply
                elif b.get("type") == "tool_use":
                    cur["tools"] += 1
                    cur["shell"] += b.get("name") == "Bash"
                    claude_edit(b, cur["edits"])
        elif t == "user":
            claude_failed(d, failed)
    marks = [r["at"] for r in rows]
    for f in glob.glob(os.path.join(os.path.splitext(path)[0], "subagents", "*.jsonl")):
        for j, d in enumerate(lines(f)):
            cur = turn_at(rows, marks, d.get("timestamp") or "")
            if cur is None:
                continue
            m = d.get("message") or {}
            if d.get("type") == "assistant":
                if m.get("usage") and m.get("model") and not m["model"].startswith("<"):
                    cur["calls"][m.get("id") or f"{f}:{j}"] = (m["model"], m["usage"])
                for b in m.get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        claude_edit(b, cur["edits"])
            elif d.get("type") == "user":
                claude_failed(d, failed)
    return done_turns(rows, failed)


def claude_edit(b, edits):
    inp, n = b.get("input") or {}, b.get("name")
    if n in EDIT_TOOLS and inp.get(EDIT_TOOLS[n]):
        edits[b.get("id")] = inp[EDIT_TOOLS[n]]


def claude_failed(d, failed):
    c = (d.get("message") or {}).get("content")
    for b in c if isinstance(c, list) else []:
        if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
            failed.add(b.get("tool_use_id"))


def codex_turns(path):
    rows, last_total, model_now, effort_now, local = [], None, None, None, False
    for d in lines(path):
        t, p, ts = d.get("type"), d.get("payload") or {}, d.get("timestamp") or ""
        if t == "session_meta":
            local = local or p.get("model_provider") in LOCAL
        elif t == "turn_context":
            model_now = p.get("model") or model_now
            effort_now = p.get("effort") or effort_now
        elif t == "event_msg" and p.get("type") == "token_count" and p.get("info"):
            total = p["info"].get("total_token_usage")
            if rows and total != last_total:
                codex_call(
                    rows[-1]["bill"], model_now, p["info"].get("last_token_usage") or {}
                )
            last_total = total
        text = codex_prompt(d)
        if text is not None:
            rows.append(new_turn(ts, text))
            rows[-1]["model"], rows[-1]["effort"] = model_now, effort_now
            continue
        if not rows:
            continue
        cur = rows[-1]
        cur["end"] = max(cur["end"], ts)
        if t == "event_msg" and p.get("type") == "task_complete":
            cur["ms"] += p.get("duration_ms") or 0
            if p.get("last_agent_message"):
                cur["reply"] = p["last_agent_message"]
        elif (
            t == "event_msg" and p.get("type") == "patch_apply_end" and p.get("success")
        ):
            for f, ch in (p.get("changes") or {}).items():
                if not (isinstance(ch, dict) and ch.get("type") == "delete"):
                    cur["files"].add(f)
        elif (
            t == "response_item"
            and p.get("type") == "message"
            and p.get("role") == "assistant"
        ):
            said = "".join(
                b.get("text", "") for b in p.get("content") or [] if isinstance(b, dict)
            )
            if said.strip():
                cur["texts"]["last"], cur["reply_of"] = [said], "last"
        elif t == "response_item" and p.get("type") in (
            "function_call",
            "custom_tool_call",
        ):
            cur["tools"] += 1
            cur["shell"] += p.get("name") in SHELL_TOOLS
    return done_turns(rows, priced=not local)


def opencode_turns(sid):
    prompts_t = oc_prompts(sid, with_time=True)
    rows = [new_turn(iso(c), t) for c, t in prompts_t]
    marks = [c for c, _ in prompts_t]
    local, own_total = True, 0
    children = [
        c for (c,) in oc().execute("select id from session where parent_id = ?", (sid,))
    ]
    for s in [sid] + children:
        for created, data in oc().execute(
            "select time_created, data from message where session_id = ? order by time_created",
            (s,),
        ):
            cur = turn_at(rows, marks, created)
            m = json.loads(data)
            if cur is not None and s == sid and m.get("variant"):
                cur["effort"] = cur["effort"] or str(m["variant"])
            if cur is None or m.get("role") != "assistant":
                continue
            if s == sid and m.get("modelID") and not cur["model"]:
                cur["model"] = f"{m['modelID']} ({m.get('providerID') or '?'})"
            tm, tk = m.get("time") or {}, m.get("tokens") or {}
            if tm.get("completed"):
                cur["end"] = max(cur["end"], iso(tm["completed"]))
            if (m.get("providerID") or "?") not in LOCAL:
                local = False
                cache = tk.get("cache") or {}
                cur["bill"].add(m.get("modelID"), [tk.get("input") or 0, cache.get("read") or 0,
                    cache.get("write") or 0, 0, (tk.get("output") or 0) + (tk.get("reasoning") or 0)])  # fmt: skip
            cur["own"] += m.get("cost") or 0
            own_total += m.get("cost") or 0
            if s == sid and tm.get("created") and tm.get("completed"):
                cur["ms"] += tm["completed"] - tm["created"]
    for mid, created, mdata, pdata in oc().execute(
        "select m.id, m.time_created, m.data, p.data from part p join message m on m.id = p.message_id "
        "where p.session_id = ? order by p.time_created",
        (sid,),
    ):
        cur = turn_at(rows, marks, created)
        p = json.loads(pdata)
        if cur is None:
            continue
        if (
            p.get("type") == "text"
            and p.get("text", "").strip()
            and json.loads(mdata).get("role") == "assistant"
        ):
            cur["texts"].setdefault(mid, []).append(p["text"])
            cur["reply_of"] = mid
        elif p.get("type") == "tool":
            st, n = p.get("state") or {}, p.get("tool")
            inp = st.get("input") or {}
            cur["tools"] += 1
            cur["shell"] += n == "bash"
            if (
                st.get("status") != "error"
                and n in ("write", "edit", "multiedit")
                and inp.get("filePath")
            ):
                cur["files"].add(inp["filePath"])
        elif p.get("type") == "patch":
            cur["files"] |= set(p.get("files") or [])
    if not own_total:  # OpenCode records $0 for providers it has no price for: priced from the tokens instead
        for t in rows:
            t["own"] = 0
    return done_turns(rows, priced=not local)


# ---------- a record of what went in and came out ----------

# an in-toto Statement (in-toto.io/Statement/v1): the files the run wrote are its subjects, and the predicate
# holds fingerprints of everything that went in. No text is kept, only sha256 hashes, and it is saved in one
# byte form (sorted keys, no spaces, no floats), so its own sha256 is the same wherever it is worked out.
RECORD_TYPE = "https://musharna.github.io/prompt-receipts/record/v1"
SIGN_NS = "prompt-receipts"  # ssh-keygen -Y sign's namespace, so a signature made for this can't pass as another


def sha(x):
    if isinstance(x, str):
        x = x.encode("utf-8", "surrogatepass")
    return hashlib.sha256(x).hexdigest()


def canon(obj):
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8", "surrogatepass")


def no_floats(obj, where="record"):
    """a float prints differently in different languages, which would change the record's hash"""
    if isinstance(obj, float):
        raise ValueError(
            f"receipt: a float in the {where} ({obj!r}); this is a bug, please report it at {ISSUES}"
        )
    for v in (
        obj.values() if isinstance(obj, dict) else obj if isinstance(obj, list) else []
    ):
        no_floats(v, where)


def content_text(c):
    """a tool result as the model saw it, as one string (a picture stands in as its data's hash)"""
    if isinstance(c, str):
        return c
    out = []
    for b in c if isinstance(c, list) else []:
        if isinstance(b, dict) and b.get("type") in (
            "text",
            "input_text",
            "output_text",
        ):
            out.append(b.get("text") or "")
        elif isinstance(b, dict) and b.get("type") in ("image", "input_image"):
            out.append("[image " + sha(json.dumps(b, sort_keys=True)) + "]")
        else:
            out.append(json.dumps(b, sort_keys=True))
    return "\n".join(out)


def file_label(path, names):
    base = base_name(path or "")
    return base if names else (os.path.splitext(base)[1].lower() or "no type")


def output_subject(path, written, ended, names, n):
    """-> an in-toto subject for a file the run wrote: the content the log holds, else the file as it is now"""
    ext = os.path.splitext(base_name(path))[1].lower()
    name = base_name(path) if names else f"file{n}{ext}"
    disk, body, later = None, None, False
    try:
        with open(path, "rb") as fh:
            body = fh.read()
        disk = sha(body)
        later = os.path.getmtime(path) > when(ended).timestamp() + 2
    except OSError:
        pass
    if written is not None:
        digest, how = sha(written), "as written"
        if disk is None:
            how += "; not on disk now"
        elif disk != digest:
            how += "; changed on disk since"
        same = disk == digest
        body = written.encode("utf-8", "surrogatepass")
    elif disk is not None:
        digest, how, same = (
            disk,
            "on disk now" + ("; changed after the run" if later else ""),
            True,
        )
    else:
        return None, None
    subject = {
        "name": name,
        "digest": {"sha256": digest},
        "annotations": {"source": how},
    }
    return subject, {"name": name, "body": body, "path": path, "same_on_disk": same}


def record_claude(path, part, names, counts):
    win, _ = claude_window(path, part)
    prompts, system, instructions, defs, seen, env = [], {}, {}, {}, [], {}
    uses, edits, failed = {}, {}, set()
    for d in lines(path):
        t, ts = d.get("type"), d.get("timestamp") or ""
        inside = within(ts, win)
        if (
            t == "attachment"
        ):  # what was loaded counts for whatever part the record covers
            a = d.get("attachment") or {}
            at = a.get("type")
            if at == "prompt_snapshot" and a.get("systemPrompt"):
                sp = a["systemPrompt"]
                system.setdefault(
                    sha("\n\n".join(map(str, sp)) if isinstance(sp, list) else str(sp)),
                    1,
                )
            elif at == "instructions":
                for f in a.get("files") or []:
                    instructions.setdefault(
                        (base_name(f.get("path") or ""), sha(f.get("content") or "")),
                        f.get("type") or "?",
                    )
            elif at == "nested_memory":
                c = a.get("content") or {}
                if isinstance(c, dict) and isinstance(c.get("content"), str):
                    instructions.setdefault(
                        (base_name(a.get("path") or ""), sha(c["content"])),
                        c.get("type") or "?",
                    )
            elif at == "deferred_tools_record":
                for e in a.get("entries") or []:
                    defs[e.get("name") or "?"] = sha(canon(e))
            elif at == "environment":
                env = a.get("snapshot") or {}
        if not inside:
            continue
        text = claude_prompt(d)
        if text is not None:
            prompts.append(sha(text))
        elif t == "assistant":
            for b in (d.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    name, inp = b.get("name") or "?", b.get("input") or {}
                    uses[b.get("id")] = (name, inp)
                    if name in EDIT_TOOLS and inp.get(EDIT_TOOLS[name]):
                        # counted as the receipt's files line counts them: every call that didn't fail
                        edits[b.get("id")] = (
                            inp[EDIT_TOOLS[name]],
                            inp.get("content") if name == "Write" else None,
                        )
        elif t == "user":
            c = (d.get("message") or {}).get("content")
            tur = d.get("toolUseResult")
            for b in c if isinstance(c, list) else []:
                if not (isinstance(b, dict) and b.get("type") == "tool_result"):
                    continue
                name, inp = uses.get(b.get("tool_use_id"), ("?", {}))
                e = {"tool": name, "sha256": sha(content_text(b.get("content")))}
                if b.get("is_error"):
                    e["failed"] = True
                    failed.add(b.get("tool_use_id"))
                f = tur.get("file") if isinstance(tur, dict) else None
                if (
                    name == "Read"
                    and isinstance(f, dict)
                    and isinstance(f.get("content"), str)
                ):
                    e["file"] = file_label(
                        f.get("filePath") or inp.get("file_path"), names
                    )
                    e["file_sha256"] = sha(
                        f["content"]
                    )  # the file's own text, without the line numbers
                    if f.get("totalLines") is not None:
                        first = f.get("startLine") or 1
                        e["lines"] = (
                            f"{first}-{first + (f.get('numLines') or 0) - 1} of {f['totalLines']}"
                        )
                seen.append(e)
    for f in glob.glob(os.path.join(os.path.splitext(path)[0], "subagents", "*.jsonl")):
        for d in lines(f):  # files subagents wrote are outputs too
            if not within(d.get("timestamp") or "", win):
                continue
            if d.get("type") == "assistant":
                for b in (d.get("message") or {}).get("content") or []:
                    inp, n = (b or {}).get("input") or {}, (b or {}).get("name")
                    if (
                        (b or {}).get("type") == "tool_use"
                        and n in EDIT_TOOLS
                        and inp.get(EDIT_TOOLS[n])
                    ):
                        edits[b.get("id")] = (
                            inp[EDIT_TOOLS[n]],
                            inp.get("content") if n == "Write" else None,
                        )
            elif d.get("type") == "user":
                claude_failed(d, failed)
    writes = {}
    for i, (p, content) in edits.items():
        if i not in failed:
            writes[p] = (
                content  # a later Write's text replaces an earlier one; an Edit leaves none
            )
    rec = {
        "prompts": [{"sha256": h} for h in prompts],
        "system_prompt": [{"sha256": h} for h in system],
        "instructions": [
            {"name": n, "sha256": h} if not counts else {"kind": k, "sha256": h}
            for (n, h), k in instructions.items()
        ],
        "tool_definitions": [{"name": n, "sha256": h} for n, h in defs.items()],
        "tool_results": seen,
        "environment": {
            k: env[k] for k in ("platform", "shell", "osVersion") if env.get(k)
        },
    }
    limits = [
        "Claude Code logs the definitions of deferred tools only, not of its built-in ones",
        "what subagents read isn't included, only the files they wrote",
    ]
    return rec, writes, limits


def record_codex(path, part, names, counts):
    win, _ = codex_window(path, part)
    prompts, system, instructions, seen, uses, writes, git = [], {}, {}, [], {}, {}, {}
    for i, d in enumerate(lines(path)):
        t, p = d.get("type"), d.get("payload") or {}
        if t == "session_meta":
            base = p.get("base_instructions")
            base = base.get("text") if isinstance(base, dict) else base
            if isinstance(base, str):
                system.setdefault(sha(base), 1)
            git = {
                k: v
                for k, v in (p.get("git") or {}).items()
                if k == "commit_hash" and v
            }
        elif t == "turn_context" and isinstance(p.get("developer_instructions"), str):
            system.setdefault(sha(p["developer_instructions"]), 1)
        if (
            t == "response_item"
            and p.get("type") == "message"
            and p.get("role") == "user"
        ):
            for b in p.get("content") or []:
                text = (b or {}).get("text") or ""
                if text.startswith("# AGENTS.md instructions"):
                    instructions.setdefault(("AGENTS.md", sha(text)), "AGENTS.md")
        if not within(i, win):
            continue
        text = codex_prompt(d)
        if text is not None:
            prompts.append(sha(text))
        elif t == "response_item" and p.get("type") in (
            "function_call",
            "custom_tool_call",
        ):
            uses[p.get("call_id")] = p.get("name") or "?"
        elif t == "response_item" and p.get("type") in (
            "function_call_output",
            "custom_tool_call_output",
        ):
            seen.append(
                {
                    "tool": uses.get(p.get("call_id"), "?"),
                    "sha256": sha(content_text(p.get("output"))),
                }
            )
        elif (
            t == "event_msg" and p.get("type") == "patch_apply_end" and p.get("success")
        ):
            for f, ch in (p.get("changes") or {}).items():
                if isinstance(ch, dict) and ch.get("type") != "delete":
                    writes[f] = (
                        ch.get("content")
                        if ch.get("type") == "add"
                        and isinstance(ch.get("content"), str)
                        else None
                    )
    rec = {
        "prompts": [{"sha256": h} for h in prompts],
        "system_prompt": [{"sha256": h} for h in system],
        "instructions": [
            {"name": n, "sha256": h} if not counts else {"kind": k, "sha256": h}
            for (n, h), k in instructions.items()
        ],
        "tool_results": seen,
    }
    if git:
        rec["git_commit"] = git["commit_hash"]
    limits = ["Codex logs no tool definitions"]
    return rec, writes, limits


def record_opencode(sid, part, names, counts):
    prompts_t = oc_prompts(sid, with_time=True)
    win = bounds([t for t, _ in prompts_t], pick(len(prompts_t), part)[0])
    seen, writes = [], {}
    for mcreated, pdata in oc().execute(
        "select m.time_created, p.data from part p join message m on m.id = p.message_id "
        "where p.session_id = ? order by p.time_created",
        (sid,),
    ):
        if not within(mcreated, win):
            continue
        p = json.loads(pdata)
        if p.get("type") != "tool":
            continue
        st, n = p.get("state") or {}, p.get("tool") or "?"
        if "output" in st:
            e = {"tool": n, "sha256": sha(content_text(st.get("output")))}
            if st.get("status") == "error":
                e["failed"] = True
            seen.append(e)
        inp = st.get("input") or {}
        if (
            st.get("status") != "error"
            and n in ("write", "edit", "multiedit")
            and inp.get("filePath")
        ):
            writes[inp["filePath"]] = (
                inp.get("content")
                if n == "write" and isinstance(inp.get("content"), str)
                else None
            )
    rec = {
        "prompts": [{"sha256": sha(t)} for c, t in prompts_t if within(c, win)],
        "tool_results": seen,
    }
    limits = [
        "OpenCode keeps neither the system prompt nor tool definitions in its database"
    ]
    return rec, writes, limits


def make_record(r, tool, key, part, names, counts, hide, renames, turns=()):
    rec, writes, limits = {
        "claude": record_claude,
        "codex": record_codex,
        "opencode": record_opencode,
    }[tool](key, part, names, counts)
    made = [
        output_subject(p, w, r["ended"], names, n)
        for n, (p, w) in enumerate(writes.items(), 1)
    ]
    subjects = [s for s, _ in made if s]
    r["_outputs"] = [b for _, b in made if b]  # the files themselves, for --bundle only
    pred = {
        "receipt_no": r["receipt_no"],
        "receipt_version": VERSION,
        "tool": r["tool"],
        "part": r["part"],
    }
    if "version" not in hide:
        pred["tool_version"] = r.get("version")
    if "date" not in hide and "time" not in hide:
        pred["started"], pred["ended"] = r["started"], r["ended"]
    if "model" not in hide:
        pred["models"], pred["effort"] = r.get("models"), r.get("effort")
    if "settings" not in hide:
        pred["permissions"] = r.get("permissions")
    if "cost" not in hide and "cost_usd" in r:
        pred["cost_micro_usd"] = int(round(r["cost_usd"] * 1e6))
    for e in (
        rec.get("instructions") or []
    ):  # --rename applies here too, so the record can't undo it
        if e.get("name") in renames:
            e["name"] = renames[e["name"]]
    pred.update(rec)
    # each prompt's last reply: what the model said it did, to check a pasted answer against
    pred["replies"] = [
        {"turn": t["n"], "sha256": sha(t["reply"])} for t in turns if t.get("reply")
    ]
    pred["limits"] = limits + [
        "neither the tool nor the model takes a seed, so the same inputs can give a different output: "
        "this record lets a run be checked, not repeated",
        "made after the run from its log, so it shows what the log said when it was made",
    ]
    stmt = {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": subjects,
        "predicateType": RECORD_TYPE,
        "predicate": pred,
    }
    no_floats(stmt)
    data = canon(stmt)
    inputs = (
        len(pred.get("system_prompt", []))
        + len(pred.get("instructions", []))
        + len(pred.get("tool_results", []))
    )
    r["record"] = {
        "sha256": sha(data),
        "prompts": len(pred["prompts"]),
        "inputs": inputs,
        "outputs": len(subjects),
    }
    return data


def browser():
    """-> a Chrome, Edge or Chromium to take a screenshot with ($RECEIPT_BROWSER first), or None"""
    if os.environ.get("RECEIPT_BROWSER"):
        return os.environ["RECEIPT_BROWSER"]
    for n in (
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "microsoft-edge",
        "msedge",
        "chrome",
    ):
        if shutil.which(n):
            return shutil.which(n)
    for p in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ):
        if os.path.exists(p):
            return p
    return None


class QuietFiles(http.server.SimpleHTTPRequestHandler):
    def log_message(
        self, *args
    ):  # the browser's requests for the page's files aren't news
        pass


def shot(outputs, tmp):
    """-> a PNG of the first page the run made, taken with a headless browser, from the files that go in the
    bundle, laid out in their folders. They are served from 127.0.0.1, and only while the picture is taken:
    browsers won't run a page's module scripts from a file:// address, so a page opened that way can come out
    blank. Only a copy of the run's own files is served, so the page can't read anything else on this computer"""
    pages = [
        o
        for o in outputs
        if os.path.splitext(o["name"])[1].lower() in (".html", ".htm", ".svg")
    ]
    if not pages:
        sys.exit(
            "receipt: --shot found no page (.html or .svg) among the files the run wrote"
        )
    page = pages[0]
    top = os.path.commonpath(
        [os.path.dirname(os.path.abspath(o["path"])) for o in outputs]
    )
    rel = os.path.relpath(os.path.abspath(page["path"]), top)
    folder = os.path.join(tmp, "page")
    for o in outputs:
        dest = os.path.join(folder, os.path.relpath(os.path.abspath(o["path"]), top))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(o["body"])
    if not all(o["same_on_disk"] for o in outputs):
        print(
            "receipt: some files changed after the run, so the screenshot is of the files as the run wrote "
            "them; files it didn't write aren't in it",
            file=sys.stderr,
        )
    b = browser()
    if not b:
        sys.exit(
            "receipt: --shot needs Chrome, Edge or Chromium, and none was found; "
            "set RECEIPT_BROWSER to the browser's path"
        )
    png = os.path.join(tmp, "preview.png")
    # no --user-data-dir: given a profile of its own, Chromium starts as a whole browser and doesn't exit
    srv = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(QuietFiles, directory=folder)
    )
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/" + urllib.parse.quote(
        rel.replace(os.sep, "/")
    )
    cmd = [b, "--headless", "--disable-gpu", "--hide-scrollbars", f"--screenshot={png}",
           "--window-size=1280,800", "--virtual-time-budget=5000", url]  # fmt: skip
    try:
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                 start_new_session=os.name != "nt")  # fmt: skip
        except OSError as e:
            sys.exit(f"receipt: --shot couldn't start {b}: {e}")
        try:
            said = "".join(p.communicate(timeout=60))
        except subprocess.TimeoutExpired:
            kill_tree(p)
            sys.exit(f"receipt: --shot: {b} took over 60 s and was stopped")
    finally:
        srv.shutdown()
        srv.server_close()
    if not os.path.exists(png):
        sys.exit(f"receipt: --shot: {b} made no picture ({said.strip()[-300:]})")
    with open(png, "rb") as fh:
        return fh.read()


def kill_tree(p):
    """a browser starts helper processes; stop them all, not just the first"""
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True
        )
    else:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            p.kill()
    p.wait()


def bundle(path, r, s, payload, record, outputs, a):
    """one zip, an RO-Crate (w3id.org/ro/crate/1.2): the receipt, the record and the files the run wrote,
    with ro-crate-preview.html so it opens in a browser"""
    tmp = tempfile.mkdtemp(prefix="receipt-")
    try:
        files = {
            "receipt.txt": (s + "\n").encode("utf-8"),
            "receipt.json": (payload + "\n").encode("utf-8"),
        }
        rec = os.path.join(tmp, "record.json")
        with open(rec, "wb") as fh:
            fh.write(record)
        files["record.json"] = record
        if a.sign:
            sign(a.sign, rec)
            with open(rec + ".sig", "rb") as fh:
                files["record.json.sig"] = fh.read()
        outs = {}
        for o in outputs:
            outs["outputs/" + o["name"]] = o["body"]
        files.update(outs)
        if a.shot:
            files["preview.png"] = shot(outputs, tmp)
    finally:
        shutil.rmtree(
            tmp, ignore_errors=True
        )  # a browser can leave files behind for a moment
    files["ro-crate-metadata.json"] = canon(crate(r, files, outs))
    files["ro-crate-preview.html"] = preview(r, s, files).encode("utf-8")
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(files):
            z.writestr(name, files[name])
    print(
        f"receipt: bundle saved to {path} ({many(len(outs), 'file')} the run wrote)",
        file=sys.stderr,
    )


TOOL_URLS = {  # RO-Crate asks for a url on each piece of software
    "Claude Code": "https://github.com/anthropics/claude-code",
    "Codex CLI": "https://github.com/openai/codex",
    "OpenCode": "https://opencode.ai",
}


CRATE_PARTS = {
    "receipt.txt": "the receipt, as receipt.py printed it",
    "receipt.json": "the receipt as JSON",
    "record.json": "an in-toto Statement: SHA-256 fingerprints of what went into the run and the files it wrote",
    "record.json.sig": "an SSH signature of record.json",
    "preview.png": "a screenshot of the page the run made, from the files in this bundle",
}


def crate(r, files, outs):
    today = datetime.date.today().isoformat()
    run = {"@id": "#run", "@type": "CreateAction", "name": f"{r['tool']} run ({r['part']})",
           "instrument": {"@id": "#tool"}, "result": [{"@id": f} for f in outs]}  # fmt: skip
    if r.get("started"):
        run["startTime"], run["endTime"] = r["started"], r["ended"]
    graph = [
        {"@id": "ro-crate-metadata.json", "@type": "CreativeWork",
         "conformsTo": {"@id": "https://w3id.org/ro/crate/1.2"}, "about": {"@id": "./"}},
        {"@id": "./", "@type": "Dataset", "name": f"Prompt receipt no. {r['receipt_no']}",
         "description": f"A {r['tool']} run: its receipt, a record of fingerprints of what went in and came out, "
                        f"and the files it wrote. Made with receipt.py {VERSION} ({SITE}).",
         "datePublished": today, "license": {"@id": "#license"},
         "hasPart": [{"@id": f} for f in sorted(files) if f != "ro-crate-metadata.json"], "mentions": {"@id": "#run"}},
        {"@id": "#license", "@type": "CreativeWork", "name": "No license given",
         "description": "Ask whoever shared this bundle before reusing the files in it."},
        {"@id": "#tool", "@type": "SoftwareApplication", "name": r["tool"], "url": TOOL_URLS[r["tool"]],
         "version": r.get("version") or "not recorded"},
        run,
    ]  # fmt: skip
    for f in sorted(files):
        if f != "ro-crate-metadata.json":
            graph.append({"@id": f, "@type": "File", "name": f.split("/")[-1],
                          "description": CRATE_PARTS.get(f, "a file the run wrote"),
                          "contentSize": str(len(files[f])),
                          "encodingFormat": mimetypes.guess_type(f)[0] or "application/octet-stream"})  # fmt: skip
    return {"@context": "https://w3id.org/ro/crate/1.2/context", "@graph": graph}


def preview(r, s, files):
    links = "".join(
        f'<li><a href="{html.escape(f)}">{html.escape(f)}</a></li>'
        for f in sorted(files)
        if f != "ro-crate-preview.html"
    )
    img = (
        '<p><img src="preview.png" alt="what the run made" style="max-width:100%"></p>'
        if "preview.png" in files
        else ""
    )
    return (
        '<!doctype html><meta charset="utf-8"><title>Prompt receipt no. '
        f'{html.escape(r["receipt_no"])}</title><body style="font-family:system-ui;max-width:52rem;margin:2rem auto">'
        f'<pre style="background:#f8f5ee;padding:1.2rem;white-space:pre-wrap">{html.escape(s)}</pre>{img}'
        f"<h2>In this bundle</h2><ul>{links}</ul><p>Check the files against the record with "
        f'<code>python3 receipt.py --verify record.json outputs/*</code> (<a href="{SITE}">receipt.py</a>).</p>'
    )


def sign(key, path):
    sig = path + ".sig"
    if os.path.exists(sig):
        os.remove(sig)  # ssh-keygen won't write over an old signature
    try:
        p = subprocess.run(
            [
                "ssh-keygen",
                "-Y",
                "sign",
                "-f",
                os.path.expanduser(key),
                "-n",
                SIGN_NS,
                path,
            ],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        sys.exit(
            "receipt: --sign needs ssh-keygen (OpenSSH 8.0 or newer), and it isn't installed"
        )
    if p.returncode or not os.path.exists(sig):
        sys.exit(
            f"receipt: ssh-keygen couldn't sign {path}: {p.stderr.strip() or p.stdout.strip()}"
        )
    print(f"receipt: signed, signature in {sig}", file=sys.stderr)


def file_hashes(path):
    """a file's sha256, plus its text's with Windows line ends and a final newline taken off, since a log
    keeps a file's text the way the tool read it"""
    with open(path, "rb") as fh:
        b = fh.read()
    hs = {sha(b)}
    try:
        t = b.decode("utf-8")
    except UnicodeDecodeError:
        return hs
    for v in (
        t,
        t.rstrip("\n"),
        t.replace("\r\n", "\n"),
        t.replace("\r\n", "\n").rstrip("\n"),
    ):
        hs.add(sha(v))
    return hs


def verify(files, signers):
    bad = False
    for f in files:
        if not os.path.exists(f):
            sys.exit(f"receipt: no file {f}")
        sig = f + ".sig"
        if not os.path.exists(sig):
            continue
        who = None
        try:
            if signers:
                fp = subprocess.run(
                    ["ssh-keygen", "-Y", "find-principals", "-f", signers, "-s", sig],
                    capture_output=True,
                    text=True,
                )
                who = fp.stdout.strip().split("\n")[0] if fp.returncode == 0 else None
                if not who:
                    print(f"{f}: signed, but not by a key in {signers}")
                    bad = True
                    continue
                cmd = [
                    "ssh-keygen",
                    "-Y",
                    "verify",
                    "-f",
                    signers,
                    "-I",
                    who,
                    "-n",
                    SIGN_NS,
                    "-s",
                    sig,
                ]
            else:
                cmd = ["ssh-keygen", "-Y", "check-novalidate", "-n", SIGN_NS, "-s", sig]
            with open(f, "rb") as fh:
                v = subprocess.run(cmd, stdin=fh, capture_output=True, text=True)
        except FileNotFoundError:
            sys.exit(
                "receipt: checking a signature needs ssh-keygen (OpenSSH 8.0 or newer)"
            )
        if v.returncode == 0:
            key = re.search(r"(\w+ key SHA256:\S+)", v.stdout + v.stderr)
            print(
                f"{f}: good signature"
                + (f" by {who}" if who else "")
                + (f" ({key.group(1)})" if key else "")
                + ("" if who else "; add --signers FILE to check whose key it is")
            )
        else:
            print(
                f"{f}: BAD signature: the file changed after it was signed, or the signature isn't for it"
            )
            bad = True
    try:
        with open(files[0], "rb") as fh:
            data = fh.read()
        stmt = json.loads(data)
    except (OSError, ValueError):
        stmt = None
    if not (isinstance(stmt, dict) and stmt.get("predicateType") == RECORD_TYPE):
        if len(files) > 1:
            sys.exit(
                f"receipt: {files[0]} isn't a record made with --record, so the other files can't be matched"
            )
        if not os.path.exists(files[0] + ".sig"):
            sys.exit(
                f"receipt: {files[0]} has no signature next to it ({files[0]}.sig) and isn't a record"
            )
        sys.exit(1 if bad else 0)
    pred = stmt["predicate"]
    canonical = canon(stmt) == data
    print(
        f"{files[0]}: record of {pred['tool']} receipt no. {pred['receipt_no']}, sha256 {sha(data)}"
        + (
            ""
            if canonical
            else " (not in the byte form it was made in, so its hash differs from the receipt's)"
        )
    )
    known = {}
    for s in stmt.get("subject") or []:
        known.setdefault(
            s["digest"]["sha256"],
            f"came out of the run: {s['name']} ({s['annotations']['source']})",
        )
    for e in pred.get("instructions") or []:
        known.setdefault(
            e["sha256"], f"went in: instruction file {e.get('name') or e.get('kind')}"
        )
    for e in pred.get("system_prompt") or []:
        known.setdefault(e["sha256"], "went in: the system prompt")
    for i, e in enumerate(pred.get("prompts") or [], 1):
        known.setdefault(e["sha256"], f"went in: prompt {i}")
    for e in pred.get("replies") or []:
        known.setdefault(
            e["sha256"], f"came out: the model's reply to prompt {e['turn']}"
        )
    for e in pred.get("tool_results") or []:
        if e.get("file_sha256"):
            known.setdefault(
                e["file_sha256"],
                f"went in: the model read it ({e.get('file')}, lines {e.get('lines', '?')})",
            )
        known.setdefault(e["sha256"], f"went in: {e['tool']} showed it to the model")
    for f in files[1:]:
        hit = next((known[h] for h in file_hashes(f) if h in known), None)
        print(f"{f}: {hit or 'NOT in this record'}")
        bad |= hit is None
    sys.exit(1 if bad else 0)


# ---------- checks on what was read ----------


def check(r):
    """a log that parses but holds none of what a run leaves behind usually means the tool changed its format"""
    w = []
    if not r.get("prompts"):
        w.append("found no prompts from you in this log")
    elif not r.get("models"):
        w.append("found your prompts but no model reply")
    elif not (r.get("tokens_in") or r.get("tokens_out")):
        w.append("found model replies but no token counts")
    r["warnings"] = w
    for msg in w:
        print(
            f"receipt: warning: {msg}. If this run did get replies, {r['tool']} may have changed how it "
            f"writes its logs and parts of this receipt may be wrong; please report it at {ISSUES} "
            f"(receipt.py {VERSION})",
            file=sys.stderr,
        )


HOME_PATH = re.compile(
    r"(?:/home/|/Users/|/mnt/[a-z]/Users/|[A-Za-z]:\\+Users\\+|[A-Za-z]:/Users/)[^/\\\s'\"`]+",
    re.I,
)
# the same folders as Claude Code names its project folders: -home-me, -Users-me, C--Users-me, -mnt-c-Users-me
HOME_SLUG = re.compile(r"(?:[A-Za-z]-|-mnt-[a-z])?-(?:home|Users)-[A-Za-z0-9_]+")
SECRETS = [
    ("email", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}")),
    ("key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "key",
        re.compile(
            r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_\w{20,}|AKIA[0-9A-Z]{16}"
            r"|xox[abposr]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,}|hf_[A-Za-z0-9]{30,}|glpat-[\w-]{20,})"
        ),
    ),
    # a long run of letters and digits mixing cases looks like a token; hex hashes are one case, so they pass
    (
        "key",
        re.compile(r"\b(?=[\w-]*[a-z])(?=[\w-]*[A-Z])(?=[\w-]*\d)[A-Za-z0-9_-]{32,}\b"),
    ),
]


def scrub(text, redact, where_="your prompt", flag="--prompt"):
    """home folders -> ~; an email address or key stops the receipt unless --redact"""
    text = HOME_PATH.sub("~", text.replace(slug(home()), "~"))
    text = HOME_SLUG.sub("~", text)
    found = collections.Counter()
    for kind, rx in SECRETS:
        if redact:
            text = rx.sub(f"[{kind}]", text)
        else:
            found[kind] += len(rx.findall(text))
    if found and sum(found.values()):
        what = " and ".join(
            many(n, "email address" if k == "email" else "key-like string")
            for k, n in found.items()
            if n
        )
        sys.exit(
            f"receipt: {where_} holds {what}, so it was not printed. Leave out {flag}, "
            "or add --redact to print it with [email] and [key] in their place"
        )
    return text


def prompt_id(text):
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()[:12]


def receipt_no(*parts):
    """the same session and part always get the same number, and it gives nothing away about the session"""
    h = sha("\n".join(map(str, parts)))
    return f"{h[:4]}-{h[4:8]}"


# ---------- leaving things out ----------

NAMED = [
    "skills_used",
    "mcp_used",
    "subagents",
    "plugins_used",
    "memory",
    "models",
    "background_models",
    "providers",
    "file_names",
]


def rename(r, pairs):
    for pair in pairs:
        if "=" not in pair:
            sys.exit(f"receipt: --rename needs old=new, got {pair!r}")
        old, new = pair.split("=", 1)
        hit = False
        for key in NAMED:
            v = r.get(key)
            if isinstance(v, dict) and old in v:
                v[new] = v.pop(old) + v.get(new, 0) if new in v else v.pop(old)
                hit = True
            elif isinstance(v, list):
                for i, x in enumerate(v):
                    base = re.sub(r" \(.*\)$", "", x)
                    if base == old:
                        v[i] = new + x[len(base) :]
                        hit = True
        for it in r.get("items") or []:  # the priced lines name each model too
            if it["model"] == old:
                it["model"] = new
                hit = True
        if not hit:
            names = sorted(
                {
                    re.sub(r" \(.*\)$", "", str(x))
                    for k in NAMED
                    for x in (r.get(k) or [])
                }
            )
            sys.exit(
                f"receipt: --rename {old!r} isn't on this receipt, so nothing was renamed. Names on it: {', '.join(names) or 'none'}"
            )


def counts_only(r):
    for key in ("skills_used", "mcp_used"):  # how many different ones
        if r.get(key):
            r[key] = {"count": len(r[key])}
    if r.get("subagents"):  # how many ran
        r["subagents"] = {"count": sum(r["subagents"].values())}
    if "plugins_used" in r:
        r["plugins_used"] = len(r["plugins_used"])
    if r.get("memory") is not None:
        r["memory"] = len(r["memory"])
    r.pop("file_names", None)


DROP = {
    "version": ["version"],
    "date": ["started", "ended"],
    "model": ["models", "background_models", "effort", "providers"],
    "time": ["started", "ended", "duration_ms", "model_time_ms", "prompts"],
    "cost": ["cost_usd", "cost_note"],
    "items": ["items", "prices", "cost_check", "extras"],
    "billing": ["billing"],
    "tokens": ["tokens_in", "tokens_cached", "tokens_out", "tokens_note"],
    "work": [
        "tool_calls",
        "shell_commands",
        "web",
        "images_made",
        "lines_changed",
        "tool_errors",
        "interrupted",
        "model_errors",
    ],
    "files": [
        "files_written",
        "files_deleted",
        "file_types",
        "file_names",
        "files_note",
    ],
    "addons": [
        "skills_used",
        "skills_available",
        "mcp_used",
        "mcp_connected",
        "plugins_used",
        "plugins_available",
        "subagents",
    ],
    "hooks": ["hooks", "hooks_added_context"],
    "memory": ["memory"],
    "settings": ["permissions"],
}


# ---------- adding receipts up, or setting them side by side ----------


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            r = json.load(fh)
    except (OSError, ValueError) as e:
        sys.exit(
            f"receipt: can't read {path} as a JSON receipt ({e}); make one with --json --out FILE.json"
        )
    if not isinstance(r, dict) or "tool" not in r or "part" not in r:
        sys.exit(f"receipt: {path} isn't a receipt made with --json")
    if "duration_ms" not in r and r.get("started") and r.get("ended"):
        r["duration_ms"] = (
            when(r["ended"]) - when(r["started"])
        ).total_seconds() * 1000
    return r


def hidden_in(rs):
    """parts left out of any of the receipts, which a total therefore can't include"""
    return {
        part
        for part, keys in DROP.items()
        if any(not any(k in r for k in keys) for r in rs)
    }


def counted(v):
    """a names dict or a {"count": n} -> how many"""
    if isinstance(v, dict):
        return v["count"] if set(v) == {"count"} else len(v)
    return v if isinstance(v, int) else len(v or [])


def combine(rs):
    hide = hidden_in(rs)
    rs = sorted(rs, key=lambda x: x.get("started") or "")
    tools = list(dict.fromkeys(x["tool"] for x in rs))
    r = {
        "tool": " + ".join(tools),
        "part": f"{len(rs)} receipts added up",
        "receipt_version": VERSION,
        "combined": len(rs),
    }
    # each tool's versions in time order: "Claude Code 2.1.268 → 2.1.278 + Codex CLI 0.128.0"
    r["version"] = " + ".join(
        (f"{t} " if len(tools) > 1 else "")
        + span(x.get("version") for x in rs if x["tool"] == t)
        for t in tools
    )
    if len(tools) > 1:
        r["tool"] = ""
    r["models"] = list(dict.fromkeys(m for x in rs for m in x.get("models") or []))
    r["background_models"] = sorted(
        {m for x in rs for m in x.get("background_models") or []}
    )
    r["providers"] = list(
        dict.fromkeys(m for x in rs for m in x.get("providers") or [])
    )
    r["effort"] = span(x.get("effort") for x in rs)
    r["permissions"] = span(x.get("permissions") for x in rs)
    r["billing"] = " + ".join(
        dict.fromkeys(x["billing"] for x in rs if x.get("billing"))
    )
    if all(x.get("started") for x in rs):
        r["started"] = min(x["started"] for x in rs)
        r["ended"] = max(x["ended"] for x in rs)
    for k in (
        "prompts", "duration_ms", "model_time_ms", "tool_calls", "shell_commands", "web",
        "images_made", "tool_errors", "interrupted", "model_errors", "hooks_added_context",
        "files_written", "files_deleted",
    ):  # fmt: skip
        if any(x.get(k) is not None for x in rs):
            r[k] = sum(x.get(k) or 0 for x in rs)
    with_cost = [x for x in rs if "cost_usd" in x]
    if with_cost:
        r["cost_usd"] = round(sum(x["cost_usd"] for x in with_cost), 6)
        r["cost_note"] = (
            "added up"
            if len(with_cost) == len(rs)
            else f"{len(with_cost)} of {len(rs)} receipts have a cost; the others' tools log no price"
        )
    else:
        r["cost_note"] = span(x.get("cost_note") for x in rs)
    merged = {}
    for x in rs:
        for it in x.get("items") or []:
            k = (it["model"], it["kind"], it.get("rate"))
            if k not in merged:
                merged[k] = dict(it)
                continue
            for f in ("count", "usd"):
                if f in it:
                    merged[k][f] = merged[k].get(f, 0) + it[f]
    r["items"] = list(merged.values())
    for it in r["items"]:
        if "usd" in it:
            it["usd"] = round(it["usd"], 6)
    r["prices"] = span(x.get("prices") for x in rs)
    if with_cost and all(x.get("cost_check") for x in with_cost):
        r["cost_check"] = {
            k: round(sum(x["cost_check"][k] for x in with_cost), 6)
            for k in ("lines_usd", "own_usd")
        }
    r["extras"] = dict(
        sum(
            (collections.Counter(x.get("extras") or {}) for x in rs),
            collections.Counter(),
        )
    )
    r["receipt_no"] = receipt_no(
        "combined", *sorted(x.get("receipt_no") or "" for x in rs)
    )
    with_tokens = [x for x in rs if "tokens_in" in x]
    if with_tokens:
        for k in ("tokens_in", "tokens_cached", "tokens_out"):
            r[k] = sum(x.get(k) or 0 for x in with_tokens)
        if len(with_tokens) < len(rs):
            r["tokens_note"] = (
                f"{len(with_tokens)} of {len(rs)} receipts have token counts"
            )
    if all(x.get("lines_changed") for x in rs):
        r["lines_changed"] = [sum(x["lines_changed"][i] for x in rs) for i in (0, 1)]
    r["file_types"] = dict(
        sum(
            (collections.Counter(x.get("file_types") or {}) for x in rs),
            collections.Counter(),
        )
    )
    if all("file_names" in x for x in rs):
        r["file_names"] = sorted({n for x in rs for n in x["file_names"]})
    if len(rs) > 1:
        r["files_note"] = "added up, so a file edited in two parts counts twice"
    for k in ("skills_used", "mcp_used", "subagents"):
        vals = [x.get(k) for x in rs if x.get(k) is not None]
        if any(isinstance(v, dict) and set(v) == {"count"} for v in vals):
            r[k] = {"count": sum(counted(v) for v in vals)}
        elif vals:
            r[k] = dict(
                sum((collections.Counter(v) for v in vals), collections.Counter())
            )
    for k in ("skills_available", "mcp_connected", "plugins_available"):
        vals = [x[k] for x in rs if x.get(k) is not None]
        if vals:
            r[k] = max(vals)
    for k in ("plugins_used", "memory"):
        vals = [x.get(k) for x in rs if x.get(k) is not None]
        if any(isinstance(v, int) for v in vals):
            r[k] = sum(counted(v) for v in vals)
        elif vals:
            r[k] = sorted({n for v in vals for n in v})
        elif k == "memory":
            r[k] = None
    hk = [x.get("hooks") for x in rs if x.get("hooks") is not None]
    r["hooks"] = (
        dict(sum((collections.Counter(h) for h in hk), collections.Counter()))
        if hk
        else None
    )
    r["warnings"] = sorted({w for x in rs for w in x.get("warnings") or []})
    prompts = {x.get("first_prompt") for x in rs}
    if len(prompts) == 1:
        r["first_prompt"] = prompts.pop()
    ids = {x.get("prompt_id") for x in rs}
    if len(ids) == 1 and None not in ids:
        r["prompt_id"] = ids.pop()
    for part in hide:
        for k in DROP[part]:
            r.pop(k, None)
        print(
            f"receipt: {part} is left out of at least one receipt, so the total leaves it out",
            file=sys.stderr,
        )
    return r, hide


def same_prompt(rs):
    ids = [x.get("prompt_id") for x in rs]
    if None in ids:
        return None
    return len(set(ids)) == 1


def compare(rs, hide):
    def cell(r, row):
        if row == "tool":
            return f"{r['tool']} {r.get('version', '')}".strip()
        if row == "model":
            return ", ".join(r.get("models") or []) or "?"
        if row == "effort":
            return r.get("effort") or "?"
        if row == "date":
            return (
                f"{when(r['started']).day} {when(r['started']):%b %Y}"
                if r.get("started")
                else "-"
            )
        if row == "time":
            return mins(r["duration_ms"]) if r.get("duration_ms") is not None else "-"
        if row == "cost":
            c = r.get("cost_usd")
            return "-" if c is None else f"${c:.2f}" if c >= 0.01 else "<$0.01"
        if row == "tokens":
            return (
                f"{toks(r['tokens_in'])} in, {toks(r['tokens_out'])} out"
                if "tokens_in" in r
                else "-"
            )
        if row == "calls":
            return (
                f"{r['tool_calls']} ({r.get('tool_errors') or 0} failed)"
                if "tool_calls" in r
                else "-"
            )
        if row == "files":
            return str(r["files_written"]) if "files_written" in r else "-"
        if row == "prompt":
            return r.get("prompt_id") or "-"

    rows = [
        ("tool", "version"), ("model", "model"), ("effort", "model"), ("date", "date"),
        ("time", "time"), ("cost", "cost"), ("tokens", "tokens"), ("calls", "work"),
        ("files", "files"), ("prompt", None),
    ]  # fmt: skip
    hide = hide | hidden_in(rs)
    grid = [
        [row] + [cell(r, row) for r in rs]
        for row, part in rows
        if part is None or part not in hide
    ]
    width = [min(max(len(line[i]) for line in grid), 26) for i in range(len(grid[0]))]
    width[0] = 7  # labels line up with a receipt's: 7 wide + 2 spaces
    same = same_prompt(rs)
    head = f"Comparison · {len(rs)} runs · " + (
        f"the same prompt (id {rs[0]['prompt_id']})"
        if same
        else "different prompts"
        if same is False
        else "prompt not fingerprinted (make each receipt with --prompt-id)"
    )
    out = [f"Receipt v{VERSION} · {head}"]
    for line in grid:
        out.append(
            "  ".join(
                (c if len(c) <= w else c[: w - 1] + "…").ljust(w)
                for c, w in zip(line, width)
            ).rstrip()
        )
    return "\n".join(out), same


# ---------- printing ----------


def names(d):
    if isinstance(d, dict) and set(d) == {"count"}:
        return f"{d['count']} used"
    return (
        ", ".join(
            f"{k}" + (f" ×{v}" if v > 1 else "") for k, v in sorted((d or {}).items())
        )
        or "none"
    )


def money(x):
    return f"${x:,.2f}" if x >= 0.005 else "$0.00" if not x else "<$0.01"


def rate_text(per_m):
    """$ per million tokens with at least two decimals: $20.00, $0.20, $0.0125"""
    s = f"{per_m:.4f}".rstrip("0")
    return "$" + (s + "0" * (2 - len(s.split(".")[1])))


def clock(dt):
    """3:05 PM EDT; Windows names zones in words, so there it's the offset: 3:05 PM UTC-4"""
    zone = dt.tzname() or ""
    if not zone or " " in zone or len(zone) > 5:
        off = int(dt.utcoffset().total_seconds() // 60)
        zone = f"UTC{'+' if off >= 0 else '-'}{abs(off) // 60}" + (
            f":{abs(off) % 60:02d}" if off % 60 else ""
        )
    return (
        f"{dt.hour % 12 or 12}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'} {zone}"
    )


def item_lines(r, width=80):
    """a receipt's line items: each model, then what it used, how much, at what price, and what that came to"""
    out, model = [], None
    for it in r["items"]:
        if it["model"] != model:
            model = it["model"]
            out.append(" " * 9 + model)
        k = it["kind"]
        if k == "own figure":
            out.append(
                f"{'':11}{'calls logged with no detail':<35}{money(it['usd']):>9}"
            )
        elif k == "no price":
            out.append(f"{'':11}{toks(it['count'])} tokens, no price for this model")
        else:
            qty = (
                f"{it['count']} × {money(it['rate'] / 1e6)}"
                if k == "web search"
                else f"{toks(it['count'])} × {rate_text(it['rate'])}/M"
            )
            out.append(f"{'':11}{k:<18}{qty:>17}{money(it['usd']):>9}")
    ex = r.get("extras") or {}
    extra = []
    if ex.get("fast_calls"):
        extra.append(f"fast mode on {many(ex['fast_calls'], 'call')}")
    if ex.get("us_only_calls"):
        extra.append(f"US-only processing on {many(ex['us_only_calls'], 'call')}")
    if ex.get("thinking_ms"):
        extra.append(f"thinking {mins(ex['thinking_ms'])}")
    if ex.get("retry_ms"):
        extra.append(f"waiting on retries {mins(ex['retry_ms'])}")
    if extra:
        out.append("extras   " + " · ".join(extra))
    chk = r.get("cost_check")
    if chk and abs(chk["lines_usd"] - chk["own_usd"]) >= 0.005:
        msg = (
            f"the lines add up to {money(chk['lines_usd'])}, not {money(chk['own_usd'])}: "
            f"{r['tool'] or 'the tool'}'s own total and its logged calls disagree, as they can in long "
            "sessions that were compacted or resumed"
        )
        out += [
            ("check    " if i == 0 else " " * 9) + w
            for i, w in enumerate(textwrap.wrap(msg, width - 9))
        ]
    out.append(f"prices   API list prices per million tokens ($/M), from {r['prices']}")
    return out


def text(r, hide, with_prompt, width=80):
    head = f"Receipt v{VERSION} · {r['tool']}"
    if "version" not in hide:
        head = f"{head} {r['version']}".replace("·  ", "· ")
    elif not r["tool"]:  # several tools added up, and their versions hidden
        head += " several tools"
    if "date" not in hide and r.get("started"):
        day = when(
            r["started"]
        )  # not %-d: Windows' strftime has no way to drop the leading zero
        end = when(r["ended"])
        head += f" · {day.day} {day:%b %Y}"
        if r.get("combined") and end.date() != day.date():
            head += f" → {end.day} {end:%b %Y}"
        elif "time" not in hide:
            head += f", {clock(day)}"
    if r["part"] != "whole session":
        head += f" · {r['part']}"
    if r.get("receipt_no"):
        head += f" · no. {r['receipt_no']}"
    out = [head]
    if "model" not in hide:
        bg = r.get("background_models")
        bg = f" (+ {', '.join(bg)} in the background)" if bg else ""
        via = [
            p
            for p in r.get("providers") or []
            if p != "openai" and not any(f"({p}" in m for m in r["models"])
        ]
        via = (
            " via "
            + ", ".join(p + (" (on this computer)" if p in LOCAL else "") for p in via)
            if via
            else ""
        )
        out.append(
            f"model    {', '.join(r['models']) or 'no model reply in this log'}{via}{bg} · effort {r['effort']}"
        )
    if "time" not in hide:
        took = mins(r["duration_ms"])
        if r.get("model_time_ms"):
            took += f" (model working {mins(r['model_time_ms'])})"
        out.append(
            f"time     {took} · {r['prompts']} prompt{'s' if r['prompts'] != 1 else ''} from me"
        )
    if "cost" not in hide:
        if "cost_usd" in r:
            note, chk = r["cost_note"], r.get("cost_check")
            if (
                chk
                and "items" not in hide
                and abs(chk["lines_usd"] - chk["own_usd"]) < 0.005
            ):
                note += "; the lines below add up to it"
            out.append(f"cost     {money(r['cost_usd'])} ({note})")
        else:
            out.append(f"cost     {r['cost_note']}")
        if "items" not in hide and r.get("items"):
            out += item_lines(r, width)
    if "billing" not in hide and r.get("billing"):
        out.append(f"billing  {r['billing']}")
    if "tokens" not in hide and "tokens_in" in r:
        note = f" ({r['tokens_note']})" if r.get("tokens_note") else ""
        out.append(
            f"tokens   in {toks(r['tokens_in'])} ({toks(r['tokens_cached'])} cached) · out {toks(r['tokens_out'])}{note}"
        )
    if "work" not in hide:
        work = f"{many(r['tool_calls'], 'tool call')}, {many(r['shell_commands'], 'shell command')} · web {r['web']}"
        if r.get("images_made"):
            work += f" · images made {r['images_made']}"
        if any(r.get("lines_changed") or []):
            work += f" · lines +{r['lines_changed'][0]} -{r['lines_changed'][1]}"
        if r.get("tool_errors"):
            work += f" · {many(r['tool_errors'], 'failed call')}"
        if r.get("model_errors"):
            work += f" · {many(r['model_errors'], 'model error')}"
        if r.get("interrupted"):
            work += f" · interrupted {r['interrupted']}×"
        out.append(f"work     {work}")
    if "files" not in hide and "files_written" in r:
        n = r["files_written"]
        if r.get("file_names"):
            fn = r["file_names"][
                :12
            ]  # names repeat across folders, so count the rest from n
            what = ", ".join(fn) + (f" and {n - len(fn)} more" if n > len(fn) else "")
        else:
            what = names(r.get("file_types"))
        line = f"files    {many(n, 'file')} written or edited" + (
            f" ({what})" if n else ""
        )
        if r.get("files_deleted"):
            line += f" · {r['files_deleted']} deleted"
        if r.get("files_note"):
            line += f" · {r['files_note']}"
        out.append(line)
    if "addons" not in hide:
        sk = f"skills {names(r.get('skills_used'))}"
        if r.get("skills_available") is not None:
            sk += f" (of {r['skills_available']} available)"
        mc = f"MCP {names(r.get('mcp_used'))}"
        if r.get("mcp_connected") is not None:
            mc += f" (of {r['mcp_connected']} connected)"
        line = f"add-ons  {sk} · {mc}"
        if "plugins_used" in r:
            pu = r["plugins_used"]
            pu = (
                f"{pu} used"
                if isinstance(pu, int) and pu
                else ""
                if isinstance(pu, int)
                else ", ".join(pu)
            ) or "none"
            line += f" · plugins {pu}" + (
                f" (of {r['plugins_available']} installed)"
                if r.get("plugins_available")
                else ""
            )
        if "subagents" in r:
            n = sum(r["subagents"].values())
            line += f" · subagents {n}" + (
                f" ({names(r['subagents'])})"
                if n and set(r["subagents"]) != {"count"}
                else ""
            )
        out.append(line)
    if "hooks" not in hide:
        h = r.get("hooks")
        if h is None:
            out.append(f"hooks    not in {r['tool'] or 'these'} logs")
        else:
            # Claude Code logs a hook run only when the hook says something, so the count is a floor
            line = (
                f"hooks    on {', '.join(sorted(h))} ({sum(h.values())} logged runs)"
                if h
                else "hooks    none logged"
            )
            if r.get("hooks_added_context"):
                line += f" · added context {many(r['hooks_added_context'], 'time')}"
            out.append(line)
    if "memory" not in hide:
        m = r.get("memory")
        m = (
            f"not in {r['tool'] or 'these'} logs"
            if m is None
            else (f"{m} file{'s' if m != 1 else ''}" if m else "none loaded")
            if isinstance(m, int)
            else (", ".join(m) or "none loaded")
        )
        out.append(f"memory   {m}")
    if "settings" not in hide:
        out.append(f"settings {r['permissions']}")
    if r.get("turns"):
        out += turn_lines(r, hide, width)
    if r.get("prompt_id"):
        out.append(f"id       {r['prompt_id']} (prompt fingerprint)")
    if r.get("record"):
        rec = r["record"]
        out.append(
            f"record   sha256 {rec['sha256'][:16]}… · fingerprints of {many(rec['prompts'], 'prompt')}, "
            f"{many(rec['inputs'], 'input')}, {many(rec['outputs'], 'file')} out"
        )
    if r.get("outcome"):
        out.append(
            labelled("outcome  ", r["outcome"] + " (the sender's own words)", width)
        )
    if with_prompt and r.get("prompt_texts") and not r.get("turns"):
        w = len(str(len(r["prompt_texts"])))
        for i, p in enumerate(r["prompt_texts"], 1):
            out.append(
                labelled(("prompts  " if i == 1 else " " * 9) + f"{i:>{w}}  ", p, width)
            )
    elif with_prompt and r.get("first_prompt") and not r.get("prompt_texts"):
        out.append(labelled("prompt   ", r["first_prompt"], width))
    if r.get("reply"):
        out.append(labelled("reply    ", r["reply"], width))
    if r.get("recipe"):
        out.append("rerun    " + "\n         ".join(r["recipe"]))
        out.append(
            "         (the same prompts and settings; no seed or temperature can be set, so not the same output)"
        )
    for w in r.get("warnings") or []:
        out.append(
            f"warning  {w}; receipt.py may not read this {r['tool'] or 'tool'} version right"
        )
    return "\n".join(out)


def labelled(label, body, width):
    """wrap long lines so the receipt pastes without scrolling sideways; keep the text's own line breaks.
    width is the room after the 9-column label, as text() takes it; a longer label takes its extra from it"""
    room = max(width - (len(label) - 9), 20)
    wrapped = [  # paths, links and commands stay whole, so they still work when copied
        w
        for p in body.strip().split("\n")
        for w in textwrap.wrap(p, room, break_on_hyphens=False, break_long_words=False)
        or [""]
    ]
    pad = " " * len(label)
    return "\n".join(
        ((label if i == 0 else pad) + w).rstrip() for i, w in enumerate(wrapped)
    )


def turn_lines(r, hide, width):
    rows = r["turns"]
    w = len(str(rows[-1]["n"]))
    out = []
    for i, t in enumerate(rows):
        bits = []
        if t.get("started"):
            bits.append(
                clock(when(t["started"])).rsplit(" ", 1)[0]
            )  # the zone is on the first line
        if "time_ms" in t:
            bits.append(mins(t["time_ms"]))
        if "cost_usd" in t:
            bits.append(money(t["cost_usd"]))
        if "tool_calls" in t:
            bits.append(
                many(t["tool_calls"], "tool call")
                + (
                    f", {many(t['shell_commands'], 'shell command')}"
                    if t["shell_commands"]
                    else ""
                )
            )
        if t.get("files"):
            bits.append(many(t["files"], "file"))
        label = ("turns    " if i == 0 else " " * 9) + f"{t['n']:>{w}}  "
        out.append((label + " · ".join(bits)).rstrip())
        if t.get("prompt"):
            out.append(labelled(" " * len(label), t["prompt"], width).rstrip("\n"))
    costs = [t["cost_usd"] for t in rows if "cost_usd" in t]
    if costs and len(costs) == len(rows) and "cost_usd" in r and len(rows) > 1:
        total, chk = sum(costs), r.get("cost_check") or {}
        if abs(total - r["cost_usd"]) < 0.005:
            note = "the turns add up to the cost above"
        elif chk and abs(total - chk["lines_usd"]) < 0.005:
            note = f"the turns add up to {money(total)}, as the priced lines do"
        else:
            note = f"the turns add up to {money(total)}, priced from the logged calls"
        out.append(" " * 9 + note)
    return out


# ---------- a picture of the receipt ----------

# font8x8 by Daniel Hepper, public domain (github.com/dhepper/font8x8): 8 bytes per character from
# space to ~, one per row, lowest bit leftmost; then four drawn here for · → × …
FONT = bytes.fromhex(
    "0000000000000000183c3c1818001800363600000000000036367f367f3636000c3e031e301f0c00"
    "006333180c6663001c361c6e3b336e000606030000000000180c0606060c1800060c1818180c0600"
    "00663cff3c660000000c0c3f0c0c000000000000000c0c060000003f0000000000000000000c0c00"
    "6030180c060301003e63737b6f673e000c0e0c0c0c0c3f001e33301c06333f001e33301c30331e00"
    "383c36337f3078003f031f3030331e001c06031f33331e003f3330180c0c0c001e33331e33331e00"
    "1e33333e30180e00000c0c00000c0c00000c0c00000c0c06180c0603060c180000003f00003f0000"
    "060c1830180c06001e3330180c000c003e637b7b7b031e000c1e33333f3333003f66663e66663f00"
    "3c66030303663c001f36666666361f007f46161e16467f007f46161e16060f003c66030373667c00"
    "3333333f333333001e0c0c0c0c0c1e007830303033331e006766361e366667000f06060646667f00"
    "63777f7f6b63630063676f7b736363001c36636363361c003f66663e06060f001e3333333b1e3800"
    "3f66663e366667001e33070e38331e003f2d0c0c0c0c1e003333333333333f0033333333331e0c00"
    "6363636b7f7763006363361c1c3663003333331e0c0c1e007f6331184c667f001e06060606061e00"
    "03060c18306040001e18181818181e00081c36630000000000000000000000ff0c0c180000000000"
    "00001e303e336e000706063e66663b0000001e3303331e003830303e33336e0000001e333f031e00"
    "1c36060f06060f0000006e33333e301f0706366e666667000c000e0c0c0c1e00300030303033331e"
    "070666361e3667000e0c0c0c0c0c1e000000337f7f6b630000001f333333330000001e3333331e00"
    "00003b66663e060f00006e33333e307800003b6e66060f0000003e031e301f00080c3e0c0c2c1800"
    "0000333333336e0000003333331e0c000000636b7f7f3600000063361c36630000003333333e301f"
    "00003f190c263f00380c0c070c0c38001818180018181800070c0c380c0c07006e3b000000000000"
)
FONT_EXTRA = {
    "·": bytes.fromhex("0000001818000000"),
    "→": bytes.fromhex("0010307f7f301000"),
    "×": bytes.fromhex("00663c183c660000"),
    "…": bytes.fromhex("000000000000db00"),
}
SAME = {"—": "-", "–": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "\t": " "}


def glyph(ch):
    if " " <= ch <= "~":
        o = (ord(ch) - 32) * 8
        return FONT[o : o + 8]
    if ch in FONT_EXTRA:
        return FONT_EXTRA[ch]
    plain = (
        SAME.get(ch)
        or unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode()[:1]
    )
    return glyph(plain) if plain else glyph("?")


def png(rows, scale=2):
    """rows: [(text, ink)] with ink 1 = dark, 3 = faint -> PNG bytes; paper strip with torn ends"""
    cw, lh, pad, tooth = 8 * scale, 12 * scale, 20 * scale, 5 * scale
    cols = max(len(t) for t, _ in rows)
    w = cols * cw + 2 * pad
    h = len(rows) * lh + 2 * pad + 2 * tooth
    img = [bytearray(w) for _ in range(h)]
    cache = {}
    for i, (line, ink) in enumerate(rows):
        y0 = tooth + pad + i * lh
        for gy in range(8):
            row = bytearray()
            for ch in line:
                key = (ch, gy, ink)
                if key not in cache:
                    bits = glyph(ch)[gy]
                    cache[key] = bytes(
                        ink if bits >> x & 1 else 0
                        for x in range(8)
                        for _ in range(scale)
                    )
                row += cache[key]
            for sy in range(scale):
                img[y0 + gy * scale + sy][pad : pad + len(row)] = row
    for x in range(w):  # torn paper at both ends: a zigzag of background
        d = abs(x % (2 * tooth) - tooth)
        for y in range(d):
            img[y][x] = 2
            img[h - 1 - y][x] = 2
    raw = b"".join(b"\x00" + bytes(r) for r in img)

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    palette = bytes([251, 248, 240, 38, 34, 30, 44, 49, 61, 100, 93, 85])
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 3, 0, 0, 0))
        + chunk(b"PLTE", palette)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


PNG_COLS = 62  # narrow enough to stay legible when a feed shrinks the picture to a phone's width


def fold(value, n):
    """split a line's value into pieces of at most n characters, breaking between its "·" items,
    and before a bracketed note rather than inside it"""
    out, cur = [], ""
    for item in value.split(" · "):
        joined = f"{cur} · {item}" if cur else item
        if len(joined) <= n:
            cur = joined
            continue
        if cur:
            out.append(cur)
        before, bracket, note = item.partition(" (")
        if len(item) <= n:
            pieces = [item]
        elif bracket and len(before) <= n and len(note) + 1 <= n:
            pieces = [before, "(" + note]
        else:  # names hold hyphens (claude-haiku-4-5): break at spaces only
            pieces = textwrap.wrap(item, n, break_on_hyphens=False) or [""]
        out += pieces[:-1]
        cur = pieces[-1]
    return out + [cur]


def picture(s, table=False):
    """a receipt's lines wrap under their label (s is made at PNG_COLS); a comparison table keeps its columns"""
    head, *body = s.split("\n")
    heads = fold(head, max([PNG_COLS] + [len(b) for b in body if table]))
    if not table:
        body = [
            (label if i == 0 else " " * 9) + piece
            for line in body
            for label, value in [(line[:9], line[9:])]
            for i, piece in enumerate(fold(value, PNG_COLS - 9))
        ]
    cols = max(len(x) for x in body + heads)
    rows = [(x, 1) for x in heads] + [("-" * cols, 3)]
    rows += [(x, 1) for x in body]
    rows += [
        ("-" * cols, 3),
        (f"made with receipt.py {VERSION} · musharna.github.io/prompt-receipts", 3),
    ]
    return png(rows)


# ---------- main ----------


def out_path(a, r, ext):
    p = os.path.expanduser(a.out)
    if os.path.isdir(p) or a.out.endswith(("/", "\\")):
        os.makedirs(p, exist_ok=True)
        day = (
            when(r["started"]).strftime("%Y-%m-%d-%H%M%S")
            if r.get("started")
            else "receipt"
        )
        tool = re.sub(r"[^a-z]+", "-", r["tool"].lower()).strip("-") or "combined"
        p = os.path.join(p, f"receipt-{day}-{tool}.{ext}")
    return p


def main():
    global PRICES, PRICES_FROM
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="parts for --hide: " + ", ".join(PARTS),
    )
    ap.add_argument("session", nargs="?")
    ap.add_argument("--version", action="version", version=f"receipt.py {VERSION}")
    ap.add_argument("--codex", action="store_true")
    ap.add_argument("--opencode", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--pick", type=int)
    ap.add_argument("--last", type=int)
    ap.add_argument("--turns", nargs="?", const="all", metavar="A-B")
    ap.add_argument("--hide", default="")
    ap.add_argument("--counts", action="store_true")
    ap.add_argument("--rename", action="append", default=[])
    ap.add_argument("--prompt", action="store_true")
    ap.add_argument("--redact", action="store_true")
    ap.add_argument("--prompt-id", action="store_true")
    ap.add_argument("--file-names", action="store_true")
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--png", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--hook", action="store_true")
    ap.add_argument("--combine", nargs="+", metavar="RECEIPT.json")
    ap.add_argument("--compare", nargs="+", metavar="RECEIPT.json")
    ap.add_argument("--prices", metavar="FILE")
    ap.add_argument("--record", metavar="FILE")
    ap.add_argument("--sign", metavar="KEY")
    ap.add_argument("--verify", nargs="+", metavar="FILE")
    ap.add_argument("--signers", metavar="FILE")
    ap.add_argument("--reply", action="store_true")
    ap.add_argument("--outcome", metavar="TEXT")
    ap.add_argument("--recipe", action="store_true")
    ap.add_argument("--link", action="store_true")
    ap.add_argument("--bundle", metavar="FILE.zip")
    ap.add_argument("--shot", action="store_true")
    a = ap.parse_args()
    # Windows writes files and pipes in its old code page, which has no "→" and would crash; use UTF-8
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    if a.verify:
        if any(
            v not in (None, False, [], "")
            for k, v in vars(a).items()
            if k not in ("verify", "signers")
        ):
            sys.exit(
                "receipt: --verify only checks files; give it the files, and --signers if you have one"
            )
        verify(a.verify, a.signers)
        return
    if a.signers:
        sys.exit("receipt: --signers goes with --verify")
    if a.prices:
        try:
            with open(os.path.expanduser(a.prices), encoding="utf-8") as fh:
                PRICES = price_table(json.load(fh))
        except (OSError, ValueError) as e:
            sys.exit(f"receipt: can't read {a.prices} as a price file ({e})")
        if not PRICES:
            sys.exit(
                f"receipt: no Anthropic or OpenAI prices in {a.prices}; it should be a copy of LiteLLM's "
                "model_prices_and_context_window.json"
            )
        PRICES_FROM = f"{base_name(a.prices)}, given with --prices"
    hide = {h.strip() for h in a.hide.split(",") if h.strip()}
    if hide - set(PARTS):
        sys.exit(
            f"receipt: --hide doesn't know {', '.join(sorted(hide - set(PARTS)))}; parts are: {', '.join(PARTS)}"
        )
    if "cost" in hide or "model" in hide:
        hide.add(
            "items"
        )  # the lines would give the total away, and name each model and its price
    if a.last is not None and a.last < 1:
        sys.exit("receipt: --last needs a number of prompts, 1 or more")
    part = ("last", a.last) if a.last else turn_range(a.turns)
    if a.last and part and a.turns not in (None, "all"):
        sys.exit("receipt: pick one of --last N and --turns A-B")
    if a.codex and a.opencode:
        sys.exit("receipt: pick one of --codex and --opencode")
    if a.redact and not (a.prompt or a.reply or a.outcome or a.recipe):
        sys.exit(
            "receipt: --redact changes text the receipt shows, so it needs --prompt, --reply, --recipe or --outcome"
        )
    if a.out and a.out.lower().endswith(".png"):
        a.png = True
    if a.out and a.out.lower().endswith(".json"):
        a.json = True
    if a.out and a.out.lower().endswith(".md"):
        a.md = True
    if a.png and not a.out:
        sys.exit("receipt: a picture needs a file: --out receipt.png")
    if sum(map(bool, (a.png, a.json, a.md))) > 1:
        sys.exit("receipt: pick one of --md, --json and --png")
    if a.hook and not a.out:
        sys.exit(
            "receipt: --hook needs --out (a file or folder), since hooks' output isn't shown"
        )
    many_in = a.combine or a.compare
    if a.combine and a.compare:
        sys.exit("receipt: pick one of --combine and --compare")
    if many_in and (
        a.session
        or a.list
        or a.pick
        or a.last
        or a.turns
        or a.hook
        or a.reply
        or a.recipe
    ):
        sys.exit("receipt: --combine and --compare read JSON receipts, not sessions")
    if a.shot and not a.bundle:
        sys.exit("receipt: --shot goes into a --bundle, so add --bundle FILE.zip")
    if a.bundle and (many_in or a.list):
        sys.exit(
            "receipt: --bundle covers one session, so it can't go with --combine, --compare or --list"
        )
    if a.record and (many_in or a.list):
        sys.exit(
            "receipt: --record covers one session, so it can't go with --combine, --compare or --list"
        )
    if a.sign and not (a.out or a.record):
        sys.exit(
            "receipt: --sign signs what is saved, so add --out FILE, --record FILE or both"
        )
    tool = "codex" if a.codex else "opencode" if a.opencode else "claude"

    if a.compare:
        rs = [load(f) for f in a.compare]
        s, same = compare(rs, hide)
        payload = (
            json.dumps({"same_prompt": same, "receipts": rs}, indent=1)
            if a.json
            else None
        )
        saved = emit(a, rs[0], s, payload, table=True)
        if a.sign and saved:
            sign(a.sign, saved)
        return
    if a.combine:
        r, left_out = combine([load(f) for f in a.combine])
        hide |= left_out
    else:
        if a.hook:
            try:
                payload = json.load(sys.stdin)
                path = payload["transcript_path"]
            except (ValueError, KeyError, TypeError) as e:
                sys.exit(
                    f"receipt: --hook expects Claude Code's hook input on stdin ({e!r})"
                )
            if not first_prompt_of("claude", path):
                print(
                    "receipt: this session has no prompts, so no receipt was saved",
                    file=sys.stderr,
                )
                return
            tool = "claude"
        elif a.session:
            path = a.session
            if not (a.codex or a.opencode):
                if a.session.startswith("ses_") and not os.path.exists(a.session):
                    tool = "opencode"
                elif (
                    os.path.basename(path).startswith("rollout-")
                    or os.path.abspath(path).startswith(codex_dir() + os.sep)
                    or "/.codex/" in os.path.abspath(path).replace(os.sep, "/")
                ):
                    tool = "codex"
        else:
            fs = sessions(tool, a.all)
            # a session with none of your prompts isn't a run (opening Claude Code and quitting leaves one)
            runs = ((f, p) for f in fs for p in [first_prompt_of(tool, f)] if p)
            scope = "any folder" if a.all else "this folder"
            if a.list:
                shown = list(itertools.islice(runs, 15))
                if not shown:
                    nothing_found(tool, a.all)
                for i, (f, p) in enumerate(shown, 1):
                    stamp = changed(tool, f).strftime("%d %b %H:%M")
                    folder = (
                        f"{base_name(folder_of(tool, f))[:18]:18}  " if a.all else ""
                    )
                    print(f"{i:3}  {stamp}  {folder}{p[:70]}")
                print(
                    "\nthen run it again with --pick N" + (" --all" if a.all else ""),
                    file=sys.stderr,
                )
                return
            n = a.pick or 1
            if n < 1:
                sys.exit("receipt: --pick needs a number from --list, 1 or more")
            path = next(itertools.islice(runs, n - 1, None), (None,))[0]
            if not path:
                found = sum(1 for f in fs if first_prompt_of(tool, f))
                if not found:
                    nothing_found(tool, a.all)
                sys.exit(
                    f"receipt: --pick {n}, but {scope} has {found} sessions (see --list)"
                )
        r = (
            opencode(path, part)
            if tool == "opencode"
            else codex(path, part)
            if tool == "codex"
            else claude(path, part)
        )
        r["receipt_version"] = VERSION
        r["duration_ms"] = round(
            (when(r["ended"]) - when(r["started"])).total_seconds() * 1000
        )
        r.setdefault("extras", {})
        r["receipt_no"] = receipt_no(r["tool"], r.pop("session_key"), r["part"])
        check(r)
        rows = []
        if (
            a.turns is not None
            or a.prompt
            or a.reply
            or a.recipe
            or a.record
            or a.bundle
        ):
            rows = {
                "claude": claude_turns,
                "codex": codex_turns,
                "opencode": opencode_turns,
            }[tool](path)
            sel, _ = pick(len(rows), part)
            rows = rows[sel[0] : sel[1]] if sel else rows
        add_turns(r, rows, a, hide)
    if a.rename:
        rename(r, a.rename)
    renames = dict(p.split("=", 1) for p in a.rename)
    if a.recipe:
        prompts = [
            scrub(t["prompt"], a.redact, "your prompt", "--recipe") for t in rows
        ]
        r["recipe"] = recipe(r, rows, prompts, hide, renames)
    if a.counts:
        counts_only(r)
    if not a.file_names:
        r.pop("file_names", None)
    if r.get("first_prompt") and (a.prompt or a.prompt_id) and "prompt_id" not in r:
        r["prompt_id"] = prompt_id(r["first_prompt"])
    if not a.prompt_id and not a.prompt:
        r.pop("prompt_id", None)
    if a.prompt and r.get("first_prompt"):
        r["first_prompt"] = scrub(r["first_prompt"], a.redact)
    else:
        r.pop("first_prompt", None)
    if a.outcome:
        r["outcome"] = scrub(
            a.outcome.strip(), a.redact, "your --outcome note", "--outcome"
        )
    record = None
    if a.record or a.bundle:
        record = make_record(
            r, tool, path, part, a.file_names, a.counts, hide, renames, rows
        )
    s = text(r, hide, a.prompt)
    if a.png:  # the picture is narrower, so its prompt wraps to fit
        s = text(r, hide, a.prompt, width=PNG_COLS - 9)
    outputs = r.pop("_outputs", [])
    payload = None
    if a.json or a.bundle:
        for part in hide:
            for key in DROP[part]:
                r.pop(key, None)
        payload = json.dumps(r, indent=1)
    if a.bundle:
        bundle(
            os.path.expanduser(a.bundle),
            r,
            text(r, hide, a.prompt),
            payload,
            record,
            outputs,
            a,
        )
        if not a.json:
            payload = None
    saved = [emit(a, r, s, payload)]
    if a.record:
        rp = os.path.expanduser(a.record)
        with open(rp, "wb") as fh:
            fh.write(record)
        print(f"receipt: record saved to {rp}", file=sys.stderr)
        saved.append(rp)
    for p in saved:
        if a.sign and p:
            sign(a.sign, p)
    if a.link:
        print(link(text(r, hide, a.prompt)))


def link(s):
    """-> a link to the site that shows this receipt; the receipt rides in the part after #, which browsers
    never send to the server, so nothing is uploaded"""
    z = zlib.compressobj(
        9, zlib.DEFLATED, -15
    )  # raw deflate, which browsers unpack with DecompressionStream
    packed = base64.urlsafe_b64encode(z.compress(s.encode("utf-8")) + z.flush()).rstrip(
        b"="
    )
    url = f"{SITE}r/#r1.{packed.decode()}"
    if len(url) > LINK_BUDGET:
        print(
            f"receipt: the link is {len(url):,} characters; Discord cuts messages at {LINK_BUDGET:,}, so it may "
            "not paste whole there. --hide parts or leave out --prompt to shorten it",
            file=sys.stderr,
        )
    return f"\nlink (the receipt is inside the link; nothing is uploaded):\n{url}"


def add_turns(r, rows, a, hide):
    """put what --turns, --prompt, --reply and --recipe asked for on the receipt; the text stays off unless asked"""
    texts = [t["prompt"] for t in rows]
    if a.turns is not None:
        keep = {
            "n",
            "started",
            "time_ms",
            "cost_usd",
            "tool_calls",
            "shell_commands",
            "files",
        }
        if "time" in hide or "date" in hide:
            keep -= {"started"}
        if "time" in hide:
            keep -= {"time_ms"}
        if "cost" in hide:
            keep -= {"cost_usd"}
        if "work" in hide:
            keep -= {"tool_calls", "shell_commands"}
        if "files" in hide:
            keep -= {"files"}
        r["turns"] = [{k: v for k, v in t.items() if k in keep} for t in rows]
    if a.prompt and len(texts) > 1:
        r["prompt_texts"] = [scrub(t, a.redact) for t in texts]
        if a.turns is not None:
            for t, x in zip(r["turns"], r["prompt_texts"]):
                t["prompt"] = x
    if a.reply:
        last = rows[-1]["reply"] if rows else None
        r["reply"] = (
            scrub(last, a.redact, "the model's reply", "--reply") if last else None
        )


EFFORTS = {"minimal", "low", "medium", "high", "xhigh", "max"}


def recipe(r, rows, prompts, hide, renames):
    """-> the commands that rerun these prompts, each on the model and effort it ran with; what --hide or
    --rename keeps off the receipt stays out of the commands too"""
    q = shlex.quote
    settings = "settings" not in hide and r.get("permissions") or ""
    cmds = []
    for i, (t, p) in enumerate(zip(rows, prompts)):
        model = effort = None
        if "model" not in hide:
            model = t["model"]
            if model:  # named as --rename names it on the receipt
                base = re.sub(r" \(.*\)$", "", model)
                model = renames.get(base, base) + model[len(base) :]
            else:
                model = (r.get("models") or [None])[0]
            effort = t["effort"] or (r.get("effort") or "").split(" → ")[0]
            effort = effort if effort in EFFORTS else None
        if r["tool"] == "Claude Code":
            mode = settings.split(" → ")[-1]
            tail = (f" --model {q(model)}" if model else "") + (
                f" --effort {effort}" if effort else ""
            )
            tail += (
                f" --permission-mode {q(mode)}"
                if mode and mode not in ("default", "not recorded")
                else ""
            )
            cmds.append(f"claude -p{' -c' if i else ''} {q(p)}{tail}")
        elif r["tool"] == "Codex CLI":
            tail = (f" -m {q(model)}" if model else "") + (
                f" -c model_reasoning_effort={effort}" if effort else ""
            )
            cmds.append(f"codex exec{' resume --last' if i else ''}{tail} {q(p)}")
        elif r["tool"] == "OpenCode":
            m = re.match(r"(\S+) \(([^,)]+)", model or "")
            tail = f" -m {q(m.group(2) + '/' + m.group(1))}" if m else ""
            tail += f" --variant {effort}" if effort else ""
            agent = re.match(r"agent (\S+)", settings)
            tail += (
                f" --agent {q(agent.group(1))}"
                if agent and agent.group(1) != "?"
                else ""
            )
            cmds.append(f"opencode run{' -c' if i else ''}{tail} {q(p)}")
    return cmds


def turn_range(spec):
    """--turns: all of them, A, A-B, A- (to the end) or -B (from the first) -> a part for pick()"""
    if spec in (None, "all"):
        return None
    m = re.fullmatch(r"(\d*)-?(\d*)", spec.strip())
    if not m or not (m.group(1) or m.group(2)) or ("-" not in spec and not m.group(1)):
        sys.exit(
            f"receipt: --turns takes a prompt number or a range like 3-5, 3- or -5, not {spec!r}"
        )
    a = int(m.group(1) or 1)
    b = int(m.group(2)) if m.group(2) else (None if "-" in spec else a)
    if a < 1 or (b is not None and b < 1):
        sys.exit("receipt: prompts are numbered from 1")
    return ("turns", a, b)


def nothing_found(tool, everywhere):
    msg = f"receipt: no {TOOLS[tool]} session found " + (
        "in any folder" if everywhere else f"for this folder (looked in {where(tool)})"
    )
    hints = [] if everywhere else elsewhere(tool)
    sys.exit("\n  ".join([msg] + hints))


def emit(a, r, s, payload, table=False):
    if a.png:
        data, ext = picture(s, table), "png"
    elif payload is not None:
        data, ext = payload, "json"
    else:
        data, ext = (f"```\n{s}\n```" if a.md else s), ("md" if a.md else "txt")
    if a.out:
        p = out_path(a, r, ext)
        if isinstance(data, bytes):
            with open(p, "wb") as fh:
                fh.write(data)
        else:
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(data + "\n")
        print(f"receipt: saved to {p}", file=sys.stderr)
    else:
        p = None
        print(data)
    if a.report:
        url = FORM + urllib.parse.quote(s, safe="")
        if len(url) > 8000:
            sys.exit(
                "receipt: this receipt is too long for a form link; leave out --prompt or use --counts"
            )
        print(
            f"\nTo report this run, open the form with your receipt filled in:\n{url}"
        )
    if not a.out and not a.hook:
        print(
            "\nreceipt: check it before you share. To leave things out: --hide cost,date,… · --counts (no names) · "
            "--rename name=label · --last N (just your last N prompts). More: --help",
            file=sys.stderr,
        )
    return p


if __name__ == "__main__":
    main()
