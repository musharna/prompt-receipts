"""Make a receipt for your own AI coding run (Claude Code, Codex, OpenCode, Qwen Code, Gemini CLI or Copilot CLI):
what ran, how long, what it cost, what was switched on.

usage: python3 receipt.py [SESSION] [options]

  no SESSION       the newest Claude Code session for the current folder
  --codex          use Codex sessions instead; --opencode for OpenCode, --qwen for Qwen Code, --gemini for
                   Gemini CLI, --copilot for GitHub Copilot CLI
  --list           list this folder's recent sessions; then --pick N to choose one
  --all            with --list or --pick: sessions from every folder, not just this one
  --last N         only your last N prompts
  --turns          one line per prompt: when, how long, what it cost, tool calls, files
  --turns 3-5      cover only prompts 3 to 5 (also 3, 3- or -5), and list them

  totals over time (this folder's sessions; with --all, every folder's):
  --totals         add up cost, sessions, prompts, time and tokens by day; or --totals week, month, folder, model
  --since DATE     with --totals: only prompts sent on or after DATE (2026-10-01); --until DATE for on or before

  leaving things out (check the receipt before you share it):
  --hide a,b       drop parts: version, date, model, time, cost, items, billing, tokens, work, files, output,
                   addons, hooks, memory, settings
  --counts         numbers instead of names for skills, MCP servers, plugins, subagent types and memory files
  --rename a=b     show name a as b (repeatable); fails if a isn't on the receipt, so a typo can't leak it
  --prompt         also print your prompts (home folders become ~; stops if one holds an email address or a key)
  --model NAME     the model, for a log that doesn't name it (codex exec --json output): said to be your word,
                   and its tokens priced at that model's API prices
  --asked FILE     the prompt a log doesn't hold (claude -p output), from FILE or - for stdin; the receipt
                   says it is the sender's words, and a --record still vouches only for the log
  --reply          also print the model's last reply, checked the same way
  --recipe         also print the commands that rerun your prompts with the same model and effort
  --outcome TEXT   add your own words on how it went ("worked first try")
  --redact         replace email addresses and keys with [email] and [key] instead of stopping
  --prompt-id      add a short fingerprint of the prompt (not the prompt), so --compare can tell runs of one prompt
  --file-names     name the files the run wrote (off by default: only their count and types)

  output:
  --md, --json     wrap it for GitHub or Discord, or print it as JSON (hidden parts stay out)
  --out PATH       save it to a file (.txt, .md, .json or .png) or into a folder
  --png            with --out: draw it as a picture, for posting where text gets mangled: what was asked
                   for, what it made, what it took and the total
  --picture FILE   with --png: put a picture of what the run made on it: a PNG as it is, a sound as its
                   spectrogram, a video as 4 of its frames (WAV and PNG need nothing; others need ffmpeg). With
                   --shot: a screenshot of the page it made, or with no page, its video or sound
  --look LOOK      with --png: strip (the whole receipt, the default), card (cut down to 1080x1350 for a
                   feed: the prompt, the picture, model, time, tool calls and the total) or print (the strip
                   in a real font, drawn by Chrome, Edge or Chromium)
  --theme THEME    with --png: paper (the default), night, terminal, blueprint or pink
  --link           also print a link that shows the receipt on the site; the receipt is inside the link, so
                   nothing is uploaded
  --share          --link, and a link to send it to the gallery (a GitHub issue with the link filled in)
  --report         also print a link to the Prompt Receipts form with this receipt filled in
  --hook           read a Claude Code hook's input from stdin (for a SessionEnd hook; needs --out)
  --statusline     be Claude Code's status line: print a one-line receipt (model, cost, time, plan limits) and
                   keep the plan-limit readings, so later receipts can say how much of your limits a run used
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
  --shot           with --bundle or --png: add a screenshot of the page the run made (needs Chrome, Edge or Chromium)

  showing what the run made:
  --page F.html    save one page with the receipt, every prompt and full reply, the files the run wrote, and
                   each web page it made running in a sandboxed frame; text is checked like --prompt
  --output-url URL with --page: you'll put that page at URL (https://); the receipt carries its sha256, and the
                   receipt site shows the page only if what it fetches matches

Paths, your email and account ids never print, and file contents only go in a --bundle or a --page.
Standard library only.
MIT License, Copyright (c) 2026 Jaret Arnold: https://github.com/musharna/prompt-receipts/blob/main/LICENSE
Prompts and page text: https://musharna.github.io/prompt-receipts/ (CC BY 4.0)."""

import argparse
import array
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
import math
import mimetypes
import os
import pathlib
import re
import shlex
import shutil
import signal
import socketserver
import sqlite3
import stat
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

VERSION = "7.10"
ISSUES = "https://github.com/musharna/prompt-receipts/issues"
SITE = "https://musharna.github.io/prompt-receipts/"
LINK_BUDGET = 2000  # Discord cuts messages at 2,000 characters
FORM = (
    "https://docs.google.com/forms/d/e/1FAIpQLSfo7LHk0Ljj2NES_qAX3-OMIbxbql9fhCsSNSzVLF_bEXoXNA/viewform"
    "?usp=pp_url&entry.349092046=tool&entry.1393206370="
)
TOOLS = {"claude": "Claude Code", "codex": "Codex CLI", "opencode": "OpenCode", "qwen": "Qwen Code", "gemini": "Gemini CLI",
         "copilot": "Copilot CLI"}
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
    "output",
    "addons",
    "hooks",
    "memory",
    "settings",
]

# ---------- prices ----------

# API list prices in dollars per million tokens: input, cache read, cache write (5 min), cache write (1 h), output.
# An optional last item holds multipliers ("fast": fast mode, "us": US-only processing) and "above": [tokens,
# the five prices] for a call whose prompt is bigger than that, or "tiers": a list of those, for prices set by prompt
# size (Alibaba Cloud's). Made from LiteLLM's model_prices_and_context_window.json
# (MIT; the source ccusage, tokscale and codeburn use) by tools/update_prices.py: don't edit by hand.
# --- prices start ---
PRICES_FROM = 'LiteLLM 05166e2, 9 Oct 2026'
PRICES = {'claude-fable-5': [10, 1, 12.5, 20, 50, {'us': 1.1}],
 'claude-fable-5-1': [10, 0.25, 12.5, 20, 50, {'us': 1.1}],
 'claude-haiku-4-5': [1, 0.1, 1.25, 2, 5],
 'claude-haiku-4-5-20251001': [1, 0.1, 1.25, 2, 5],
 'claude-haiku-5-5': [0.1, 0.01, 0.125, 0.2, 0.5, {'above': [100000, 0.5, 0.05, 0.625, 1, 2.5], 'us': 1.1}],
 'claude-mythos-5': [10, 1, 12.5, 20, 50, {'us': 1.1}],
 'claude-mythos-5-1': [10, 0.25, 12.5, 20, 50, {'us': 1.1}],
 'claude-mythos-preview': [10, 1, 12.5, 20, 50, {'us': 1.1}],
 'claude-opus-4-5': [5, 0.5, 6.25, 10, 25],
 'claude-opus-4-5-20251101': [5, 0.5, 6.25, 10, 25],
 'claude-opus-4-6': [5, 0.5, 6.25, 10, 25, {'us': 1.1}],
 'claude-opus-4-6-20260205': [5, 0.5, 6.25, 10, 25, {'us': 1.1}],
 'claude-opus-4-7': [5, 0.5, 6.25, 10, 25, {'us': 1.1}],
 'claude-opus-4-7-20260416': [5, 0.5, 6.25, 10, 25, {'us': 1.1}],
 'claude-opus-4-8': [5, 0.5, 6.25, 10, 25, {'fast': 2.0, 'us': 1.1}],
 'claude-opus-5': [5, 0.5, 6.25, 10, 25, {'fast': 2.0, 'us': 1.1}],
 'claude-opus-5-5': [4, 0.2, 5, 8, 20, {'fast': 2, 'us': 1.1}],
 'claude-sonnet-4-5': [3, 0.3, 3.75, 6, 15, {'above': [200000, 6, 0.6, 7.5, 12, 22.5]}],
 'claude-sonnet-4-5-20250929': [3, 0.3, 3.75, 6, 15, {'above': [200000, 6, 0.6, 7.5, 12, 22.5]}],
 'claude-sonnet-4-6': [3, 0.3, 3.75, 6, 15, {'us': 1.1}],
 'claude-sonnet-5': [2, 0.2, 2.5, 4, 10, {'us': 1.1}],
 'claude-sonnet-5-5': [2, 0.1, 2.5, 4, 10, {'us': 1.1}],
 'gemini-2.0-flash-exp-image-generation': [0, 0, 0, 0, 0],
 'gemini-2.5-computer-use-preview-10-2025': [1.25,
                                             1.25,
                                             1.25,
                                             1.25,
                                             10,
                                             {'above': [200000, 2.5, 2.5, 2.5, 2.5, 15]}],
 'gemini-2.5-flash': [0.3, 0.03, 0.3, 0.3, 2.5],
 'gemini-2.5-flash-image': [0.3, 0.03, 0.3, 0.3, 2.5],
 'gemini-2.5-flash-lite': [0.1, 0.01, 0.1, 0.1, 0.4],
 'gemini-2.5-flash-native-audio-latest': [0.5, 0.5, 0.5, 0.5, 2],
 'gemini-2.5-flash-native-audio-preview-09-2025': [0.5, 0.5, 0.5, 0.5, 2],
 'gemini-2.5-flash-native-audio-preview-12-2025': [0.5, 0.5, 0.5, 0.5, 2],
 'gemini-2.5-flash-preview-tts': [0.5, 0.5, 0.5, 0.5, 10],
 'gemini-2.5-pro': [1.25, 0.125, 1.25, 1.25, 10, {'above': [200000, 2.5, 0.25, 2.5, 2.5, 15]}],
 'gemini-2.5-pro-preview-tts': [1, 0.125, 1, 1, 20],
 'gemini-3-flash-preview': [0.5, 0.05, 0.5, 0.5, 3],
 'gemini-3-pro-image': [2, 2, 2, 2, 12],
 'gemini-3-pro-image-preview': [2, 2, 2, 2, 12],
 'gemini-3.1-flash-image': [0.5, 0.5, 0.5, 0.5, 3],
 'gemini-3.1-flash-image-preview': [0.5, 0.5, 0.5, 0.5, 3],
 'gemini-3.1-flash-lite': [0.25, 0.025, 0.25, 0.25, 1.5],
 'gemini-3.1-flash-lite-image': [0.25, 0.25, 0.25, 0.25, 1.5],
 'gemini-3.1-flash-lite-preview': [0.25, 0.025, 0.25, 0.25, 1.5],
 'gemini-3.1-flash-live-preview': [0.75, 0.75, 0.75, 0.75, 4.5],
 'gemini-3.1-flash-tts-preview': [1, 1, 1, 1, 20],
 'gemini-3.1-pro-preview': [2, 0.2, 2, 2, 12, {'above': [200000, 4, 0.4, 4, 4, 18]}],
 'gemini-3.1-pro-preview-customtools': [2, 0.2, 2, 2, 12, {'above': [200000, 4, 0.4, 4, 4, 18]}],
 'gemini-3.5-flash': [1.5, 0.15, 1.5, 1.5, 9],
 'gemini-3.5-flash-lite': [0.3, 0.03, 0.3, 0.3, 2.5],
 'gemini-3.5-live-translate-preview': [3.5, 3.5, 3.5, 3.5, 21],
 'gemini-3.5-transcribe': [2, 2, 2, 2, 12],
 'gemini-3.5-transcribe-live': [3.5, 3.5, 3.5, 3.5, 21],
 'gemini-3.6-flash': [0.75, 0.075, 0.75, 0.75, 3.75],
 'gemini-3.7-flash': [0.75, 0.075, 0.75, 0.75, 3.75],
 'gemini-3.8-flash': [0.75, 0.075, 0.75, 0.75, 3.75],
 'gemini-3.8-flash-lite-tts': [0.5, 0.125, 0.5, 0.5, 6],
 'gemini-3.8-flash-tts': [0.5, 0.125, 0.5, 0.5, 9],
 'gemini-3.8-live': [0.75, 0.75, 0.75, 0.75, 4.5],
 'gemini-3.8-live-extended-thinking': [0.75, 0.75, 0.75, 0.75, 4.5],
 'gemini-embedding-001': [0.15, 0.15, 0.15, 0.15, 0],
 'gemini-embedding-2': [0.2, 0.2, 0.2, 0.2, 0],
 'gemini-embedding-2-preview': [0.2, 0.2, 0.2, 0.2, 0],
 'gemini-exp-1114': [0, 0, 0, 0, 0, {'above': [128000, 0, 0, 0, 0, 0]}],
 'gemini-exp-1206': [0, 0, 0, 0, 0, {'above': [128000, 0, 0, 0, 0, 0]}],
 'gemini-flash-latest': [0.75, 0.075, 0.75, 0.75, 3.75],
 'gemini-flash-lite-latest': [0.3, 0.03, 0.3, 0.3, 2.5],
 'gemini-gemma-2-27b-it': [0.35, 0.35, 0.35, 0.35, 1.05],
 'gemini-gemma-2-9b-it': [0.35, 0.35, 0.35, 0.35, 1.05],
 'gemini-live-2.5-flash-preview-native-audio-09-2025': [0.5, 0.5, 0.5, 0.5, 2],
 'gemini-nano-banana-2.1': [1.5, 1.5, 1.5, 1.5, 7.5],
 'gemini-omni-1.1-flash': [1.5, 1.5, 1.5, 1.5, 9],
 'gemini-omni-flash-preview': [1.5, 1.5, 1.5, 1.5, 9],
 'gemini-pro-latest': [2, 0.2, 2, 2, 12, {'above': [200000, 4, 0.4, 4, 4, 18]}],
 'gemini-robotics-er-2-preview': [1, 0.1, 1, 1, 5],
 'gemini-robotics-er-2-streaming-preview': [1, 1, 1, 1, 5],
 'gpt-5': [1.25, 0.125, 1.25, 1.25, 10],
 'gpt-5-2025-08-07': [1.25, 0.125, 1.25, 1.25, 10],
 'gpt-5-chat': [1.25, 0.125, 1.25, 1.25, 10],
 'gpt-5-chat-latest': [1.25, 0.125, 1.25, 1.25, 10],
 'gpt-5-codex': [1.25, 0.125, 1.25, 1.25, 10],
 'gpt-5-mini': [0.25, 0.025, 0.25, 0.25, 2],
 'gpt-5-mini-2025-08-07': [0.25, 0.025, 0.25, 0.25, 2],
 'gpt-5-nano': [0.05, 0.005, 0.05, 0.05, 0.4],
 'gpt-5-nano-2025-08-07': [0.05, 0.005, 0.05, 0.05, 0.4],
 'gpt-5-pro': [15, 15, 15, 15, 120],
 'gpt-5-pro-2025-10-06': [15, 15, 15, 15, 120],
 'gpt-5-search-api': [1.25, 0.125, 1.25, 1.25, 10],
 'gpt-5-search-api-2025-10-14': [1.25, 0.125, 1.25, 1.25, 10],
 'gpt-5.1': [1.25, 0.125, 1.25, 1.25, 10],
 'gpt-5.1-2025-11-13': [1.25, 0.125, 1.25, 1.25, 10],
 'gpt-5.1-chat-latest': [1.25, 0.125, 1.25, 1.25, 10],
 'gpt-5.1-codex': [1.25, 0.125, 1.25, 1.25, 10],
 'gpt-5.1-codex-max': [1.25, 0.125, 1.25, 1.25, 10],
 'gpt-5.1-codex-mini': [0.25, 0.025, 0.25, 0.25, 2],
 'gpt-5.2': [1.75, 0.175, 1.75, 1.75, 14],
 'gpt-5.2-2025-12-11': [1.75, 0.175, 1.75, 1.75, 14],
 'gpt-5.2-chat-latest': [1.75, 0.175, 1.75, 1.75, 14],
 'gpt-5.2-codex': [1.75, 0.175, 1.75, 1.75, 14],
 'gpt-5.2-pro': [21, 21, 21, 21, 168],
 'gpt-5.2-pro-2025-12-11': [21, 21, 21, 21, 168],
 'gpt-5.3-chat-latest': [1.75, 0.175, 1.75, 1.75, 14],
 'gpt-5.3-codex': [1.75, 0.175, 1.75, 1.75, 14],
 'gpt-5.4': [2.5, 0.25, 2.5, 2.5, 15, {'above': [272000, 5, 0.5, 5, 5, 22.5]}],
 'gpt-5.4-2026-03-05': [2.5, 0.25, 2.5, 2.5, 15, {'above': [272000, 5, 0.5, 5, 5, 22.5]}],
 'gpt-5.4-mini': [0.75, 0.075, 0.75, 0.75, 4.5],
 'gpt-5.4-mini-2026-03-17': [0.75, 0.075, 0.75, 0.75, 4.5],
 'gpt-5.4-nano': [0.2, 0.02, 0.2, 0.2, 1.25],
 'gpt-5.4-nano-2026-03-17': [0.2, 0.02, 0.2, 0.2, 1.25],
 'gpt-5.4-pro': [30, 30, 30, 30, 180, {'above': [272000, 60, 60, 60, 60, 270]}],
 'gpt-5.4-pro-2026-03-05': [30, 30, 30, 30, 180, {'above': [272000, 60, 60, 60, 60, 270]}],
 'gpt-5.5': [5, 0.5, 5, 5, 30, {'above': [272000, 10, 1, 10, 10, 45]}],
 'gpt-5.5-2026-04-23': [5, 0.5, 5, 5, 30, {'above': [272000, 10, 1, 10, 10, 45]}],
 'gpt-5.5-cyber': [12.5, 1.25, 12.5, 12.5, 75],
 'gpt-5.5-pro': [30, 30, 30, 30, 180, {'above': [272000, 60, 60, 60, 60, 270]}],
 'gpt-5.5-pro-2026-04-23': [30, 30, 30, 30, 180, {'above': [272000, 60, 60, 60, 60, 270]}],
 'gpt-5.6': [4, 0.4, 5, 5, 20, {'above': [272000, 8, 0.8, 10, 10, 30]}],
 'gpt-5.6-cyber': [12.5, 1.25, 15.625, 15.625, 75, {'above': [272000, 25, 2.5, 31.25, 31.25, 112.5]}],
 'gpt-5.6-luna': [0.2, 0.02, 0.25, 0.25, 1.2, {'above': [272000, 0.4, 0.04, 0.5, 0.5, 1.8]}],
 'gpt-5.6-sol': [4, 0.4, 5, 5, 20, {'above': [272000, 8, 0.8, 10, 10, 30]}],
 'gpt-5.6-terra': [2, 0.2, 2.5, 2.5, 12, {'above': [272000, 4, 0.4, 5, 5, 18]}],
 'gpt-6-astra': [10, 1, 12.5, 12.5, 50, {'above': [272000, 20, 2, 25, 25, 75]}],
 'gpt-6-luna': [0.1, 0.01, 0.125, 0.125, 0.5, {'above': [272000, 0.2, 0.02, 0.25, 0.25, 0.75]}],
 'gpt-6-sol': [2, 0.2, 2.5, 2.5, 10, {'above': [272000, 4, 0.4, 5, 5, 15]}],
 'gpt-6.1-sol': [2, 0.1, 2.5, 2.5, 10, {'above': [272000, 4, 0.2, 5, 5, 15]}],
 'o3': [2, 0.5, 2, 2, 8],
 'o3-2025-04-16': [2, 0.5, 2, 2, 8],
 'o3-deep-research': [10, 2.5, 10, 10, 40],
 'o3-mini': [1.1, 0.55, 1.1, 1.1, 4.4],
 'o3-mini-2025-01-31': [1.1, 0.55, 1.1, 1.1, 4.4],
 'o3-pro': [20, 20, 20, 20, 80],
 'o3-pro-2025-06-10': [20, 20, 20, 20, 80],
 'o4-mini': [1.1, 0.275, 1.1, 1.1, 4.4],
 'o4-mini-2025-04-16': [1.1, 0.275, 1.1, 1.1, 4.4],
 'o4-mini-deep-research': [2, 0.5, 2, 2, 8],
 'qwen-coder': [0.3, 0.3, 0.3, 0.3, 1.5],
 'qwen-flash': [0.05, 0.05, 0.05, 0.05, 0.4, {'tiers': [[256000, 0.25, 0.25, 0.25, 0.25, 2]]}],
 'qwen-flash-2025-07-28': [0.05, 0.05, 0.05, 0.05, 0.4, {'tiers': [[256000, 0.25, 0.25, 0.25, 0.25, 2]]}],
 'qwen-max': [1.6, 1.6, 1.6, 1.6, 6.4],
 'qwen-plus': [0.4, 0.4, 0.4, 0.4, 1.2],
 'qwen-plus-2025-01-25': [0.4, 0.4, 0.4, 0.4, 1.2],
 'qwen-plus-2025-04-28': [0.4, 0.4, 0.4, 0.4, 1.2],
 'qwen-plus-2025-07-14': [0.4, 0.4, 0.4, 0.4, 1.2],
 'qwen-plus-2025-07-28': [0.4, 0.4, 0.4, 0.4, 1.2, {'tiers': [[256000, 1.2, 1.2, 1.2, 1.2, 3.6]]}],
 'qwen-plus-2025-09-11': [0.4, 0.4, 0.4, 0.4, 1.2, {'tiers': [[256000, 1.2, 1.2, 1.2, 1.2, 3.6]]}],
 'qwen-plus-latest': [0.4, 0.4, 0.4, 0.4, 1.2, {'tiers': [[256000, 1.2, 1.2, 1.2, 1.2, 3.6]]}],
 'qwen-turbo': [0.05, 0.05, 0.05, 0.05, 0.2],
 'qwen-turbo-2024-11-01': [0.05, 0.05, 0.05, 0.05, 0.2],
 'qwen-turbo-2025-04-28': [0.05, 0.05, 0.05, 0.05, 0.2],
 'qwen-turbo-latest': [0.05, 0.05, 0.05, 0.05, 0.2],
 'qwen3-coder-flash': [0.3,
                       0.08,
                       0.3,
                       0.3,
                       1.5,
                       {'tiers': [[32000, 0.5, 0.12, 0.5, 0.5, 2.5],
                                  [128000, 0.8, 0.2, 0.8, 0.8, 4],
                                  [256000, 1.6, 0.4, 1.6, 1.6, 9.6]]}],
 'qwen3-coder-flash-2025-07-28': [0.3,
                                  0.3,
                                  0.3,
                                  0.3,
                                  1.5,
                                  {'tiers': [[32000, 0.5, 0.5, 0.5, 0.5, 2.5],
                                             [128000, 0.8, 0.8, 0.8, 0.8, 4],
                                             [256000, 1.6, 1.6, 1.6, 1.6, 9.6]]}],
 'qwen3-coder-plus': [1,
                      0.1,
                      1,
                      1,
                      5,
                      {'tiers': [[32000, 1.8, 0.18, 1.8, 1.8, 9],
                                 [128000, 3, 0.3, 3, 3, 15],
                                 [256000, 6, 0.6, 6, 6, 60]]}],
 'qwen3-coder-plus-2025-07-22': [1,
                                 1,
                                 1,
                                 1,
                                 5,
                                 {'tiers': [[32000, 1.8, 1.8, 1.8, 1.8, 9],
                                            [128000, 3, 3, 3, 3, 15],
                                            [256000, 6, 6, 6, 6, 60]]}],
 'qwen3-max': [1.2, 1.2, 1.2, 1.2, 6, {'tiers': [[32000, 2.4, 2.4, 2.4, 2.4, 12], [128000, 3, 3, 3, 3, 15]]}],
 'qwen3-max-2026-01-23': [1.2,
                          1.2,
                          1.2,
                          1.2,
                          6,
                          {'tiers': [[32000, 2.4, 2.4, 2.4, 2.4, 12], [128000, 3, 3, 3, 3, 15]]}],
 'qwen3-max-preview': [1.2,
                       1.2,
                       1.2,
                       1.2,
                       6,
                       {'tiers': [[32000, 2.4, 2.4, 2.4, 2.4, 12], [128000, 3, 3, 3, 3, 15]]}],
 'qwen3-next-80b-a3b-instruct': [0.15, 0.15, 0.15, 0.15, 1.2],
 'qwen3-next-80b-a3b-thinking': [0.15, 0.15, 0.15, 0.15, 1.2],
 'qwen3-vl-235b-a22b-instruct': [0.4, 0.4, 0.4, 0.4, 1.6],
 'qwen3-vl-235b-a22b-thinking': [0.4, 0.4, 0.4, 0.4, 4],
 'qwen3-vl-32b-instruct': [0.16, 0.16, 0.16, 0.16, 0.64],
 'qwen3-vl-32b-thinking': [0.16, 0.16, 0.16, 0.16, 2.87],
 'qwen3-vl-plus': [0.2,
                   0.2,
                   0.2,
                   0.2,
                   1.6,
                   {'tiers': [[32000, 0.3, 0.3, 0.3, 0.3, 2.4], [128000, 0.6, 0.6, 0.6, 0.6, 4.8]]}],
 'qwen3.5-plus': [0.4, 0.4, 0.4, 0.4, 2.4, {'tiers': [[256000, 0.5, 0.5, 0.5, 0.5, 3]]}],
 'qwen3.7-max': [2.5, 0.5, 2.5, 2.5, 7.5],
 'qwen3.7-plus': [0.4, 0.08, 0.4, 0.4, 1.6, {'tiers': [[256000, 1.2, 0.24, 1.2, 1.2, 4.8]]}],
 'qwen3.8-flash': [0.15, 0.016, 0.2, 0.2, 0.47],
 'qwen3.8-max': [2, 0.25, 2, 2, 6],
 'qwen3.8-omni-flash': [0.15, 0.016, 0.15, 0.15, 0.47]}
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
        prov = v.get("litellm_provider") if isinstance(v, dict) else None
        if prov in ("anthropic", "openai") and re.match(r"(claude-|gpt-[56]|o[34]|codex-)", name):
            model = name
        elif (prov, name.split("/")[0]) in (("gemini", "gemini"), ("dashscope", "dashscope")) and re.match(
            r"[a-z]+/(gemini-|qwen)", name
        ):  # Gemini CLI's models at Google's prices; Qwen Code's at Alibaba Cloud's
            model = name.split("/", 1)[1]
        else:
            continue
        tiers = sorted(  # Alibaba Cloud prices by prompt size: one row per range of prompt tokens
            (t for t in v.get("tiered_pricing") or [] if isinstance(t, dict) and t.get("range")),
            key=lambda t: t["range"][0],
        )
        row = five(v, "") or (five(tiers[0], "") if tiers else None)
        if not row:
            continue
        extra = {
            k: x
            for k, x in (v.get("provider_specific_entry") or {}).items()
            if k in ("fast", "us") and isinstance(x, (int, float))
        }
        if tiers and not five(v, "") and all(five(t, "") for t in tiers):
            extra["tiers"] = [[int(t["range"][0])] + five(t, "") for t in tiers[1:]]
        for key in v:
            m = re.fullmatch(r"input_cost_per_token(_above_(\d+)k_tokens)", key)
            if m and five(v, m.group(1)):
                extra["above"] = [int(m.group(2)) * 1000] + five(v, m.group(1))
        table[model] = row + ([extra] if extra else [])
    return table


def rates_for(model):
    """-> a PRICES row for a model as a log names it (claude-opus-5-5[1m], anthropic/claude-…, …-20251001), else None"""
    name = re.sub(r"\[.*\]$", "", model or "").split("/")[-1].lower()
    name = re.sub(r"-1m(-internal)?$", "", name)  # Copilot CLI's name for the long-context version
    for n in (
        name,
        re.sub(r"(?<=\d)\.(?=\d)", "-", name),  # Copilot CLI's claude-opus-4.7 is claude-opus-4-7
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

    def add(self, model, n, fast=False, us=False, searches=0, summed=False):
        """n: tokens of each kind, in CLASSES' order; summed: n adds up several calls, so no one prompt's size is known"""
        model = re.sub(r"\[.*\]$", "", model or "?")
        row = rates_for(model)
        if row is None:
            if sum(n):
                self.unpriced[model] += sum(n)
            return
        extra = row[5] if len(row) > 5 else {}
        rates, mult = row[:5], 1
        if extra.get("above") and sum(n[:4]) > extra["above"][0] and not summed:
            rates = extra["above"][1:]
        for tier in extra.get("tiers", []) if not summed else []:  # the last range the prompt is past sets the price
            if sum(n[:4]) > tier[0]:
                rates = tier[1:]
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


def claude_lines(path):
    """a Claude Code session log one entry at a time, or the output of `claude -p --output-format stream-json
    --verbose` read as one: the same replies and tool results, without the prompt, effort, hooks or memory files"""
    it = lines(path)
    first, ui = next(it, None), []
    # a first launch (an empty home) writes UI events, with no timestamp, before claude -p's init line; a session
    # log's entries always carry one, so these never hide a session log's own lines
    while first and first.get("type") == "system" and first.get("subtype") != "init" and "timestamp" not in first:
        ui.append(first)
        first = next(it, None)
    if first is None:
        yield from ui
        return
    if not (first.get("type") == "system" and first.get("subtype") == "init" and "claude_code_version" in first):
        yield from ui
        yield first
        yield from it
        return
    # claude -p stamps no prompt, so the run starts at its last event less the duration its result gives.
    # Each message's usage is the one it started with (an output count of a few tokens): only the result has
    # the output the run made, so what the messages don't show is added at the end, per model
    last, took, said, made = "", None, {}, {}
    for d in lines(path):
        last = max(last, d.get("timestamp") or "")
        if d.get("type") == "result":
            took = d.get("duration_ms") or took
            made = {re.sub(r"\[.*\]$", "", k): v.get("outputTokens") or 0 for k, v in (d.get("modelUsage") or {}).items()}
        m = d.get("message") or {}
        if d.get("type") == "assistant" and m.get("usage") and m.get("model"):
            said[m.get("id")] = (m["model"], m["usage"].get("output_tokens") or 0)
    start = iso(when(last).timestamp() * 1000 - took) if last and took else None
    yield {"type": "stream-init", "cwd": first.get("cwd")}
    yield {"type": "attachment", "attachment": {"type": "skill_listing", "skillCount": len(first.get("skills") or []),
           "names": first.get("skills") or []}}  # fmt: skip
    servers = [x.get("name") for x in first.get("mcp_servers") or [] if isinstance(x, dict) and x.get("name")]
    if servers:
        yield {"type": "attachment", "attachment": {"type": "mcp_instructions_delta", "addedNames": servers}}
    base = {"version": first.get("claude_code_version"), "cwd": first.get("cwd"), "sessionId": first.get("session_id"),
            "permissionMode": first.get("permissionMode")}  # fmt: skip
    prompted = False
    for d in it:
        t = d.get("type")
        if t in ("user", "assistant"):
            e = dict(d, **base)
            if d.get("parent_tool_use_id"):  # a subagent's message, inline here, in a file of its own in a session log
                e["isSidechain"] = True
            if d.get("isSynthetic"):  # Claude Code's own words (a note after a picture it read), not a prompt
                e["isMeta"] = True
            if d.get("thinking_duration_ms"):
                e["thinkingDurationMs"] = d["thinking_duration_ms"]
            if d.get("tool_use_result") is not None:
                e["toolUseResult"] = d["tool_use_result"]
            if t == "user" and claude_prompt(e) is not None:
                prompted = True  # sent with --input-format stream-json and --replay-user-messages, it is here
            elif t == "assistant" and not prompted and not e.get("isSidechain"):
                prompted = True
                yield dict(base, type="user", timestamp=start or e.get("timestamp"), promptNotSaved=True,
                           message={"role": "user", "content": ""})  # fmt: skip
            yield e
        elif t == "result":  # its totals are the run's so far, like a session log's cost-state
            for model, n in sorted(made.items()):
                more = n - sum(x for mm, x in said.values() if mm == model)
                if more > 0:
                    yield dict(base, type="assistant", timestamp=last, message={"id": f"output:{model}", "model": model,
                               "usage": {"output_tokens": more}})  # fmt: skip
            made = {}
            yield {"type": "cost-state", "startTime": first.get("session_id"), "totalCostUSD": d.get("total_cost_usd"),
                   "modelUsage": d.get("modelUsage") or {}, "totalAPIDuration": d.get("duration_api_ms")}  # fmt: skip


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


def files_part(r, paths, deleted=0, texts=None):
    """paths: the files the run wrote; texts: {path: the whole text a write put there, or None after an edit}"""
    names_ = [base_name(p) for p in paths]
    r["files_written"] = len(paths)
    r["files_deleted"] = deleted
    r["file_types"] = dict(
        collections.Counter(os.path.splitext(n)[1].lower() or "no type" for n in names_)
    )
    r["file_names"] = sorted(set(names_))
    if texts and r.get("ended"):  # a file the run changed again after writing it is measured as the run left it
        texts = {p: None if t is not None and changed_by_run(p, t, r["ended"]) else t for p, t in texts.items()}
    r.update(output_shape(paths, texts or {}))
    r["_written"] = (list(paths), texts or {})  # for --page and --bundle only


def changed_by_run(path, written, ended):
    """a file the log says was written whole that differs on disk, last changed before the run ended: the run
    changed it again (with a shell command, say), so the copy on disk is what it made"""
    try:
        if os.path.getmtime(path) > when(ended).timestamp() + 2:
            return False
        with open(path, "rb") as fh:
            return fh.read() != written.encode("utf-8", "surrogatepass")
    except OSError:
        return False


PAGE_TYPES = (".html", ".htm")
SHAPE_MAX = 50 * 2**20  # a file this big is measured by its size alone


def file_body(path, text):
    """-> the file's bytes as the run left it: the text the log holds, else the file as it is now; None if gone"""
    if text is not None:
        return text.encode("utf-8", "surrogatepass")
    try:
        if os.path.getsize(path) > SHAPE_MAX:
            return b"\0" * os.path.getsize(path)  # counted as bytes, not lines
        with open(path, "rb") as f:
            return f.read()
    except OSError:
        return None


def is_text(body):
    return b"\0" not in body[:8192]


def output_shape(paths, texts):
    """-> how much the run wrote: lines (text files), bytes, whether one is a web page, how many are gone"""
    n_lines, size, gone = 0, 0, 0
    for p in paths:
        body = file_body(p, texts.get(p))
        if body is None:
            gone += 1
            continue
        size += len(body)
        if is_text(body):
            n_lines += body.count(b"\n") + (1 if body and not body.endswith(b"\n") else 0)
    out = {"output_lines": n_lines, "output_bytes": size,
           "web_page": any(base_name(p).lower().endswith(PAGE_TYPES) for p in paths)}  # fmt: skip
    if gone:
        out["files_gone"] = gone
    return out


def size_text(n):
    if n < 1024:
        return many(n, "byte")
    if n < 2**20:
        return f"{max(round(n / 1024), 1):,} KB"
    return f"{n / 2**20:,.1f} MB"


AUDIO_TYPES = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".oga": "audio/ogg", ".opus": "audio/ogg",
               ".flac": "audio/flac", ".m4a": "audio/mp4", ".aac": "audio/aac"}  # fmt: skip
VIDEO_TYPES = {".mp4": "video/mp4", ".m4v": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"}
SKIP_DIRS = {"node_modules", "__pycache__", "venv", "env", "site-packages"}  # and every folder whose name starts with .
MADE_SCAN_MAX = 20000  # files looked at, at most, for the ones made while the run went
MADE_HOW = "changed in the run's folder while it ran"


def made_while(folder, started, ended, written):
    """-> (the files in folder last changed while the run went that its own tools didn't write, whether the look
    stopped early). Programs it ran made these (a script's sound, ffmpeg's video); anything else changing files
    there at the time would count too, which is why the receipt lists them apart"""
    lo, hi = when(started).timestamp() - 1, when(ended).timestamp() + 2
    found, seen = [], 0
    for top, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS)
        for f in sorted(files):
            if f.startswith("."):
                continue
            seen += 1
            if seen > MADE_SCAN_MAX:
                return found, True
            path = os.path.join(top, f)
            try:
                st = os.lstat(path)  # a link isn't followed
            except OSError:
                continue
            if stat.S_ISREG(st.st_mode) and lo <= st.st_mtime <= hi and os.path.realpath(path) not in written:
                found.append(path)
    return found, False


def length_text(secs):
    if secs < 10:
        return f"{secs:.2g} s"
    secs = int(secs)
    if secs < 3600:
        return f"{secs // 60}:{secs % 60:02d}"
    return f"{secs // 3600}:{secs % 3600 // 60:02d}:{secs % 60:02d}"


def wav_secs(path):
    """-> a WAV's length in seconds from its header alone, or None"""
    try:
        with open(path, "rb") as fh:
            head = fh.read(12)
            if head[:4] != b"RIFF" or head[8:12] != b"WAVE":
                return None
            rate = align = None
            while True:
                h = fh.read(8)
                if len(h) < 8:
                    return None
                tag, n = struct.unpack("<4sI", h)
                if tag == b"fmt ":
                    _, _, rate, _, align, _ = struct.unpack("<HHIIHH", fh.read(n + (n & 1))[:16])
                elif tag == b"data" and rate and align:
                    return min(n, os.path.getsize(path) - fh.tell()) // align / rate
                else:
                    fh.seek(n + (n & 1), 1)
    except (OSError, struct.error):
        return None


def mp4_info(path):
    """-> (seconds, width, height) from an MP4, MOV or M4A's header boxes (0, 0 when there's no picture), or None"""

    def boxes(b):
        i = 0
        while i + 8 <= len(b):
            n, tag = struct.unpack(">I4s", b[i : i + 8])
            if n < 8:
                return
            yield tag, b[i + 8 : i + n]
            i += n

    try:
        size, pos, moov = os.path.getsize(path), 0, None
        with open(path, "rb") as fh:
            while pos + 8 <= size:
                fh.seek(pos)
                n, tag = struct.unpack(">I4s", fh.read(8))
                head = 8
                if n == 1:
                    n, head = struct.unpack(">Q", fh.read(8))[0], 16
                elif n == 0:
                    n = size - pos
                if n < head:
                    return None
                if tag == b"moov":
                    moov = fh.read(min(n - head, 64 * 2**20))
                    break
                pos += n
        if moov is None:
            return None
        secs, w, h = None, 0, 0
        for tag, body in boxes(moov):
            if tag == b"mvhd" and body:
                scale, dur = struct.unpack(">IQ", body[20:32]) if body[0] == 1 else struct.unpack(">II", body[12:20])
                secs = dur / scale if scale else None
            elif tag == b"trak":
                for t2, b2 in boxes(body):
                    if t2 == b"tkhd" and len(b2) >= 84 and not w:
                        tw, th = struct.unpack(">II", b2[-8:])
                        w, h = tw >> 16, th >> 16
        return secs, w, h
    except (OSError, struct.error, IndexError):
        return None


def media_facts(paths):
    """-> how many sounds and videos are among paths, and how long they are, from their headers (no decoding)"""
    videos, sounds = [], []
    for path in paths:
        ext = os.path.splitext(path)[1].lower()
        if ext in VIDEO_TYPES:
            videos.append((mp4_info(path) if ext != ".webm" else None) or (None, 0, 0))
        elif ext in AUDIO_TYPES:
            sounds.append(wav_secs(path) if ext == ".wav" else (mp4_info(path) or (None,))[0] if ext == ".m4a" else None)
    out = {}
    if videos:
        out["videos"] = len(videos)
        if all(v[0] is not None for v in videos):
            out["video_seconds"] = round(sum(v[0] for v in videos), 1)
        if len(videos) == 1 and videos[0][1]:
            out["video_size"] = f"{videos[0][1]}×{videos[0][2]}"
    if sounds:
        out["sounds"] = len(sounds)
        if all(x is not None for x in sounds):
            out["sound_seconds"] = round(sum(sounds), 1)
    return out


def media_text(m):
    out = []
    for kind in ("video", "sound"):
        n = m.get(kind + "s")
        if not n:
            continue
        t = f"a {kind}" if n == 1 else f"{n} {kind}s"
        if m.get(kind + "_seconds") is not None:
            t += f", {length_text(m[kind + '_seconds'])}" + (" in all" if n > 1 else "")
        if kind == "video" and m.get("video_size"):
            t += f", {m['video_size']}"
        out.append(t)
    return " · ".join(out)


def made_part(r, folder):
    """the files programs the run ran made: changed in its folder while it ran, besides the ones its own tools wrote"""
    if not folder or not os.path.isdir(folder) or not r.get("started") or not r.get("ended"):
        return
    if os.path.realpath(folder) in {os.path.realpath(home()), os.path.realpath(os.path.abspath(os.sep))}:
        print("receipt: didn't look for files programs the run ran made: its folder is your home folder, where "
              "too much else changes", file=sys.stderr)  # fmt: skip
        return
    written = {os.path.realpath(x if os.path.isabs(x) else os.path.join(folder, x))
               for x in r.get("_written", ([], {}))[0]}  # fmt: skip
    paths, stopped = made_while(folder, r["started"], r["ended"], written)
    r["_made"] = paths
    if not paths and not stopped:
        return
    names_ = [base_name(x) for x in paths]
    r["files_made"] = len(paths)
    r["made_types"] = dict(collections.Counter(os.path.splitext(n)[1].lower() or "no type" for n in names_))
    rank = lambda n: (0 if n.lower().endswith(tuple(VIDEO_TYPES)) else 1 if n.lower().endswith(tuple(AUDIO_TYPES))
                      else 2 if n.lower().endswith(tuple(IMAGE_TYPES)) else 3, n)  # fmt: skip
    r["made_names"] = sorted(set(names_), key=rank)  # videos and sounds first: what the run was asked for, mostly
    size = 0
    for x in paths:
        try:
            size += os.path.getsize(x)
        except OSError:
            pass
    r["made_bytes"] = size
    media = media_facts(paths)
    if media:
        r["made_media"] = media
    if stopped:
        r["made_note"] = f"stopped looking after {MADE_SCAN_MAX:,} files"


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
    if tool == "qwen":
        fs = glob.glob(os.path.join(qwen_dir(), "projects", "*", "chats", "*.jsonl"))
        fs.sort(key=os.path.getmtime, reverse=True)
        return fs if everywhere else [f for f in fs if same_folder(qwen_cwd(f))]
    if tool == "gemini":
        fs = glob.glob(os.path.join(gemini_dir(), "tmp", "*", "chats", "session-*.json*"))
        fs.sort(key=os.path.getmtime, reverse=True)
        return fs if everywhere else [f for f in fs if gemini_here(f)]
    if tool == "copilot":
        fs = glob.glob(os.path.join(copilot_dir(), "session-state", "*", "events.jsonl"))
        fs.sort(key=os.path.getmtime, reverse=True)
        return fs if everywhere else [f for f in fs if same_folder(copilot_cwd(f))]
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
        "qwen": tilde(os.path.join(qwen_dir(), "projects")) + " (matched on folder)",
        "gemini": tilde(os.path.join(gemini_dir(), "tmp")) + " (matched on folder)",
        "copilot": tilde(os.path.join(copilot_dir(), "session-state")) + " (matched on folder)",
    }[tool]


def folder_of(tool, key):
    if tool == "opencode":
        return next((d for i, d, _ in oc_rows() if i == key), "")
    return {"codex": codex_cwd, "qwen": qwen_cwd, "gemini": gemini_cwd, "copilot": copilot_cwd}.get(tool, claude_cwd)(key)


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
    for d in gemini_messages(key) if tool == "gemini" else claude_lines(key) if tool == "claude" else lines(key):
        t = {"codex": codex_prompt, "qwen": qwen_prompt, "gemini": gemini_prompt, "copilot": copilot_prompt}.get(
            tool, claude_prompt
        )(d)
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
    elif tool != "opencode":
        cwds = [folder_of(tool, f) for f in sessions(tool, True)]
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
            flags = [f"--{t}" for t in TOOLS if t != "claude"]
            how = (
                f"leave out {', '.join(flags[:-1])} and {flags[-1]}"
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
    """-> your prompt text if this entry is one, else None ("" for a prompt the log counts but doesn't hold)"""
    if d.get("promptNotSaved"):
        return ""
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
        [d.get("timestamp") or "" for d in claude_lines(path) if claude_prompt(d) is not None]
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
    edits, failed, errors, interrupted, wrote = {}, set(), 0, 0, {}
    # every model call, main conversation and subagents, priced one by one; Claude Code writes a running total
    # per process, and a resumed session starts a new one, so the totals are kept per process and added up
    procs, calls, thinking, key, stream, unsaved = {}, {}, {}, None, False, 0
    for i, d in enumerate(claude_lines(path)):
        t, ts = d.get("type"), d.get("timestamp") or ""
        inside = within(ts, win)
        key = key or d.get("sessionId")
        # what was loaded: whole session, whatever part the receipt covers
        if t == "stream-init":
            stream = True
        elif t == "cost-state":
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
            unsaved += not text
            first_prompt = first_prompt or text or None
        elif t == "assistant" and d.get("isSidechain"):  # files subagents wrote count too
            for b in (d.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    claude_edit(b, edits, wrote)
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
                    claude_edit(b, edits, wrote)
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
                            claude_edit(b, edits, wrote)
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
        if any("totalLinesAdded" in p for p in procs.values()):  # claude -p's output doesn't count them
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
    texts = {}
    for i, p in edits.items():  # a later Write's text replaces an earlier one; an Edit leaves none
        if i not in failed:
            texts[p] = wrote.get(i)
    files_part(r, sorted(texts), texts=texts)
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
    if unsaved:
        r["prompts_unsaved"] = unsaved
    if stream:  # claude -p's output says what was loaded at the start, but not instruction files or hook runs
        r["log_name"] = "claude -p output"
        r["hooks"], r["memory"] = None, None
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


def long_from(model):
    """the prompt size past which a model costs more, if it does"""
    row = rates_for(model) or []
    extra = row[5] if len(row) > 5 else {}
    return extra["above"][0] if extra.get("above") else (extra["tiers"][0][0] if extra.get("tiers") else None)


def codex_call(bill, model, u, summed=False):
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
        summed=summed,
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
    written, deleted, patched_by_event, patch_inputs, texts = set(), set(), False, [], {}
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
                        texts[f] = ch.get("content") if kind == "add" and isinstance(ch.get("content"), str) else None
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
    files_part(r, sorted(written - deleted), len(deleted), texts)
    r["skills_used"] = dict(skills)
    r["mcp_used"] = dict(mcp)
    r["hooks"] = None  # Codex session logs don't record hook runs
    r["memory"] = ["AGENTS.md"] if agents_md else []
    r["first_prompt"] = first_prompt
    return r


EXEC_JSON = "codex exec --json output"


def is_exec_json(path):
    """is this the output of `codex exec --json`? It starts with the thread it made"""
    try:
        return next(lines(path), {}).get("type") == "thread.started"
    except (OSError, StopIteration):
        return False


def codex_exec(path, part=None):
    """the output of `codex exec --json` (its events, printed as the run went): the replies, commands, files and
    tokens, without the prompt, the model, Codex's version or any times, which it doesn't print"""
    r = {"tool": "Codex CLI", "part": "whole session", "log_name": EXEC_JSON}
    usage, calls, shell, web, mcp, errors, written, deleted, replies, key = collections.Counter(), 0, 0, 0, 0, 0, set(), set(), 0, None
    for d in lines(path):
        t, it = d.get("type"), d.get("item") or {}
        if t == "thread.started":
            key = key or d.get("thread_id")
        elif t == "turn.completed":
            usage.update({k: v for k, v in (d.get("usage") or {}).items() if isinstance(v, int)})
        elif t == "item.completed":
            kind = it.get("type")
            if kind == "agent_message":
                replies += 1
            elif kind == "command_execution":
                calls, shell = calls + 1, shell + 1
                errors += it.get("exit_code") not in (0, None)
            elif kind == "file_change":
                calls += 1
                for ch in it.get("changes") or []:
                    (deleted if ch.get("kind") == "delete" else written).add(ch.get("path"))
            elif kind == "web_search":
                calls, web = calls + 1, web + 1
            elif kind == "mcp_tool_call":
                calls, mcp = calls + 1, mcp + 1
    if not key:
        sys.exit(f"receipt: {path} has no thread.started event; is it the output of codex exec --json?")
    r.update(version="", models=[], providers=[], effort="not recorded", permissions=None, started=None, ended=None,
             prompts=1, prompts_unsaved=1, model_time_ms=None, session_key=key, first_prompt=None,
             cost_note=f"no model in {EXEC_JSON}, so no price (--model names it)", billing=codex_billing([]),
             tokens_in=usage["input_tokens"], tokens_cached=usage["cached_input_tokens"],
             tokens_out=usage["output_tokens"], tool_calls=calls, shell_commands=shell, web=web, images_made=0,
             tool_errors=errors, interrupted=0, skills_used={}, mcp_used={"MCP tool calls": mcp} if mcp else {},
             hooks=None, memory=None, replies=replies, _usage=dict(usage))  # fmt: skip
    files_part(r, sorted(p for p in written - deleted if p), len(deleted))
    return r


def exec_turns(path):
    """codex exec --json output as one turn: its last reply, tool calls and files; no times, prompt or model"""
    reply, calls, shell, files = None, 0, 0, set()
    for d in lines(path):
        it = d.get("item") or {}
        if d.get("type") != "item.completed":
            continue
        if it.get("type") == "agent_message" and (it.get("text") or "").strip():
            reply = it["text"]
        elif it.get("type") in ("command_execution", "file_change", "web_search", "mcp_tool_call"):
            calls += 1
            shell += it.get("type") == "command_execution"
            files |= {c.get("path") for c in it.get("changes") or [] if c.get("kind") != "delete"}
    return [{"n": 1, "started": None, "time_ms": None, "tool_calls": calls, "shell_commands": shell,
             "files": len(files - {None}), "prompt": None, "reply": reply, "model": None, "effort": None,
             "_models": {}}]  # fmt: skip


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
    errors, model_errors, interrupted, written, texts = 0, 0, 0, set(), {}
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
            texts.update(dict.fromkeys(p.get("files") or []))
        if p.get("type") != "tool":
            continue
        n, st = p.get("tool", "?"), p.get("state") or {}
        tools[n] += 1
        inp = st.get("input") or {}
        if st.get("status") == "error":
            errors += 1
        elif n in ("write", "edit", "multiedit") and inp.get("filePath"):
            written.add(inp["filePath"])
            texts[inp["filePath"]] = inp.get("content") if n == "write" and isinstance(inp.get("content"), str) else None
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
    files_part(r, sorted(written), texts=texts)
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
        span = max(round((when(t["end"]) - when(t["at"])).total_seconds() * 1000), 0)
        # the tool's own durations overlap when background work wakes the model within one prompt, so their sum
        # can pass the time from the prompt to its last work; that span is as long as a prompt can have run
        ms = min(t["ms"], span) if t["ms"] and span else t["ms"] or span
        row = {"n": n, "started": t["at"], "time_ms": ms, "tool_calls": t["tools"],
               "shell_commands": t["shell"], "files": len(files),
               "prompt": t["prompt"], "reply": t["reply"] or None, "model": t["model"],
               "effort": t["effort"]}  # fmt: skip
        if priced:
            row["cost_usd"] = round(t["own"] or t["bill"].total(), 6)
        row["_models"] = models_of(t)
        out.append(row)
    return out


def models_of(t):
    """-> {model: [$, tokens in, tokens out]} for one turn; a tool's own figure is shared out in proportion"""
    per = {}
    for it in t["bill"].items():
        m = per.setdefault(it["model"], [0.0, 0, 0])
        m[0] += it.get("usd", 0)
        if it["kind"] == "output":
            m[2] += it["count"]
        elif it["kind"] in CLASSES or it["kind"] == "no price":
            m[1] += it["count"]
    if t["own"]:
        paid = sum(m[0] for m in per.values())
        if paid:
            for m in per.values():
                m[0] *= t["own"] / paid
        else:
            per.setdefault(t["model"] or "?", [0.0, 0, 0])[0] = t["own"]
    return per


def claude_turns(path):
    """-> one row per prompt: when, how long, its calls priced (subagents' too), tool calls, files, last reply"""
    rows, failed = [], set()
    for i, d in enumerate(claude_lines(path)):
        t, ts = d.get("type"), d.get("timestamp") or ""
        text = claude_prompt(d)
        if text is not None:
            rows.append(new_turn(ts, text))
            rows[-1]["effort"] = d.get("effort")
            continue
        if not rows:
            continue
        cur = rows[-1]
        if worked(d):  # bookkeeping entries come days later when a session is reopened; they aren't the turn's
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
                for b in m.get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        claude_edit(b, cur["edits"])
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


def worked(d):
    """a model reply, a tool's result or a finished compaction: what marks how long a prompt kept Claude Code busy"""
    t = d.get("type")
    if t == "assistant":  # Claude Code writes "<synthetic>" replies itself, e.g. when a session is resumed
        return not str((d.get("message") or {}).get("model") or "").startswith("<")
    if t == "system" and d.get("subtype") == "compact_boundary":
        return True
    c = (d.get("message") or {}).get("content") if t == "user" else None
    return isinstance(c, list) and any(  # an interruption ends the prompt's work too
        isinstance(x, dict) and (x.get("type") == "tool_result" or str(x.get("text", "")).startswith("[Request interrupted"))
        for x in c
    )


def claude_edit(b, edits, wrote=None):
    inp, n = b.get("input") or {}, b.get("name")
    if n in EDIT_TOOLS and inp.get(EDIT_TOOLS[n]):
        edits[b.get("id")] = inp[EDIT_TOOLS[n]]
        if wrote is not None and n == "Write" and isinstance(inp.get("content"), str):
            wrote[b.get("id")] = inp["content"]


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


# ---------- Qwen Code ----------

# Qwen Code (a fork of Gemini CLI) keeps one JSONL file per session in ~/.qwen/projects/<folder>/chats/. Each API
# call is logged twice: on the reply, and as an api_response telemetry event. Only the events also cover calls made
# in the background (its memory extractor), so they are the ledger; a log without them is read from the replies.
QWEN_SHELL = ("run_shell_command",)
QWEN_WRITES = {"write_file": "file_path", "edit": "file_path", "replace": "file_path"}
GOOGLE_AUTH = ("gemini", "vertex-ai", "gemini-api-key", "oauth-personal")  # reasoning is counted apart from output


def qwen_dir():
    return os.path.expanduser(
        os.environ.get("QWEN_RUNTIME_DIR") or os.environ.get("QWEN_HOME") or os.path.join(home(), ".qwen")
    )


def qwen_prompt(d):
    """-> your prompt text if this entry is one, else None; Qwen Code marks what it adds itself with a subtype"""
    if d.get("type") != "user" or d.get("subtype") or d.get("provenance", "real_user") != "real_user":
        return None
    parts = (d.get("message") or {}).get("parts") or []
    text = "\n".join(
        x["text"] for x in parts if isinstance(x, dict) and isinstance(x.get("text"), str) and not x.get("thought")
    )
    return text if text.strip() else None


def qwen_cwd(path):
    for i, d in enumerate(lines(path)):
        if d.get("cwd"):
            return d["cwd"]
        if i > 50:
            break
    return ""


def qwen_calls(path):
    """-> [(line number, time, model, login type, usage)] for every API call the session made"""
    events, replies, auth = [], [], None
    for i, d in enumerate(lines(path)):
        auth = (d.get("executionContext") or {}).get("authType") or auth
        u = (d.get("systemPayload") or {}).get("uiEvent") or {}
        if d.get("type") == "system" and str(u.get("event.name", "")).endswith("api_response"):
            events.append((i, d.get("timestamp") or "", u.get("model"), u.get("auth_type") or auth, {
                "in": u.get("input_token_count") or 0, "cached": u.get("cached_content_token_count") or 0,
                "out": u.get("output_token_count") or 0, "thoughts": u.get("thoughts_token_count") or 0,
                "ms": u.get("duration_ms") or 0}))  # fmt: skip
        elif d.get("type") == "assistant" and d.get("usageMetadata"):
            m = d["usageMetadata"]
            replies.append((i, d.get("timestamp") or "", d.get("model"), auth, {
                "in": m.get("promptTokenCount") or 0, "cached": m.get("cachedContentTokenCount") or 0,
                "out": m.get("candidatesTokenCount") or 0, "thoughts": m.get("thoughtsTokenCount") or 0,
                "ms": 0}))  # fmt: skip
    return events or replies


def qwen_call(bill, model, auth, u):
    # the prompt count includes the cached tokens; reasoning is inside the output count, except on Google's API
    out = u["out"] + (u["thoughts"] if auth in GOOGLE_AUTH else 0)
    bill.add(model, [max(u["in"] - u["cached"], 0), u["cached"], 0, 0, out])
    return u["in"], u["cached"], out


QWEN_LOGINS = {
    "openai": "an API key for an OpenAI-compatible service",
    "anthropic": "an Anthropic API key",
    "gemini": "a Gemini API key",
    "vertex-ai": "Vertex AI",
}


def qwen_billing(auths):
    auths = [x for x in dict.fromkeys(auths) if x]
    if auths == ["qwen-oauth"]:
        return "Qwen OAuth: a free daily allowance, not charged per run"
    if auths:
        how = " and ".join(QWEN_LOGINS.get(x, f"a {x} login") for x in auths)
        return f"{how}: charged per token by that service, whose prices can differ from the list prices above"
    return "not recorded in the session log"


def qwen_window(path, part):
    marks = [i for i, d in enumerate(lines(path)) if qwen_prompt(d) is not None] if part else []
    sel, name = pick(len(marks), part)
    return bounds(marks, sel), name


def qwen_tool_calls(d):
    """-> [(call id, tool name, args)] in a reply"""
    return [
        (fc.get("id"), fc.get("name") or "?", fc.get("args") or {})
        for x in (d.get("message") or {}).get("parts") or []
        for fc in [x.get("functionCall") if isinstance(x, dict) else None]
        if isinstance(fc, dict)
    ]


def qwen(path, part=None):
    win, name = qwen_window(path, part)
    r = {"tool": "Qwen Code", "part": name}
    versions, models, modes, auths, stamps = [], [], [], [], []
    prompts, first_prompt, key = 0, None, None
    calls, mcp = collections.Counter(), collections.Counter()
    errors, interrupted, written, pending, texts = 0, 0, set(), {}, {}
    for i, d in enumerate(lines(path)):
        key = key or d.get("sessionId")
        if not within(i, win):
            continue
        t, ts = d.get("type"), d.get("timestamp")
        if ts:
            stamps.append(ts)
        versions.append(d.get("version"))
        ctx = d.get("executionContext") or {}
        modes.append(ctx.get("approvalMode"))
        auths.append(ctx.get("authType"))
        text = qwen_prompt(d)
        if text is not None:
            prompts += 1
            first_prompt = first_prompt or text
        elif t == "assistant":
            for cid, n, args in qwen_tool_calls(d):
                calls[n] += 1
                if n.startswith("mcp__") or "__" in n:
                    mcp[n] += 1
                if n in QWEN_WRITES and args.get(QWEN_WRITES[n]):
                    whole = args.get("content") if n == "write_file" and isinstance(args.get("content"), str) else None
                    pending[cid] = (args[QWEN_WRITES[n]], whole)
        elif t == "tool_result":
            res = d.get("toolCallResult") or {}
            if res.get("status") == "error" or res.get("error"):
                errors += 1
            elif res.get("callId") in pending:
                f, whole = pending[res["callId"]]
                written.add(f)
                texts[f] = whole
        elif t == "system" and d.get("subtype") == "turn_result":
            interrupted += (d.get("systemPayload") or {}).get("state") == "cancelled"
    if not stamps:
        sys.exit(f"receipt: {path} has no timestamped entries; is it a Qwen Code session log?")
    bill, tin, tcached, tout, busy = Bill(), 0, 0, 0, 0
    for i, ts, model, auth, u in qwen_calls(path):
        if within(i, win):
            a, c, o = qwen_call(bill, model, auth, u)
            tin, tcached, tout, busy = tin + a, tcached + c, tout + o, busy + u["ms"]
            models.append(model)
            auths.append(auth)
    r["version"] = span(versions)
    r["models"] = list(dict.fromkeys(m for m in models if m))
    r["effort"] = "not in Qwen Code logs"
    r["permissions"] = f"approvals {span(modes)}"
    r["started"], r["ended"] = min(stamps), max(stamps)
    r["prompts"] = prompts
    r["model_time_ms"] = busy or None
    r["session_key"] = key or os.path.basename(path)
    if bill.lines:
        r["cost_usd"] = round(bill.total(), 6)
        r["cost_note"] = "worked out from the logged calls at API list prices; Qwen Code logs no price"
        priced(r, bill)
    else:
        r["cost_note"] = "Qwen Code logs no price" + (
            f", and the price table has none for {', '.join(bill.unpriced)}" if bill.unpriced else ""
        )
    r["billing"] = qwen_billing(auths)
    r["tokens_in"], r["tokens_cached"], r["tokens_out"] = tin, tcached, tout
    r["tool_calls"] = sum(calls.values())
    r["shell_commands"] = sum(calls.get(n, 0) for n in QWEN_SHELL)
    r["web"] = sum(v for n, v in calls.items() if n.startswith("web_") or n.endswith("web_search"))
    r["tool_errors"] = errors
    r["interrupted"] = interrupted
    files_part(r, sorted(written), texts=texts)
    r["skills_used"] = {}
    r["mcp_used"] = dict(mcp)
    r["hooks"] = None
    r["memory"] = None
    r["first_prompt"] = first_prompt
    return r


def qwen_turns(path):
    by_line = collections.defaultdict(list)
    for c in qwen_calls(path):
        by_line[c[0]].append(c)
    rows, pending = [], {}
    for i, d in enumerate(lines(path)):
        ts, t = d.get("timestamp") or "", d.get("type")
        text = qwen_prompt(d)
        if text is not None:
            rows.append(new_turn(ts, text))
            continue
        if not rows:
            continue
        cur = rows[-1]
        for _, cts, model, auth, u in by_line.get(i, []):
            qwen_call(cur["bill"], model, auth, u)
            cur["model"] = cur["model"] or model
            cur["end"] = max(cur["end"], cts)
        if t in ("assistant", "tool_result"):
            cur["end"] = max(cur["end"], ts)
        if t == "assistant":
            said = [x["text"] for x in (d.get("message") or {}).get("parts") or []
                    if isinstance(x, dict) and isinstance(x.get("text"), str) and not x.get("thought")]  # fmt: skip
            if "".join(said).strip():
                cur["texts"][i], cur["reply_of"] = said, i
            for cid, n, args in qwen_tool_calls(d):
                cur["tools"] += 1
                cur["shell"] += n in QWEN_SHELL
                if n in QWEN_WRITES and args.get(QWEN_WRITES[n]):
                    pending[cid] = args[QWEN_WRITES[n]]
        elif t == "tool_result":
            res = d.get("toolCallResult") or {}
            if res.get("status") != "error" and not res.get("error") and res.get("callId") in pending:
                cur["files"].add(pending[res["callId"]])
    return done_turns(rows)


# ---------- Gemini CLI ----------

# Gemini CLI keeps one JSONL file per session in ~/.gemini/tmp/<folder>/chats/ (one whole JSON file in older
# versions). A message is written again each time it changes, since its tokens and tool calls come later, so the
# last copy of each id is the one to read. Each reply is one API call: its prompt count includes the cached tokens,
# and reasoning is counted apart from the output. A subagent's calls are in chats/<session id>/.
GEMINI_SHELL = ("run_shell_command",)
GEMINI_WRITES = ("write_file", "replace")


def gemini_dir():
    return os.path.join(os.path.expanduser(os.environ.get("GEMINI_CLI_HOME") or home()), ".gemini")


def gemini_doc(path):
    """an older whole-JSON session file, else {}"""
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def gemini_head(path):
    """-> the session's header: sessionId, projectHash, startTime"""
    if path.endswith(".json"):
        return gemini_doc(path)
    return next((d for d in lines(path) if isinstance(d, dict)), {})


def gemini_messages(path):
    """-> the session's messages in order, each as last written ($set, $patch and $rewindTo lines are skipped)"""
    if path.endswith(".json"):
        return [m for m in gemini_doc(path).get("messages") or [] if isinstance(m, dict)]
    last = {}
    for d in lines(path):
        if isinstance(d, dict) and d.get("id") and d.get("type"):
            last[d["id"]] = d  # a dict keeps the place of the first copy
    return list(last.values())


def gemini_text(parts):
    if isinstance(parts, (str, dict)):
        parts = [parts]
    return "\n".join(
        x if isinstance(x, str) else x["text"]
        for x in parts or []
        if isinstance(x, str) or (isinstance(x, dict) and isinstance(x.get("text"), str) and not x.get("thought"))
    )


def gemini_prompt(d):
    """-> your prompt text if this message is one, else None; tool results are logged as user messages too"""
    if d.get("type") != "user":
        return None
    text = gemini_text(d.get("displayContent") or d.get("content"))
    if text.lstrip().startswith("<session_context>"):  # Gemini CLI's own opening message
        return None
    return text if text.strip() else None


def gemini_cwd(path):
    folder = os.path.dirname(os.path.dirname(path))
    try:
        with open(os.path.join(folder, ".project_root"), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        pass
    names = gemini_doc(os.path.join(gemini_dir(), "projects.json")).get("projects")
    return next((p for p, s in (names or {}).items() if s == os.path.basename(folder)), "")


def gemini_here(path):
    """was this session run in this folder? Older folders are named by a hash, which the header also holds"""
    return same_folder(gemini_cwd(path)) or gemini_head(path).get("projectHash") in {sha(h) for h in heres()}


def gemini_calls(path):
    """-> [(message number, time, model, tokens)] for every reply, a subagent's too (placed by its time)"""
    main = gemini_messages(path)
    times = [m.get("timestamp") or "" for m in main]
    out = [(i, m.get("timestamp") or "", m.get("model"), m["tokens"]) for i, m in enumerate(main)
           if m.get("type") == "gemini" and isinstance(m.get("tokens"), dict)]  # fmt: skip
    sid = gemini_head(path).get("sessionId")
    for f in sorted(glob.glob(os.path.join(os.path.dirname(path), sid, "*.json*"))) if sid else []:
        for m in gemini_messages(f):
            if m.get("type") == "gemini" and isinstance(m.get("tokens"), dict):
                ts = m.get("timestamp") or ""
                out.append((max(bisect.bisect_right(times, ts) - 1, 0), ts, m.get("model"), m["tokens"]))
    return out


def gemini_call(bill, model, t):
    # the prompt count includes the cached tokens; reasoning and the tool-use prompt are counted apart
    cached = t.get("cached") or 0
    tin = (t.get("input") or 0) + (t.get("tool") or 0)
    out = (t.get("output") or 0) + (t.get("thoughts") or 0)
    bill.add(model, [max(tin - cached, 0), cached, 0, 0, out])
    return tin, cached, out


def gemini_tool_calls(d):
    return [c for c in d.get("toolCalls") or [] if isinstance(c, dict)] if d.get("type") == "gemini" else []


def gemini(path, part=None):
    msgs = gemini_messages(path)
    marks = [i for i, d in enumerate(msgs) if gemini_prompt(d) is not None] if part else []
    sel, name = pick(len(marks), part)
    win = bounds(marks, sel)
    r = {"tool": "Gemini CLI", "part": name}
    models, stamps, cwd = [], [], gemini_cwd(path)
    prompts, first_prompt = 0, None
    calls, mcp = collections.Counter(), collections.Counter()
    errors, interrupted, written, texts = 0, 0, set(), {}
    for i, d in enumerate(msgs):
        if not within(i, win):
            continue
        if d.get("timestamp"):
            stamps.append(d["timestamp"])
        text = gemini_prompt(d)
        if text is not None:
            prompts += 1
            first_prompt = first_prompt or text
        tcs = gemini_tool_calls(d)
        for c in tcs:
            n, args = c.get("name") or "?", c.get("args") or {}
            calls[n] += 1
            if n.startswith("mcp_"):  # mcp_<server>_<tool>; a server with _ in its name is cut short
                mcp[n[4:].split("_")[0]] += 1
            if c.get("status") == "error":
                errors += 1
            elif c.get("status") == "success" and n in GEMINI_WRITES and args.get("file_path"):
                f = os.path.join(cwd, args["file_path"])
                written.add(f)
                texts[f] = args.get("content") if n == "write_file" and isinstance(args.get("content"), str) else None
        interrupted += any(c.get("status") == "cancelled" for c in tcs)
    if not stamps:
        sys.exit(f"receipt: {path} has no timestamped messages; is it a Gemini CLI session log?")
    bill, tin, tcached, tout = Bill(), 0, 0, 0
    for i, ts, model, t in gemini_calls(path):
        if within(i, win):
            a, c, o = gemini_call(bill, model, t)
            tin, tcached, tout = tin + a, tcached + c, tout + o
            models.append(model)
            stamps.append(ts or stamps[-1])
    r["version"] = ""  # Gemini CLI doesn't log its version
    r["models"] = list(dict.fromkeys(m for m in models if m))
    r["effort"] = "not in Gemini CLI logs"
    r["permissions"] = "not in Gemini CLI logs"
    r["started"], r["ended"] = min(stamps), max(stamps)
    r["prompts"] = prompts
    r["model_time_ms"] = None
    r["session_key"] = gemini_head(path).get("sessionId") or os.path.basename(path)
    if bill.lines:
        r["cost_usd"] = round(bill.total(), 6)
        r["cost_note"] = "worked out from the logged calls at API list prices; Gemini CLI logs no price"
        priced(r, bill)
    else:
        r["cost_note"] = "Gemini CLI logs no price" + (
            f", and the price table has none for {', '.join(bill.unpriced)}" if bill.unpriced else ""
        )
    r["billing"] = (
        "not in Gemini CLI logs: a Google account's free allowance isn't charged; "
        "a Gemini API key or Vertex AI is charged per token"
    )
    r["tokens_in"], r["tokens_cached"], r["tokens_out"] = tin, tcached, tout
    r["tool_calls"] = sum(calls.values())
    r["shell_commands"] = sum(calls.get(n, 0) for n in GEMINI_SHELL)
    r["web"] = sum(v for n, v in calls.items() if n in ("web_fetch", "google_web_search"))
    r["tool_errors"] = errors
    r["interrupted"] = interrupted
    files_part(r, sorted(written), texts=texts)
    r["skills_used"] = {}
    r["mcp_used"] = dict(mcp)
    r["hooks"] = None
    r["memory"] = None
    r["first_prompt"] = first_prompt
    return r


def gemini_turns(path):
    msgs, cwd = gemini_messages(path), gemini_cwd(path)
    by_msg = collections.defaultdict(list)
    for c in gemini_calls(path):
        by_msg[c[0]].append(c)
    rows = []
    for i, d in enumerate(msgs):
        ts = d.get("timestamp") or ""
        text = gemini_prompt(d)
        if text is not None:
            rows.append(new_turn(ts, text))
        if not rows:
            continue
        cur = rows[-1]
        for _, cts, model, t in by_msg.get(i, []):
            gemini_call(cur["bill"], model, t)
            cur["model"] = cur["model"] or model
            cur["end"] = max(cur["end"], cts)
        if d.get("type") == "gemini":
            cur["end"] = max(cur["end"], ts)
            said = gemini_text(d.get("content"))
            if said.strip():
                cur["texts"][i], cur["reply_of"] = [said], i
        for c in gemini_tool_calls(d):
            n, args = c.get("name") or "?", c.get("args") or {}
            cur["tools"] += 1
            cur["shell"] += n in GEMINI_SHELL
            cur["end"] = max(cur["end"], c.get("timestamp") or "")
            if c.get("status") == "success" and n in GEMINI_WRITES and args.get("file_path"):
                cur["files"].add(os.path.join(cwd, args["file_path"]))
    return done_turns(rows)


# ---------- GitHub Copilot CLI ----------

# Copilot CLI keeps each session's events in ~/.copilot/session-state/<session id>/events.jsonl. Every API call
# leaves a session.usage_record: its input count includes cache reads and writes, its output count includes the
# reasoning, and on GitHub's billing it holds the AI credits the call used (1 credit = $0.01). session.shutdown
# holds running totals for the whole session, so it isn't added again.
COPILOT_SHELL = ("bash", "powershell", "local_shell")
COPILOT_WRITES = ("create", "edit", "str_replace", "str_replace_editor")


def copilot_dir():
    return os.path.expanduser(os.environ.get("COPILOT_HOME") or os.path.join(home(), ".copilot"))


def copilot_prompt(d):
    """-> your prompt text if this event is one, else None (a skill's or another agent's message has a source)"""
    if d.get("type") != "user.message":
        return None
    x = d.get("data") or {}
    if x.get("isAutopilotContinuation") or str(x.get("source") or "").startswith(("skill-", "agent-")):
        return None
    text = x.get("content")
    return text if isinstance(text, str) and text.strip() else None


def copilot_cwd(path):
    for i, d in enumerate(lines(path)):
        if d.get("type") in ("session.start", "session.resume"):
            return ((d.get("data") or {}).get("context") or {}).get("cwd") or ""
        if i > 50:
            break
    return ""


def copilot_calls(path):
    """-> [(line number, time, usage)] for every API call the session made"""
    return [(i, d.get("timestamp") or "", (d.get("data") or {}).get("usage") or {})
            for i, d in enumerate(lines(path)) if d.get("type") == "session.usage_record"]  # fmt: skip


def copilot_call(bill, u):
    read, write, tin = u.get("cacheReadTokens") or 0, u.get("cacheWriteTokens") or 0, u.get("inputTokens") or 0
    out = u.get("outputTokens") or 0  # the reasoning is inside it
    bill.add(u.get("model"), [max(tin - read - write, 0), read, write, 0, out])
    return tin, read, out


def copilot_billing(byok, nano, status):
    if nano:
        part = " (some calls have no figure)" if status == "partial" else ""
        return f"GitHub Copilot: {nano / 1e9:,.2f} AI credits by the log, ${nano / 1e11:,.2f} at $0.01 a credit{part}"
    if byok:
        return "your own API key: charged per token by that service, whose prices can differ from the list prices above"
    return "GitHub Copilot plan; the log has no AI-credit figure for these calls"


def copilot(path, part=None):
    marks = [i for i, d in enumerate(lines(path)) if copilot_prompt(d) is not None] if part else []
    sel, name = pick(len(marks), part)
    win = bounds(marks, sel)
    r = {"tool": "Copilot CLI", "part": name}
    versions, models, efforts, stamps = [], [], [], []
    prompts, first_prompt, key = 0, None, None
    calls, mcp = collections.Counter(), collections.Counter()
    errors, interrupted, written, deleted, pending, texts = 0, 0, set(), set(), {}, {}
    bill, tin, tcached, tout, busy, nano, byok, status = Bill(), 0, 0, 0, 0, 0, False, None
    for i, d in enumerate(lines(path)):
        t, x = d.get("type"), d.get("data") or {}
        if t == "session.start":
            key = x.get("sessionId")
            versions.append(x.get("copilotVersion"))
        if t in ("session.start", "session.resume", "session.model_change") and within(i, win):
            efforts.append(x.get("reasoningEffort"))
        if not within(i, win):
            continue
        if d.get("timestamp"):
            stamps.append(d["timestamp"])
        text = copilot_prompt(d)
        if text is not None:
            prompts += 1
            first_prompt = first_prompt or text
        elif t == "assistant.message":
            for c in x.get("toolRequests") or []:
                n = c.get("name") or "?"
                calls[n] += 1
                if c.get("mcpServerName"):
                    mcp[c["mcpServerName"]] += 1
                args = c.get("arguments") or {}
                if n in COPILOT_WRITES and args.get("path"):
                    whole = args.get("file_text") if n == "create" and isinstance(args.get("file_text"), str) else None
                    pending[c.get("toolCallId")] = (args["path"], whole)
        elif t == "tool.execution_complete":
            if not x.get("success"):
                errors += 1
            elif x.get("fileEdits"):
                f, whole = pending.get(x.get("toolCallId"), (None, None))
                for e in x["fileEdits"]:
                    (deleted if e.get("kind") == "delete" else written).add(e.get("path"))
                    texts[e.get("path")] = whole if e.get("path") == f else None
            elif x.get("toolCallId") in pending:
                f, whole = pending[x["toolCallId"]]
                written.add(f)
                texts[f] = whole
        elif t == "abort":
            interrupted += 1
        elif t == "session.usage_record":
            u = x.get("usage") or {}
            a, c, o = copilot_call(bill, u)
            tin, tcached, tout, busy = tin + a, tcached + c, tout + o, busy + (u.get("duration") or 0)
            models.append(u.get("model"))
            efforts.append(u.get("reasoningEffort"))
            nano += (u.get("copilotUsage") or {}).get("totalNanoAiu") or 0
            byok = byok or bool(u.get("isByok"))
            status = "partial" if status == "partial" or u.get("aiCreditsStatus") == "partial" else status
    if not stamps:
        sys.exit(f"receipt: {path} has no timestamped events; is it a Copilot CLI session log?")
    r["version"] = span(versions)
    r["models"] = list(dict.fromkeys(m for m in models if m))
    r["effort"] = span(efforts) if any(efforts) else "not recorded"
    r["permissions"] = "not in Copilot CLI logs"
    r["started"], r["ended"] = min(stamps), max(stamps)
    r["prompts"] = prompts
    r["model_time_ms"] = busy or None
    r["session_key"] = key or os.path.basename(os.path.dirname(path))
    if bill.lines:
        r["cost_usd"] = round(bill.total(), 6)
        r["cost_note"] = "worked out from the logged calls at API list prices"
        priced(r, bill)
    else:
        r["cost_note"] = "no list price" + (
            f": the price table has none for {', '.join(bill.unpriced)}" if bill.unpriced else ""
        )
    r["billing"] = copilot_billing(byok, nano, status)
    r["tokens_in"], r["tokens_cached"], r["tokens_out"] = tin, tcached, tout
    r["tool_calls"] = sum(calls.values())
    r["shell_commands"] = sum(calls.get(n, 0) for n in COPILOT_SHELL)
    r["web"] = sum(v for n, v in calls.items() if n.startswith("web_") or n.endswith("web_search"))
    r["tool_errors"] = errors
    r["interrupted"] = interrupted
    files_part(r, sorted(p for p in written if p), len(deleted), texts)
    r["skills_used"] = {}
    r["mcp_used"] = dict(mcp)
    r["hooks"] = None
    r["memory"] = None
    r["first_prompt"] = first_prompt
    return r


def copilot_turns(path):
    rows, pending = [], {}
    for i, d in enumerate(lines(path)):
        t, x, ts = d.get("type"), d.get("data") or {}, d.get("timestamp") or ""
        text = copilot_prompt(d)
        if text is not None:
            rows.append(new_turn(ts, text))
            continue
        if not rows:
            continue
        cur = rows[-1]
        if t == "session.usage_record":
            u = x.get("usage") or {}
            copilot_call(cur["bill"], u)
            cur["model"] = cur["model"] or u.get("model")
            cur["effort"] = cur["effort"] or u.get("reasoningEffort")
            cur["end"] = max(cur["end"], ts)
        elif t == "assistant.message":
            cur["end"] = max(cur["end"], ts)
            said = x.get("content")
            if isinstance(said, str) and said.strip() and not x.get("parentToolCallId"):
                cur["texts"][i], cur["reply_of"] = [said], i
            for c in x.get("toolRequests") or []:
                n = c.get("name") or "?"
                cur["tools"] += 1
                cur["shell"] += n in COPILOT_SHELL
                if n in COPILOT_WRITES and (c.get("arguments") or {}).get("path"):
                    pending[c.get("toolCallId")] = c["arguments"]["path"]
        elif t == "tool.execution_complete":
            cur["end"] = max(cur["end"], ts)
            if x.get("success"):
                edits = [e.get("path") for e in x.get("fileEdits") or [] if e.get("kind") != "delete"]
                cur["files"].update(p for p in edits or [pending.get(x.get("toolCallId"))] if p)
    return done_turns(rows)


TURNS = {"claude": claude_turns, "codex": codex_turns, "opencode": opencode_turns, "qwen": qwen_turns,
         "gemini": gemini_turns, "copilot": copilot_turns}  # fmt: skip


# ---------- the output page ----------

# one HTML file that shows what the run made: the receipt, every prompt and its full reply, every file the run
# wrote, and each web page it made running in a sandboxed frame. It loads nothing from this site and sends nothing.
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
               ".webp": "image/webp", ".svg": "image/svg+xml"}  # fmt: skip
PAGE_TEXT_MAX = 2**20  # a text file bigger than this is shown by its size alone
LOCAL_REF = re.compile(r"^(?![a-z][a-z0-9+.-]*:|//|#)", re.I)  # not http:, data:, //host or #anchor
SCRIPT_SRC = re.compile(r"<script\b([^>]{0,500}?)\bsrc\s*=\s*([\"'])([^\"'<>]{1,500})\2([^>]{0,500})>\s{0,100}</script>", re.I)
STYLE_LINK = re.compile(r"<link\b[^>]{0,500}?>", re.I)
HREF = re.compile(r"\bhref\s*=\s*([\"'])([^\"'<>]{1,500})\1", re.I)
IMG_SRC = re.compile(r"(<img\b[^>]{0,500}?\bsrc\s*=\s*)([\"'])([^\"'<>]{1,500})\2", re.I)
MEDIA_SRC = re.compile(r"(<(?:audio|video|source)\b[^>]{0,500}?\bsrc\s*=\s*)([\"'])([^\"'<>]{1,500})\2", re.I)
PAGE_MEDIA_MAX = 16 * 2**20  # pictures, sounds and videos put in one page, in all: it stays under 25 MB


def page_files(paths, texts, names, made=()):
    """-> [{name, body, path, source}] for the files the run wrote, then those made while it ran, named as a record
    or bundle names them"""
    out = []
    for n, p in enumerate(list(paths) + list(made), 1):
        ext = os.path.splitext(base_name(p))[1].lower()
        text = texts.get(p)
        body = file_body(p, text)
        source = ("as written" if text is not None else MADE_HOW if n > len(paths) else
                  "as it is on disk now" if body is not None else "not on disk now")  # fmt: skip
        out.append({"name": base_name(p) if names else f"file{n}{ext}", "body": body, "path": p, "source": source})
    return out


def inline_page(html_text, here, by_path, left=None):
    """-> the page with the run's own .js, .css, pictures, sounds and videos it names put inside it, the names it
    couldn't, and the paths of the sounds and videos it put in. left: [bytes of media the page can still hold]"""
    missing, inside = [], []
    left = [PAGE_MEDIA_MAX] if left is None else left

    def find(ref):
        ref = ref.split("?")[0].split("#")[0]
        if not ref or not LOCAL_REF.match(ref):
            return None
        return by_path.get(os.path.normpath(os.path.join(here, ref)))

    def script(m):
        if not LOCAL_REF.match(m.group(3)):
            return m.group(0)
        body = find(m.group(3))
        if body is None:
            missing.append(m.group(3))
            return m.group(0)
        code = body.decode("utf-8", "replace").replace("</script", "<\\/script")
        attrs = (m.group(1) + m.group(4)).strip()
        return f"<script{' ' + attrs if attrs else ''}>{code}</script>"

    def style(m):
        tag = m.group(0)
        h = HREF.search(tag)
        if not h or "stylesheet" not in tag.lower() or not LOCAL_REF.match(h.group(2)):
            return tag
        body = find(h.group(2))
        if body is None:
            missing.append(h.group(2))
            return tag
        return "<style>" + body.decode("utf-8", "replace").replace("</style", "<\\/style") + "</style>"

    def img(m):
        ref = m.group(3)
        body = find(ref) if LOCAL_REF.match(ref) else None
        kind = IMAGE_TYPES.get(os.path.splitext(ref.split("?")[0])[1].lower())
        if body is None or not kind:
            if LOCAL_REF.match(ref):
                missing.append(ref)
            return m.group(0)
        return f"{m.group(1)}{m.group(2)}data:{kind};base64,{base64.b64encode(body).decode()}{m.group(2)}"

    def media(m):
        ref = m.group(3)
        if not LOCAL_REF.match(ref):
            return m.group(0)
        ext = os.path.splitext(ref.split("?")[0])[1].lower()
        kind = AUDIO_TYPES.get(ext) or VIDEO_TYPES.get(ext)
        body = find(ref)
        if body is None or not kind or len(body) > left[0]:
            missing.append(ref if body is None or not kind else f"{ref} ({size_text(len(body))}, too big for the page)")
            return m.group(0)
        left[0] -= len(body)
        inside.append(os.path.normpath(os.path.join(here, ref.split("?")[0].split("#")[0])))
        return f"{m.group(1)}{m.group(2)}data:{kind};base64,{base64.b64encode(body).decode()}{m.group(2)}"

    html_text = SCRIPT_SRC.sub(script, html_text)
    html_text = STYLE_LINK.sub(style, html_text)
    html_text = IMG_SRC.sub(img, html_text)
    html_text = MEDIA_SRC.sub(media, html_text)
    return html_text, list(dict.fromkeys(missing)), inside


DATA_URI = re.compile(r"data:[a-z0-9.+-]{1,60}/[a-z0-9.+-]{1,60};base64,[A-Za-z0-9+/=]+", re.I)


def scrub_around_data(text, redact, where_, flag):
    """scrub() the page's text, not the base64 of the pictures, sounds and videos put in it: those aren't text, so
    in them a 'key-like string' is chance, and --redact would break them"""
    held = []

    def hold(m):
        held.append(m.group(0))
        return f"\0{len(held) - 1}\0"

    text = scrub(DATA_URI.sub(hold, text), redact, where_, flag)
    return re.sub("\0(\\d+)\0", lambda m: held[int(m.group(1))], text)


def smaller(path, ext, what):
    """-> (bytes, type) of a smaller copy of a sound or video, made with ffmpeg, the same bytes each time"""
    tmp = tempfile.mkdtemp(prefix="receipt-")
    try:
        same = ["-map_metadata", "-1", "-fflags", "+bitexact", "-flags", "+bitexact"]
        if ext in VIDEO_TYPES:
            out, kind = os.path.join(tmp, "small.mp4"), "video/mp4"
            run_ffmpeg(["-i", path, *same, "-vf", "scale='min(854,iw)':-2", "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
                        out], f"a smaller copy of {what}")  # fmt: skip
        else:
            out, kind = os.path.join(tmp, "small.m4a"), "audio/mp4"
            run_ffmpeg(["-i", path, "-vn", *same, "-c:a", "aac", "-b:a", "128k", out], f"a smaller copy of {what}")
        with open(out, "rb") as fh:
            return fh.read(), kind
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def output_page(r, s, rows, files, a, hide, extra="", linked=None):
    """-> the output page's HTML; text in it goes through scrub(), as --prompt and --reply do. Pictures, sounds and
    videos go inside it up to PAGE_MEDIA_MAX in all; linked: a folder beside the page that holds the files (a
    bundle's outputs/), for sounds and videos to play from instead"""
    e = html.escape
    left, inside = [PAGE_MEDIA_MAX], set()

    def media(f, ext):
        if linked is not None and ext not in IMAGE_TYPES:
            src, note = linked + urllib.parse.quote(f["name"]), ""
        else:
            b, kind, note = f["body"], IMAGE_TYPES.get(ext) or AUDIO_TYPES.get(ext) or VIDEO_TYPES[ext], ""
            if len(b) > left[0]:
                if ext in IMAGE_TYPES or not ffmpeg() or not os.path.isfile(f["path"]):
                    how = "" if ext in IMAGE_TYPES or ffmpeg() else " (with ffmpeg installed, a smaller copy is shown)"
                    return f'<p class="dim">Not shown: {size_text(len(b))}, more than the page holds{how}.</p>'
                b, kind = smaller(f["path"], ext, f["name"])
                if len(b) > left[0]:
                    return f'<p class="dim">Not shown: even a smaller copy is {size_text(len(b))}, more than the page holds.</p>'
                note = ('<p class="dim">A smaller copy, made with ffmpeg so it fits in the page; the record\'s '
                        "fingerprint is of the original.</p>")  # fmt: skip
            left[0] -= len(b)
            src = f"data:{kind};base64,{base64.b64encode(b).decode()}"
        if ext in IMAGE_TYPES:
            return f'<img alt="{e(f["name"])}" src="{src}">{note}'
        if ext in AUDIO_TYPES:
            return f'<audio controls preload="metadata" src="{src}"></audio>{note}'
        return f'<video controls preload="metadata" playsinline src="{src}"></video>{note}'

    by_path = {os.path.normpath(f["path"]): f["body"] for f in files if f["body"] is not None}
    parts = []
    shown = [] if "files" in hide else files
    for f in shown:
        if f["body"] is None or not f["name"].lower().endswith(PAGE_TYPES) or not is_text(f["body"]):
            continue
        page, missing, put = inline_page(f["body"].decode("utf-8", "replace"), os.path.dirname(f["path"]), by_path, left)
        inside.update(put)
        page = scrub_around_data(page, a.redact, f"the page {f['name']}", "--page")
        note = (f" It names files the run didn't make, or too big to put here, so they aren't here: {e(', '.join(missing))}."
                if missing else "")  # fmt: skip
        parts.append(
            f'<h3>{e(f["name"])}</h3><iframe sandbox="allow-scripts" srcdoc="{e(page)}" title="{e(f["name"])}">'
            f'</iframe><p class="dim">Running in a sandboxed frame: it can\'t reach this page or your browser\'s '
            f"storage, so a page that saves things may show an error.{note}</p>"
        )
    out = [f'<div class="paper own"><pre>{e(s)}</pre></div>']
    if parts:
        out.append(f"<h2>{'The page it made' if len(parts) == 1 else 'The pages it made'}</h2>" + "".join(parts))
    if rows:
        out.append("<h2>Prompts and replies</h2>")
        for n, t in enumerate(rows, 1):
            if not t["prompt"] and n == 1 and r.get("prompt_given"):
                out.append(f'<h3>Prompt {n}</h3><pre class="said">{e(r["first_prompt"])}</pre><p class="dim">Given by '
                           "the sender with --asked: claude -p doesn't write the prompt it was given.</p>")  # fmt: skip
            else:
                out.append(f'<h3>Prompt {n}</h3><pre class="said">{e(scrub(t["prompt"], a.redact))}</pre>' if t["prompt"] else
                           f'<h3>Prompt {n}</h3><p class="dim">Not in the log: claude -p doesn\'t write the prompt it was given.</p>')  # fmt: skip
            if t.get("reply"):
                reply = scrub(t["reply"], a.redact, "the model's reply", "--page")
                out.append(f'<h3>Reply</h3><pre class="said">{e(reply)}</pre>')
    if shown:
        out.append("<h2>Files</h2>")
        for f in shown:
            b, ext = f["body"], os.path.splitext(f["name"])[1].lower()
            head = f"{e(f['name'])} · {e(f['source'])}" + (f" · {size_text(len(b))}" if b is not None else "")
            if b is None:
                body = ""
            elif os.path.normpath(f["path"]) in inside:
                body = '<p class="dim">It plays in the page above.</p>'
            elif ext in IMAGE_TYPES or ext in AUDIO_TYPES or ext in VIDEO_TYPES:
                body = media(f, ext)
            elif not is_text(b) or len(b) > PAGE_TEXT_MAX:
                body = '<p class="dim">Not shown: too big, or not text.</p>'
            else:
                code = scrub(b.decode("utf-8", "replace"), a.redact, "the file " + f["name"], "--page")
                body = f"<pre><code>{e(code)}</code></pre>"
            out.append(f"<details open><summary>{head}</summary>{body}</details>")
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>What the run made · receipt no. {e(r.get("receipt_no", ""))}</title><style>'
        "body{font:16px/1.5 system-ui,sans-serif;margin:0;background:#f4f2ee;color:#222}"
        "main{max-width:960px;margin:auto;padding:16px}"
        ".paper{background:#fffdf8;border:1px solid #ddd;border-radius:4px;padding:18px 20px;overflow-x:auto}"
        "pre{font:13px/1.45 ui-monospace,monospace;margin:0;overflow-x:auto}"
        ".said{white-space:pre-wrap;background:#fff;border:1px solid #ddd;border-radius:4px;padding:10px 12px}"
        "details{background:#fff;border:1px solid #ddd;border-radius:4px;margin:10px 0}"
        "summary{cursor:pointer;padding:8px 12px;font-family:ui-monospace,monospace}"
        "details pre{padding:10px 12px;border-top:1px solid #eee}"
        "details img,details video{max-width:calc(100% - 20px);display:block;margin:10px}details audio{margin:10px}"
        "iframe{width:100%;height:70vh;border:1px solid #bbb;border-radius:4px;background:#fff}"
        ".dim{color:#555;font-size:.9em}"
        "</style></head><body><main><h1 class=own>What the run made</h1>"
        + "".join(out)
        + extra
        + f'<p class="dim">Made with <a href="{SITE}">receipt.py</a> {VERSION}. Home folders are shown as ~. '
        "Files written whole are shown as the run wrote them; files it edited or changed afterward, as they are on disk "
        "now.</p>"
        # shown inside the receipt site, which has the receipt above it already, the page leaves out its own copy
        "<script>if (window.top !== window.self) for (const x of document.querySelectorAll('.own')) x.hidden = true"
        "</script>"
        "</main></body></html>"
    )


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


def output_subject(path, written, ended, names, n, how_made=None):
    """-> an in-toto subject for a file the run wrote: the content the log holds, else the file as it is now"""
    ext = os.path.splitext(base_name(path))[1].lower()
    name = base_name(path) if names else f"file{n}{ext}"
    disk, body, later = None, None, False
    try:
        with open(path, "rb") as fh:
            body = fh.read()
        disk = sha(body)
        later = ended is not None and os.path.getmtime(path) > when(ended).timestamp() + 2
    except OSError:
        pass
    if written is not None and disk is not None and not later and disk != sha(written):
        digest, how, same = disk, "on disk; the run changed it after writing it", True
    elif written is not None:
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
            how_made or "on disk now" + ("; changed after the run" if later else ""),
            True,
        )
    else:
        return None, None
    subject = {
        "name": name,
        "digest": {"sha256": digest},
        "annotations": {"source": how},
    }
    return subject, {"name": name, "body": body, "path": path, "same_on_disk": same, "source": how}


def record_claude(path, part, names, counts):
    win, _ = claude_window(path, part)
    prompts, system, instructions, defs, seen, env = [], {}, {}, {}, [], {}
    uses, edits, failed, unsaved = {}, {}, set(), 0
    for d in claude_lines(path):
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
        if text:
            prompts.append(sha(text))
        elif text is not None:
            unsaved += 1
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
    if unsaved:
        limits.append("claude -p's output doesn't hold the prompt, so there is no fingerprint of it")
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


def record_qwen(path, part, names, counts):
    win, _ = qwen_window(path, part)
    prompts, seen, uses, pending, writes = [], [], {}, {}, {}
    for i, d in enumerate(lines(path)):
        if not within(i, win):
            continue
        text = qwen_prompt(d)
        if text is not None:
            prompts.append(sha(text))
        elif d.get("type") == "assistant":
            for cid, n, args in qwen_tool_calls(d):
                uses[cid] = n
                if n in QWEN_WRITES and args.get(QWEN_WRITES[n]):
                    whole = args.get("content") if n == "write_file" and isinstance(args.get("content"), str) else None
                    pending[cid] = (args[QWEN_WRITES[n]], whole)
        elif d.get("type") == "tool_result":
            res = d.get("toolCallResult") or {}
            failed = res.get("status") == "error" or bool(res.get("error"))
            for x in (d.get("message") or {}).get("parts") or []:
                fr = x.get("functionResponse") if isinstance(x, dict) else None
                if isinstance(fr, dict):  # what the model was shown
                    e = {"tool": uses.get(fr.get("id"), fr.get("name") or "?"), "sha256": sha(canon(fr.get("response")))}
                    if failed:
                        e["failed"] = True
                    seen.append(e)
            if not failed and res.get("callId") in pending:
                f, whole = pending[res["callId"]]
                writes[f] = whole
    rec = {"prompts": [{"sha256": h} for h in prompts], "tool_results": seen}
    return rec, writes, ["Qwen Code logs neither the system prompt nor tool definitions"]


def record_gemini(path, part, names, counts):
    msgs, cwd = gemini_messages(path), gemini_cwd(path)
    marks = [i for i, d in enumerate(msgs) if gemini_prompt(d) is not None] if part else []
    sel, _ = pick(len(marks), part)
    win = bounds(marks, sel)
    prompts, seen, writes = [], [], {}
    for i, d in enumerate(msgs):
        if not within(i, win):
            continue
        text = gemini_prompt(d)
        if text is not None:
            prompts.append(sha(text))
        for c in gemini_tool_calls(d):
            n, args = c.get("name") or "?", c.get("args") or {}
            if c.get("result") is not None:  # what the model was shown
                e = {"tool": n, "sha256": sha(canon(c["result"]))}
                if c.get("status") == "error":
                    e["failed"] = True
                seen.append(e)
            if c.get("status") == "success" and n in GEMINI_WRITES and args.get("file_path"):
                whole = args.get("content") if n == "write_file" and isinstance(args.get("content"), str) else None
                writes[os.path.join(cwd, args["file_path"])] = whole
    rec = {"prompts": [{"sha256": h} for h in prompts], "tool_results": seen}
    return rec, writes, ["Gemini CLI logs neither the system prompt nor tool definitions",
                         "a subagent's tool results aren't included"]  # fmt: skip


def record_copilot(path, part, names, counts):
    marks = [i for i, d in enumerate(lines(path)) if copilot_prompt(d) is not None] if part else []
    sel, _ = pick(len(marks), part)
    win = bounds(marks, sel)
    prompts, system, seen, uses, pending, writes = [], {}, [], {}, {}, {}
    for i, d in enumerate(lines(path)):
        t, x = d.get("type"), d.get("data") or {}
        if t == "system.message" and isinstance(x.get("content"), str):
            system.setdefault(sha(x["content"]), 1)
        if not within(i, win):
            continue
        text = copilot_prompt(d)
        if text is not None:
            prompts.append(sha(text))
        elif t == "assistant.message":
            for c in x.get("toolRequests") or []:
                n, args = c.get("name") or "?", c.get("arguments") or {}
                uses[c.get("toolCallId")] = n
                if n in COPILOT_WRITES and args.get("path"):
                    whole = args.get("file_text") if n == "create" and isinstance(args.get("file_text"), str) else None
                    pending[c.get("toolCallId")] = (args["path"], whole)
        elif t == "tool.execution_complete":
            res = x.get("result") or {}
            shown = res.get("content") if x.get("success") else (x.get("error") or {}).get("message")
            e = {"tool": uses.get(x.get("toolCallId"), "?"), "sha256": sha(content_text(shown or ""))}
            if not x.get("success"):
                e["failed"] = True
            seen.append(e)
            if x.get("success"):
                f, whole = pending.get(x.get("toolCallId"), (None, None))
                for fe in x.get("fileEdits") or []:
                    if fe.get("kind") != "delete" and fe.get("path"):
                        writes[fe["path"]] = whole if fe["path"] == f else None
                if not x.get("fileEdits") and f:
                    writes[f] = whole
    rec = {"prompts": [{"sha256": h} for h in prompts], "system_prompt": [{"sha256": h} for h in system],
           "tool_results": seen}  # fmt: skip
    return rec, writes, ["Copilot CLI logs no tool definitions"]


def record_exec(path, part, names, counts):
    """codex exec --json output: what its commands printed and the files it changed; the output holds no text
    of the files, so each is fingerprinted as it is on disk now"""
    seen, writes = [], {}
    for d in lines(path):
        it = d.get("item") or {}
        if d.get("type") != "item.completed":
            continue
        if it.get("type") == "command_execution":
            e = {"tool": "command_execution", "sha256": sha(it.get("aggregated_output") or "")}
            if it.get("exit_code") not in (0, None):
                e["failed"] = True
            seen.append(e)
        elif it.get("type") == "file_change":
            for c in it.get("changes") or []:
                if c.get("path") and c.get("kind") != "delete":
                    writes[c["path"]] = None
    return {"prompts": [], "tool_results": seen}, writes, [
        f"{EXEC_JSON} holds no prompt, system prompt, instruction files, model or times",
        "files are fingerprinted as they are on disk now: the output doesn't hold their text"]


def make_record(r, tool, key, part, names, counts, hide, renames, turns=()):
    rec, writes, limits = (record_exec if r.get("log_name") == EXEC_JSON else {
        "claude": record_claude,
        "codex": record_codex,
        "opencode": record_opencode,
        "qwen": record_qwen,
        "gemini": record_gemini,
        "copilot": record_copilot,
    }[tool])(key, part, names, counts)
    made = [
        output_subject(p, w, r["ended"], names, n)
        for n, (p, w) in enumerate(writes.items(), 1)
    ] + [output_subject(p, None, r["ended"], names, len(writes) + n, MADE_HOW) for n, p in enumerate(r.get("_made", []), 1)]
    subjects = [s for s, _ in made if s]
    r["_outputs"] = [b for _, b in made if b]  # the files themselves, for --bundle and --shot
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


class LocalServer(http.server.ThreadingHTTPServer):
    def server_bind(self):  # without the name lookup of 127.0.0.1 http.server does, which takes ~35 s on some Macs
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


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
    srv = LocalServer(
        ("127.0.0.1", 0), functools.partial(QuietFiles, directory=folder)
    )
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}/" + urllib.parse.quote(
        rel.replace(os.sep, "/")
    )
    try:
        return snap(b, url, png, tmp, "--shot")
    finally:
        srv.shutdown()
        srv.server_close()


def snap(b, url, png, tmp, who, size="1280,800", more=()):
    """-> a PNG of url, taken by browser b"""
    # --timeout stops a page still loading after 10 s, then the picture is taken. Not --virtual-time-budget:
    # on a page that draws 3D in a loop, without a GPU, using up that budget took over 90 s, or never ended
    cmd = [b, "--headless", "--disable-gpu", "--hide-scrollbars", f"--screenshot={png}",
           f"--window-size={size}", "--timeout=10000", *more, url]  # fmt: skip
    # what the browser says goes to a file, not a pipe: the helper processes it starts (a GPU process for a
    # WebGL page) keep a pipe open after the browser itself is done, so waiting for the pipe to close never ends
    said_path = os.path.join(tmp, "browser.txt")
    with open(said_path, "w", encoding="utf-8") as said_fh:
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=said_fh,
                                 start_new_session=os.name != "nt")  # fmt: skip
        except OSError as e:
            sys.exit(f"receipt: {who} couldn't start {b}: {e}")
        try:
            p.wait(timeout=60)
        except subprocess.TimeoutExpired:
            kill_tree(p)
            sys.exit(f"receipt: {who}: {b} took over 60 s and was stopped")
        kill_tree(p)  # the helpers it leaves behind
    with open(said_path, encoding="utf-8", errors="replace") as fh:
        said = fh.read()
    if not os.path.exists(png):
        sys.exit(f"receipt: {who}: {b} made no picture ({said.strip()[-300:]})")
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


def bundle(path, r, s, payload, record, outputs, a, rows=(), hide=()):
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
    made = {"outputs/" + o["name"] for o in outputs if o.get("source") == MADE_HOW}
    files["ro-crate-metadata.json"] = canon(crate(r, files, outs, made))
    files["ro-crate-preview.html"] = output_page(r, s, rows, outputs, a, hide, preview(files), "outputs/").encode("utf-8")
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
    "Qwen Code": "https://github.com/QwenLM/qwen-code",
    "Gemini CLI": "https://github.com/google-gemini/gemini-cli",
    "Copilot CLI": "https://github.com/github/copilot-cli",
}


CRATE_PARTS = {
    "receipt.txt": "the receipt, as receipt.py printed it",
    "receipt.json": "the receipt as JSON",
    "record.json": "an in-toto Statement: SHA-256 fingerprints of what went into the run and the files it wrote",
    "record.json.sig": "an SSH signature of record.json",
    "preview.png": "a screenshot of the page the run made, from the files in this bundle",
}


def crate(r, files, outs, made=()):
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
                          "description": CRATE_PARTS.get(f, f"a file {MADE_HOW}" if f in made else "a file the run wrote"),
                          "contentSize": str(len(files[f])),
                          "encodingFormat": mimetypes.guess_type(f)[0] or "application/octet-stream"})  # fmt: skip
    return {"@context": "https://w3id.org/ro/crate/1.2/context", "@graph": graph}


def preview(files):
    """-> the end of the bundle's page: what's in the zip, and how to check it"""
    links = "".join(
        f'<li><a href="{html.escape(f)}">{html.escape(f)}</a></li>'
        for f in sorted(files)
        if f != "ro-crate-preview.html"
    )
    img = (
        '<h2>A picture of the page</h2><p><img src="preview.png" alt="what the run made" style="max-width:100%"></p>'
        if "preview.png" in files
        else ""
    )
    return (
        f"{img}<h2>In this bundle</h2><ul>{links}</ul><p>Check the files against the record with "
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
    elif not r.get("models") and not r.get("replies"):
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


HOME_PATH = re.compile(  # also a WSL home as Windows names it: \\wsl.localhost\Ubuntu\home\me, \\wsl$\...
    r"(?:[\\/]{2,}wsl(?:\.localhost|\$)[\\/]+[^\\/\s]+[\\/]+home[\\/]+|/home/|/Users/|/mnt/[a-z]/Users/"
    r"|[A-Za-z]:\\+Users\\+|[A-Za-z]:/Users/)[^/\\\s'\"`]+",
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
    r.pop("made_names", None)


DROP = {
    "version": ["version"],
    "date": ["started", "ended"],
    "model": ["models", "background_models", "effort", "providers"],
    "time": ["started", "ended", "duration_ms", "model_time_ms", "prompts"],
    "cost": ["cost_usd", "cost_note"],
    "items": ["items", "prices", "cost_check", "extras"],
    "billing": ["billing", "plan_use"],
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
        "output_lines",
        "output_bytes",
        "web_page",
        "files_gone",
        "files_made",
        "made_types",
        "made_names",
        "made_bytes",
        "made_media",
        "made_note",
    ],
    "output": ["output_lines", "output_bytes", "web_page", "files_gone", "replies", "reply_words", "output_url",
               "output_sha256", "made_bytes", "made_media"],
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
        "files_written", "files_deleted", "output_lines", "output_bytes", "files_gone", "replies", "reply_words",
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
        if r["first_prompt"] and any(x.get("prompt_given") for x in rs):  # one said it in their own words
            r["prompt_given"] = True
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


# ---------- the status line, and how much of a plan's limits a run used ----------

# Claude Code tells a status-line command how full a Pro or Max plan's 5-hour and weekly limits are; its session
# logs don't record it. --statusline keeps each change, one small file per session, so a receipt can say later
# how far the limits moved while the run went on.
WINDOWS = {"five_hour": "5-hour", "seven_day": "weekly"}


def limits_dir():
    base = os.environ.get("XDG_CACHE_HOME") or (
        os.environ.get("LOCALAPPDATA") if os.name == "nt" else None
    ) or os.path.join(home(), ".cache")
    return os.path.join(base, "prompt-receipts", "limits")


def limits_file(sid):
    safe = re.sub(r"[^A-Za-z0-9_-]", "", str(sid or ""))[:80]
    return os.path.join(limits_dir(), safe + ".jsonl") if safe else None


def statusline(d):
    """-> the status line for Claude Code's status-line input d, after keeping its plan-limit reading"""
    rl = d.get("rate_limits") or {}
    now = {k: [rl[k].get("used_percentage"), rl[k].get("resets_at")] for k in WINDOWS
           if isinstance(rl.get(k), dict) and rl[k].get("used_percentage") is not None}  # fmt: skip
    f = limits_file(d.get("session_id"))
    seen = readings(f) if f else []
    if f and now and (not seen or {k: seen[-1].get(k) for k in WINDOWS} != {k: now.get(k) for k in WINDOWS}):
        os.makedirs(os.path.dirname(f), exist_ok=True)
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"t": datetime.datetime.now(datetime.timezone.utc).isoformat(), **now}) + "\n")
        seen.append({"t": None, **now})
    parts = [(d.get("model") or {}).get("display_name") or (d.get("model") or {}).get("id") or "?"]
    cost = d.get("cost") or {}
    if cost.get("total_cost_usd") is not None:
        parts.append(money(cost["total_cost_usd"]))
    if cost.get("total_duration_ms"):
        parts.append(mins(cost["total_duration_ms"]))
    used = moved(seen)
    for k, name in WINDOWS.items():
        if k in now:
            mine = f" (+{used[k]:.0f}% this session)" if used.get(k, 0) >= 0.5 else ""
            parts.append(f"{name} {now[k][0]:.0f}%{mine}")
    return " · ".join(parts)


def readings(f, start=None, end=None):
    """-> the kept plan-limit readings in a file, oldest first. With start and end (datetimes): the last one
    before start, as where the run began from, then those up to a minute after end, since the status line
    runs just after each reply is logged"""
    out = []
    try:
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    x = json.loads(line)
                    at = when(x["t"]) if start else None
                except (ValueError, KeyError, TypeError, AttributeError):
                    continue
                if start and at <= start:
                    out[:] = [x]
                elif not start or at <= end + datetime.timedelta(minutes=1):
                    out.append(x)
    except OSError:
        pass
    return out


def moved(rs):
    """-> {window: percentage points the limit went up across these readings}; a new window starts from 0"""
    up = {}
    for k in WINDOWS:
        prev = None
        for x in rs:
            if not x.get(k):
                continue
            used, resets = x[k]
            if prev is None:
                up.setdefault(k, 0.0)
            elif resets != prev[1]:
                up[k] += used  # the window reset while the run went on: all of the new one's use is since then
            else:
                up[k] += max(used - prev[0], 0)
            prev = (used, resets)
    return up


def plan_use(sid, started, ended):
    """-> what the plan limits did while this run went on, from the status line's readings; None without any"""
    f = limits_file(sid)
    if not f or not started:
        return None
    rs = readings(f, when(started), when(ended or started))
    if len(rs) < 2:
        return None
    up = moved(rs)
    return {WINDOWS[k]: round(v, 1) for k, v in up.items()}


# ---------- totals over time ----------

BY = ["day", "week", "month", "folder", "model"]
NO_CALL = "(no model call)"  # a prompt stopped before the model answered, or a slash command


def totals(tool, keys, by, since, until):
    """-> {bucket: sums} over every prompt in these sessions sent between since and until (local dates)"""
    turns_of = TURNS[tool]
    out, priced = {}, True
    for key in keys:
        folder = base_name(folder_of(tool, key)) or "?"
        for t in turns_of(key):
            if not t["started"]:
                continue
            day = when(t["started"]).date()
            if (since and day < since) or (until and day > until):
                continue
            priced = priced and "cost_usd" in t
            main_model = re.sub(r"\[.*\]$", "", t["model"] or NO_CALL)
            if by == "model":
                split = t["_models"] or {main_model: [0.0, 0, 0]}
            else:
                cost, tin, tout = (sum(m[i] for m in t["_models"].values()) for i in range(3))
                split = {bucket_of(by, day, folder): [t.get("cost_usd", cost), tin, tout]}
            lead = main_model if by == "model" and main_model in split else next(iter(split))
            for b, (usd, tin, tout) in split.items():
                row = out.setdefault(b, {"cost_usd": 0.0, "sessions": set(), "prompts": 0, "time_ms": 0,
                                         "tokens_in": 0, "tokens_out": 0, "first": day, "last": day})  # fmt: skip
                row["cost_usd"] += usd
                row["tokens_in"] += tin
                row["tokens_out"] += tout
                row["sessions"].add(key)
                row["first"], row["last"] = min(row["first"], day), max(row["last"], day)
                if b == lead:  # a prompt, and its time, count once: for the model that answered it
                    row["prompts"] += 1
                    row["time_ms"] += t["time_ms"]
    return out, priced


def bucket_of(by, day, folder):
    if by == "day":
        return day.isoformat()
    if by == "week":
        return (day - datetime.timedelta(days=day.weekday())).isoformat()
    if by == "month":
        return day.strftime("%Y-%m")
    return folder


def bucket_label(by, key):
    if by in ("folder", "model"):
        return key
    if by == "month":
        d = datetime.date.fromisoformat(key + "-01")
        return f"{d:%b %Y}"
    d = datetime.date.fromisoformat(key)
    return ("week of " if by == "week" else f"{d:%a} ") + f"{d.day} {d:%b %Y}"


def date_text(a, b):
    if a == b:
        return f"{a.day} {a:%b %Y}"
    start = f"{a.day}" if (a.year, a.month) == (b.year, b.month) else f"{a.day} {a:%b}" if a.year == b.year else f"{a.day} {a:%b %Y}"
    return f"{start} – {b.day} {b:%b %Y}"


def totals_text(tool, scope, by, rows, priced, hide, billing, since, until):
    """-> (the printed table, its JSON form)"""
    order = (
        sorted(rows, key=lambda k: -rows[k]["cost_usd"])
        if by in ("folder", "model") and priced
        else sorted(rows)
    )
    cols = [("cost", "cost", "cost_usd"), ("sessions", None, "sessions"), ("prompts", None, "prompts"),
            ("time", "time", "time_ms"), ("tokens in / out", "tokens", "tokens_in")]  # fmt: skip
    cols = [c for c in cols if c[1] not in hide and not (c[0] == "cost" and not priced)]

    def cells(r):
        out = []
        for name, _, key in cols:
            if key == "cost_usd":
                out.append(money(r["cost_usd"]))
            elif key == "sessions":
                out.append(str(len(r["sessions"]) if isinstance(r["sessions"], set) else r["sessions"]))
            elif key == "time_ms":
                out.append(mins(r["time_ms"]) if r["time_ms"] else "-")
            elif key == "tokens_in":
                out.append(f"{toks(r['tokens_in'])} / {toks(r['tokens_out'])}")
            else:
                out.append(str(r[key]))
        return out

    every = [k for r in rows.values() for k in r["sessions"]]
    total = {k: sum(r[k] for r in rows.values()) for k in ("cost_usd", "prompts", "time_ms", "tokens_in", "tokens_out")}
    total["sessions"] = len(set(every))
    grid = [[by] + [c[0] for c in cols]]
    grid += [[bucket_label(by, k)] + cells(rows[k]) for k in order]
    grid += [["total"] + cells(total)]
    width = [max(len(line[i]) for line in grid) for i in range(len(grid[0]))]
    first = since or min((r["first"] for r in rows.values()), default=None)
    last = until or max((r["last"] for r in rows.values()), default=None)
    head = ["Totals"] + ([f"v{VERSION}"] if "version" not in hide else [])
    head = [" ".join(head), TOOLS[tool], scope]
    if first and "date" not in hide:
        head.append(date_text(first, last))
    head.append(f"by {by}")
    out = [" · ".join(head)]
    for i, line in enumerate(grid):
        out.append("  ".join(c.ljust(w) if j == 0 else c.rjust(w) for j, (c, w) in enumerate(zip(line, width))).rstrip())
        if i == len(grid) - 2:
            out.append("-" * len(out[-1]))
    if priced and "cost" not in hide:
        out.append(labelled("prices   ", f"API list prices for each prompt's calls (subagents included), from {PRICES_FROM}", 80))
        if tool == "claude":
            out.append(labelled("note     ", "background work Claude Code prices itself (titles, summaries) belongs to no prompt, so it isn't counted", 80))
    if not priced and "cost" not in hide:
        out.append(labelled("note     ", "no cost: some of these runs were on local models, or the tool gave no token counts", 80))
    if billing and "billing" not in hide:
        out.append(labelled("billing  ", billing, 80))
    payload = {"receipt_version": VERSION, "kind": "totals", "tool": TOOLS[tool], "scope": scope, "by": by,
               "from": first.isoformat() if first else None, "to": last.isoformat() if last else None,
               "rows": [], "total": None}  # fmt: skip
    keep = {c[2] for c in cols} | ({"tokens_out"} if "tokens_in" in {c[2] for c in cols} else set())
    for k, r in [(k, rows[k]) for k in order] + [("total", total)]:
        j = {"bucket": k}
        for key in ("cost_usd", "sessions", "prompts", "time_ms", "tokens_in", "tokens_out"):
            if key in keep:
                v = r[key]
                j[key] = len(v) if isinstance(v, set) else round(v, 6) if isinstance(v, float) else v
        if k == "total":
            payload["total"] = j
        else:
            payload["rows"].append(j)
    if "date" in hide:
        payload["from"] = payload["to"] = None
    if "version" in hide:
        payload.pop("receipt_version")
    return "\n".join(out), payload


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
        head = f"{head} {r['version']}".replace("·  ", "· ").rstrip()
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
        named = f" (the sender's word, with --model: not in {r['log_name']})" if r.get("model_given") else ""
        none = f"not in {r['log_name']}" if r.get("log_name") == EXEC_JSON else "no model reply in this log"
        out.append(
            f"model    {', '.join(r['models']) or none}{named}{via}{bg} · effort {r['effort']}"
        )
    if "time" not in hide:
        took = mins(r["duration_ms"]) if r.get("duration_ms") is not None else f"not in {r.get('log_name') or 'the log'}"
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
    if "billing" not in hide and r.get("plan_use"):
        said = ", ".join(f"{k} +{v:g}%" for k, v in r["plan_use"].items())
        out.append(labelled("limits   ", f"{said} while this ran, from the status line's readings; other sessions "
                            "running at the same time count too", width))  # fmt: skip
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
        if r.get("output_bytes") and "output" not in hide:
            n_lines = r.get("output_lines")
            line += " · " + (f"{n_lines:,} line{'' if n_lines == 1 else 's'}, " if n_lines else "") + size_text(
                r["output_bytes"]
            )
        if r.get("web_page") and "output" not in hide:
            line += " · a web page"
        if r.get("files_gone") and "output" not in hide:
            line += f" · {r['files_gone']} not on disk now"
        if r.get("files_deleted"):
            line += f" · {r['files_deleted']} deleted"
        if r.get("files_note"):
            line += f" · {r['files_note']}"
        out.append(line)
    if "files" not in hide and r.get("files_made") is not None:
        n = r["files_made"]
        if r.get("made_names"):
            fn = r["made_names"][:12]
            what = ", ".join(fn) + (f" and {n - len(fn)} more" if n > len(fn) else "")
        else:
            what = names(r.get("made_types"))
        line = f"made     {many(n, 'file')} changed in its folder while it ran" + (f" ({what})" if n else "")
        if r.get("made_bytes") and "output" not in hide:
            line += " · " + size_text(r["made_bytes"])
        if r.get("made_media") and "output" not in hide:
            line += " · " + media_text(r["made_media"])
        if r.get("made_note"):
            line += f" · {r['made_note']}"
        out.append(line)
    if r.get("output_url") and "output" not in hide:  # the site's receipt page fetches it and checks this
        out.append(f"page     {r['output_url']} · sha256 {r['output_sha256'][:16]}")
    if r.get("replies") is not None and "output" not in hide:
        n, w = r["replies"], r["reply_words"]
        out.append(f"replies  {n} {'reply' if n == 1 else 'replies'}, {w:,} word{'' if w == 1 else 's'}")
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
            out.append(f"hooks    not in {r.get('log_name') or (r['tool'] or 'these') + ' logs'}")
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
            f"not in {r.get('log_name') or (r['tool'] or 'these') + ' logs'}"
            if m is None
            else (f"{m} file{'s' if m != 1 else ''}" if m else "none loaded")
            if isinstance(m, int)
            else (", ".join(m) or "none loaded")
        )
        out.append(f"memory   {m}")
    if "settings" not in hide:
        out.append(f"settings {r['permissions'] if r.get('permissions') is not None else 'not in ' + (r.get('log_name') or 'the log')}")
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
        if r.get("prompt_given"):
            out.append(labelled("given    ", f"by the sender with --asked: {r.get('log_name') or 'the log'} doesn't "
                                "hold the prompt", width))  # fmt: skip
    elif with_prompt and r.get("prompts_unsaved") and not r.get("prompt_texts"):
        out.append(f"prompt   not in {r.get('log_name') or 'the log'}")
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


REPORT_KEYS = ("post", "by", "date", "tool", "model", "effort", "time", "cost", "tokens in", "tokens cached",
               "tokens out", "made", "prompt")  # fmt: skip
REPORT_NOTE = "from a post, not read from a log: what it says, unchecked; no receipt number or record"


def read_report(path, redact):
    """--reported FILE: what a post says about a run, as `key: value` lines; the prompt runs on to the next key"""
    try:
        if path == "-":
            body = sys.stdin.read()
        else:
            with open(os.path.expanduser(path), encoding="utf-8") as fh:
                body = fh.read()
    except (OSError, UnicodeDecodeError) as e:
        sys.exit(f"receipt: can't read --reported {path} ({getattr(e, 'strerror', None) or e})")
    got, key = {}, None
    for n, line in enumerate(body.splitlines(), 1):
        m = re.match(r"\s*([A-Za-z][A-Za-z ]*?)\s*:\s?(.*)$", line)
        k = m.group(1).lower() if m else None
        if k in REPORT_KEYS:
            if k in got:
                sys.exit(f"receipt: --reported {path} says {k} twice (line {n})")
            got[k], key = m.group(2).strip(), k
        elif key == "prompt":
            got["prompt"] += "\n" + line
        elif line.strip() and not line.lstrip().startswith("#"):
            sys.exit(f"receipt: --reported {path} line {n} isn't one of {', '.join(REPORT_KEYS)} and a colon: "
                     f"{line.strip()[:40]!r}")  # fmt: skip
    got = {k: v.strip() for k, v in got.items() if v.strip()}
    if not re.fullmatch(r"https?://\S+", got.get("post", "")):
        sys.exit(f"receipt: --reported {path} needs a post: line with the post's https:// address, so anyone can "
                 "read what it says")  # fmt: skip

    def number(k):
        v = got.get(k)
        if v is None:
            return None
        m = re.fullmatch(r"([\d,]*\.?\d+)([kKmM]?)", v.replace(" ", ""))
        if not m:
            sys.exit(f"receipt: --reported {path}: {k} needs a number like 1.2M, 40k or 40,000, not {v!r}")
        return round(float(m.group(1).replace(",", "")) * {"": 1, "k": 1e3, "m": 1e6}[m.group(2).lower()])

    cost = None
    if "cost" in got:
        m = re.fullmatch(r"(?:US)?\$?\s*([\d,]*\.?\d+)\s*(?:USD|dollars)?", got["cost"], re.I)
        if not m:
            sys.exit(f"receipt: --reported {path}: cost needs a dollar figure like $4.10, not {got['cost']!r}")
        cost = float(m.group(1).replace(",", ""))
    tin, tc, tout = number("tokens in"), number("tokens cached"), number("tokens out")
    if tc is not None and (tin is None or tc > tin):
        sys.exit(f"receipt: --reported {path}: tokens cached is part of tokens in, so it can't be more, or given "
                 "without it")  # fmt: skip
    for k in ("by", "date", "tool", "model", "effort", "time", "made", "prompt"):
        if k in got:
            got[k] = scrub(got[k], redact, "the post's prompt" if k == "prompt" else f"its {k} line",
                           f"its {k} line")  # fmt: skip
    r = {"reported": True, "receipt_version": VERSION, "tool": got.get("tool", ""), "post": got["post"],
         "by": got.get("by"), "posted": got.get("date"), "models": [got["model"]] if "model" in got else [],
         "effort": got.get("effort"), "time": got.get("time"), "made": got.get("made"),
         "first_prompt": got.get("prompt"), "tokens_in": tin, "tokens_cached": tc, "tokens_out": tout}  # fmt: skip
    if r["models"] and (tin or tout):
        bill = Bill()
        codex_call(bill, r["models"][0], {"input_tokens": tin or 0, "cached_input_tokens": tc or 0,
                                          "output_tokens": tout or 0}, summed=True)  # fmt: skip
        if bill.lines:
            r["api_usd"], r["prices"] = round(bill.total(), 6), PRICES_FROM
            # a floor: a post rarely says which input tokens were cache writes, or how big each call was
            row, long = rates_for(r["models"][0]), long_from(r["models"][0])
            more = [why for why, dearer in (
                ("some were cache writes", max(row[2:4]) > row[0] and (tin or 0) > (tc or 0)),
                (f"one call went past {(long or 0) // 1000}k tokens", long and (tin or 0) > long)) if dearer]  # fmt: skip
            r["api_note"] = "at API prices for the model and tokens it states" + ("; more if " + " or ".join(more) if more else "")
    if cost is not None:
        r["cost_usd"], r["cost_note"] = cost, "the post's own figure"
    elif r.get("api_usd") is not None:
        r["cost_usd"], r["cost_note"] = r["api_usd"], "the post states no cost: " + r["api_note"]
    return r


def reported_text(r, width=80):
    """a reported receipt: what the post says, line by line, and "not stated" for what it doesn't"""
    head = f"Reported v{VERSION} · {r['tool'] or 'tool not stated'}" + (f" · {r['posted']}" if r.get("posted") else "")
    out = [head, labelled("REPORTED ", REPORT_NOTE, width)]
    out.append(labelled("post     ", r["post"] + (f" · by {r['by']}" if r.get("by") else ""), width))
    model = ", ".join(r["models"]) or "not stated"
    out.append(f"model    {model}" + (f" · effort {r.get('effort') or 'not stated'}" if r["models"] or r.get("effort") else ""))
    out.append(f"time     {r.get('time') or 'not stated'}")
    if r.get("cost_note") == "the post's own figure":
        out.append(f"cost     {money(r['cost_usd'])} (the post's own figure)")
        if r.get("api_usd") is not None:
            out.append(labelled(" " * 9, f"{money(r['api_usd'])} {r['api_note']}", width))
    elif r.get("cost_usd") is not None:
        out.append(labelled("cost     ", f"{money(r['cost_usd'])} ({r['cost_note']})", width))
    else:
        out.append("cost     not stated")
    tin, tc, tout = r["tokens_in"], r["tokens_cached"], r["tokens_out"]
    if tin is None and tout is None:
        out.append("tokens   not stated")
    else:
        said = f"in {toks(tin)}" + (f" ({toks(tc)} cached)" if tc is not None else "") if tin is not None else "in not stated"
        out.append(f"tokens   {said} · out {toks(tout) if tout is not None else 'not stated'}")
    out.append(labelled("made     ", r.get("made") or "not stated", width))
    out.append(labelled("prompt   ", r.get("first_prompt") or "not stated", width))
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
        # Claude Code prices some background work itself (titles, summaries) with no calls in the log to tie
        # to a prompt: an "own figure" line that no turn can hold
        own = sum(i["usd"] for i in r.get("items") or [] if i["kind"] == "own figure")
        if abs(total - r["cost_usd"]) < 0.005:
            note = "the turns add up to the cost above"
        elif own and any(
            abs(total + own - x) < 0.005
            for x in (r["cost_usd"], chk.get("lines_usd", -1))
        ):
            note = (f"the turns add up to {money(total)}; the other {money(own)} is background work "
                    "the tool priced itself, not tied to one prompt")  # fmt: skip
        elif chk and abs(total - chk["lines_usd"]) < 0.005:
            note = f"the turns add up to {money(total)}, as the priced lines do"
        else:
            note = f"the turns add up to {money(total)}, priced from the logged calls"
        out.append(labelled(" " * 9, note, width))
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
    "'": bytes.fromhex("18180c0000000000"),  # font8x8's sits at its cell's left edge: "doesn't" read "doesn' t"
    "·": bytes.fromhex("0000001818000000"),
    "→": bytes.fromhex("0010307f7f301000"),
    "×": bytes.fromhex("00663c183c660000"),
    "…": bytes.fromhex("000000000000db00"),
}
SAME = {"—": "-", "–": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "\t": " "}


def glyph(ch):
    if ch in FONT_EXTRA:
        return FONT_EXTRA[ch]
    if " " <= ch <= "~":
        o = (ord(ch) - 32) * 8
        return FONT[o : o + 8]
    plain = (
        SAME.get(ch)
        or unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode()[:1]
    )
    return glyph(plain) if plain else glyph("?")


THEMES = {  # --theme: paper, ink, what shows past the torn ends, faint ink
    "paper": ((251, 248, 240), (38, 34, 30), (44, 49, 61), (100, 93, 85)),
    "night": ((30, 32, 40), (236, 232, 222), (96, 100, 114), (146, 148, 160)),
    "terminal": ((10, 22, 12), (124, 252, 140), (80, 110, 84), (70, 150, 84)),
    "blueprint": ((24, 66, 126), (238, 244, 255), (196, 210, 228), (150, 186, 232)),
    "pink": ((255, 230, 238), (122, 22, 64), (64, 22, 42), (160, 80, 115)),
}
INKS = THEMES["paper"]  # main() sets it from --theme

# Code 128: the bar and space widths of each value, in modules; set B starts with 104 and holds space to ~
CODE128 = (
    "212222 222122 222221 121223 121322 131222 122213 122312 132212 221213 221312 231212 112232 122132 122231 "
    "113222 123122 123221 223211 221132 221231 213212 223112 312131 311222 321122 321221 312212 322112 322211 "
    "212123 212321 232121 111323 131123 131321 112313 132113 132311 211313 231113 231311 112133 112331 132131 "
    "113123 113321 133121 313121 211331 231131 213113 213311 213131 311123 311321 331121 312113 312311 332111 "
    "314111 221411 431111 111224 111422 121124 121421 141122 141221 112214 112412 122114 122411 142112 142211 "
    "241211 221114 413111 241112 134111 111242 121142 121241 114212 124112 124211 411212 421112 421211 212141 "
    "214121 412121 111143 111341 131141 114113 114311 411113 411311 113141 114131 311141 411131 211412 211214 "
    "211232"
).split()


def code128(t):
    """-> the widths of a Code 128 barcode of t (set B: start, its characters, a check, stop), bar first"""
    vals = [104] + [ord(c) - 32 for c in t]
    check = (104 + sum(i * v for i, v in enumerate(vals[1:], 1))) % 103
    return [int(d) for d in "".join(CODE128[v] for v in vals + [check]) + "2331112"]


def letters(img, x, y, line, size, fg=1, bg=0, cache=None):
    """draw line at (x, y) with each dot of the 8x8 font size pixels a side"""
    cache = {} if cache is None else cache
    for gy in range(8):
        row = bytearray()
        for ch in line:
            key = (ch, gy, size, fg, bg)
            if key not in cache:
                bits = glyph(ch)[gy]
                cache[key] = bytes(fg if bits >> gx & 1 else bg for gx in range(8) for _ in range(size))
            row += cache[key]
        for sy in range(size):
            img[y + gy * size + sy][x : x + len(row)] = row


def bars(img, y, t, unit, tall):
    """a Code 128 barcode of t, centred, each module unit pixels wide; False if t can't be one"""
    if not t or not all(" " <= c <= "~" for c in t):
        return False
    widths = code128(t)
    x = (len(img[0]) - sum(widths) * unit) // 2
    bar = 1
    if dark_paper():  # scanners read dark bars on light: on dark paper, a plate of ink with paper-coloured bars
        quiet = 10 * unit
        for yy in range(y - 2 * unit, y + tall + 2 * unit):
            img[yy][x - quiet : x + sum(widths) * unit + quiet] = b"\x01" * (sum(widths) * unit + 2 * quiet)
        bar = 0
    for i, n in enumerate(widths):
        if i % 2 == 0:
            for yy in range(y, y + tall):
                img[yy][x : x + n * unit] = bytes([bar]) * (n * unit)
        x += n * unit
    return True


def dark_paper():
    """is --theme's paper darker than its ink?"""
    return sum(INKS[0]) < sum(INKS[1])


def torn(img, tooth):
    """torn paper at both ends: a zigzag of what's behind it"""
    h = len(img)
    for x in range(len(img[0])):
        d = abs(x % (2 * tooth) - tooth)
        for y in range(d):
            img[y][x] = 2
            img[h - 1 - y][x] = 2


def png_chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def encode(img, pics=()):
    """rows of ink numbers (into INKS), with pictures (x, y, (width, height, RGB rows)) laid on them -> PNG bytes:
    four colours, unless a picture needs every colour"""
    w, h = len(img[0]), len(img)
    palette = b"".join(bytes(c) for c in INKS)
    if not pics:
        raw = b"".join(b"\x00" + bytes(r) for r in img)
        return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 3, 0, 0, 0))
                + png_chunk(b"PLTE", palette) + png_chunk(b"IDAT", zlib.compress(raw, 9)) + png_chunk(b"IEND", b""))  # fmt: skip
    rgb = [palette[i * 3 : i * 3 + 3] for i in range(4)]
    lines = [bytearray(b"".join(rgb[i] for i in r)) for r in img]
    for x0, y0, (pw, ph, prows) in pics:
        for y, prow in enumerate(prows):
            lines[y0 + y][x0 * 3 : (x0 + pw) * 3] = prow
    return rgb_png(w, h, lines)


def rgb_png(w, h, rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + png_chunk(b"IDAT", zlib.compress(raw, 9)) + png_chunk(b"IEND", b""))  # fmt: skip


def with_alt(data, alt):
    """put alt text into a PNG, as an iTXt Description before its pixels, for programs that read it out"""
    pos = 8
    while data[pos + 4 : pos + 8] not in (b"IDAT", b"IEND"):
        pos += 12 + struct.unpack(">I", data[pos : pos + 4])[0]
    return data[:pos] + png_chunk(b"iTXt", b"Description\0\0\0\0\0" + alt.encode("utf-8")) + data[pos:]


def png(rows, scale=2, pic=None):
    """rows: [(text, style)] -> PNG bytes; a paper strip with torn ends, in --theme's inks. Styles: 1 dark, 3 faint,
    4 dark at twice the size, 5 paper-coloured on a dark tag, 6 a barcode of the text.
    pic: (width, height, RGB rows) of a picture, drawn framed where a (None, 0) row is"""
    cw, lh, pad, tooth = 8 * scale, 12 * scale, 20 * scale, 5 * scale
    cols = max(len(t) * (2 if ink == 4 else 1) for t, ink in rows if t is not None and ink != 6)
    w = cols * cw + 2 * pad
    margin = 4 * scale
    if pic:
        pic = shrink(*pic, w - 2 * pad - 4)
    heights = [pic[1] + 3 * margin if t is None else 2 * lh if ink == 4 else 4 * lh if ink == 6 else lh
               for t, ink in rows]  # fmt: skip
    h = sum(heights) + 2 * pad + 2 * tooth
    img = [bytearray(w) for _ in range(h)]
    cache, pics = {}, []
    y0 = tooth + pad
    for (line, ink), height in zip(rows, heights):
        y, y0 = y0, y0 + height
        if line is None:
            pw, ph, _ = pic
            x0, at = (w - pw) // 2, y + margin
            for yy in range(at - 2, at + ph + 2):  # a thin dark frame
                img[yy][x0 - 2 : x0 + pw + 2] = b"\x01" * (pw + 4)
            pics.append((x0, at, pic))
        elif ink == 6:
            bars(img, y + lh, line, scale, 2 * lh)
        elif ink == 5:
            for yy in range(y - scale * 2, y + scale * 10):
                img[yy][pad - scale * 3 : pad + len(line) * cw + scale * 3] = b"\x01" * (len(line) * cw + scale * 6)
            letters(img, pad, y, line, scale, 0, 1, cache)
        else:
            letters(img, pad, y, line, scale * (2 if ink == 4 else 1), 3 if ink == 3 else 1, 0, cache)
    torn(img, tooth)
    return encode(img, pics)


def pixels(data, what):
    """PNG bytes -> (width, height, RGB rows), see-through parts laid on the receipt's paper. Reads the PNGs
    browsers and most programs save (8 or 16 bits a channel, not interlaced); stops with a message on others"""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        sys.exit(f"receipt: {what} isn't a PNG; save it as one (a screenshot tool's PNG works)")
    pos, idat, plte, trns = 8, [], b"", b""
    w = h = depth = kind = lace = None
    while pos + 8 <= len(data):
        n, tag = struct.unpack(">I4s", data[pos : pos + 8])
        body = data[pos + 8 : pos + 8 + n]
        if tag == b"IHDR":
            w, h, depth, kind, _, _, lace = struct.unpack(">IIBBBBB", body)
        elif tag == b"PLTE":
            plte = body
        elif tag == b"tRNS":
            trns = body
        elif tag == b"IDAT":
            idat.append(body)
        elif tag == b"IEND":
            break
        pos += 12 + n
    if depth not in (8, 16) or (kind == 3 and depth != 8) or lace or kind not in (0, 2, 3, 4, 6):
        sys.exit(f"receipt: {what} is a kind of PNG receipt.py can't read (it reads 8 or 16 bits a channel, not "
                 "interlaced); save it again as an ordinary PNG")  # fmt: skip
    try:
        raw = zlib.decompress(b"".join(idat))
    except zlib.error as e:
        sys.exit(f"receipt: {what} is damaged ({e})")
    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[kind]  # samples a pixel
    bpp = ch * depth // 8  # bytes a pixel, which the row filters work in
    stride = w * bpp
    if len(raw) < h * (stride + 1):
        sys.exit(f"receipt: {what} is cut short")
    paper = INKS[0]
    prev, rows = bytearray(stride), []
    for y in range(h):
        f, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1 : (y + 1) * (stride + 1)])
        if f == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif f == 2:
            line = bytearray((a + b) & 255 for a, b in zip(line, prev))
        elif f == 3:
            for i in range(stride):
                line[i] = (line[i] + ((line[i - bpp] if i >= bpp else 0) + prev[i]) // 2) & 255
        elif f == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b, c = prev[i], prev[i - bpp] if i >= bpp else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        elif f:
            sys.exit(f"receipt: {what} is damaged (row filter {f})")
        prev = line
        if depth == 16:  # the high byte of each sample is plenty for a picture on a receipt
            line = line[0::2]
        if kind == 2:
            rows.append(bytes(line))
            continue
        out = bytearray()
        for x in range(w):
            if kind == 3:
                i = line[x]
                px = plte[i * 3 : i * 3 + 3] or b"\0\0\0"
                alpha = trns[i] if i < len(trns) else 255
            elif kind in (0, 4):
                px, alpha = bytes([line[x * ch]] * 3), (line[x * ch + 1] if kind == 4 else 255)
            else:
                px, alpha = line[x * 4 : x * 4 + 3], line[x * 4 + 3]
            out += bytes((v * alpha + q * (255 - alpha)) // 255 for v, q in zip(px, paper))
        rows.append(bytes(out))
    return w, h, rows


def shrink(w, h, rows, most, most_tall=None):
    """make a picture fit a square `most` pixels a side (a tall one would make a receipt metres long), or a box
    most × most_tall, each new pixel the average of the ones it covers"""
    most_tall = most if most_tall is None else most_tall
    if w <= most and h <= most_tall:
        return w, h, rows
    k = min(most / w, most_tall / h)
    nw, nh = max(1, round(w * k)), max(1, round(h * k))
    xs = [(x * w // nw, max(x * w // nw + 1, (x + 1) * w // nw)) for x in range(nw)]
    out = []
    for y in range(nh):
        y_a, y_b = y * h // nh, max(y * h // nh + 1, (y + 1) * h // nh)
        acc = [0] * (w * 3)
        for row in rows[y_a:y_b]:
            acc = [s + v for s, v in zip(acc, row)]
        line = bytearray()
        for x_a, x_b in xs:
            n = (x_b - x_a) * (y_b - y_a)
            line += bytes(sum(acc[x_a * 3 + c : x_b * 3 : 3]) // n for c in range(3))
        out.append(bytes(line))
    return nw, nh, out


MAGMA = [(0, 0, 4), (28, 16, 68), (79, 18, 123), (129, 37, 129), (181, 54, 122), (229, 80, 100),
         (251, 135, 97), (254, 194, 135), (252, 253, 191)]  # quiet to loud, as spectrograms are often coloured


def sound(data, what, wide=960, tall=240):
    """WAV bytes -> (its spectrogram as (width, height, RGB rows), a line saying how to read it): time left to
    right, pitch (on the mel scale, as ears hear it) bottom to top, loudness as colour, the loudest part
    brightest. Reads the WAVs most programs save (whole-number samples of 8 to 32 bits, or 32- or 64-bit
    floats); stops with a message on others. Only the stretches each column needs are read, so a long file
    takes no longer than a short one"""
    if data[:4] in (b"RF64", b"BW64", b"RIFX") and data[8:12] == b"WAVE":
        sys.exit(f"receipt: {what} is a kind of WAV receipt.py can't read ({data[:4].decode()}); "
                 "save it again as an ordinary WAV")  # fmt: skip
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        sys.exit(f"receipt: {what} isn't a WAV")
    pos, fmt, body = 12, None, None
    while pos + 8 <= len(data):
        tag, n = struct.unpack("<4sI", data[pos : pos + 8])
        if tag == b"fmt ":
            fmt = data[pos + 8 : pos + 8 + n]
        elif tag == b"data":
            body = data[pos + 8 : pos + 8 + n]
        pos += 8 + n + (n & 1)
    if fmt is None or body is None or len(fmt) < 16:
        sys.exit(f"receipt: {what} is damaged (no {'fmt' if fmt is None or len(fmt) < 16 else 'data'} part)")
    code, ch, rate, _, align, bits = struct.unpack("<HHIIHH", fmt[:16])
    if code == 0xFFFE and len(fmt) >= 26:  # WAVE_FORMAT_EXTENSIBLE: the kind is in its sub-format
        code = struct.unpack("<H", fmt[24:26])[0]
    size = align // ch if ch else 0  # bytes a sample takes, whatever its bits
    kind = {(1, 1): "B", (1, 2): "h", (1, 3): "i", (1, 4): "i", (3, 4): "f", (3, 8): "d"}.get((code, size))
    if not kind or rate < 1 or align != size * ch:
        sys.exit(f"receipt: {what} is a kind of WAV receipt.py can't read (it reads whole-number samples of 8 "
                 "to 32 bits and 32- or 64-bit floats); save it again as an ordinary WAV")  # fmt: skip
    frames = len(body) // align
    if not frames:
        sys.exit(f"receipt: {what} has no sound in it")
    scale = {"B": 1 / 128, "h": 1 / 32768, "i": 1 / 2**31, "f": 1.0, "d": 1.0}[kind] / ch
    n = 1024  # samples a column hears
    hann = [0.5 - 0.5 * math.cos(2 * math.pi * i / n) for i in range(n)]

    def heard(start):  # n samples from frame `start`, the channels mixed into one, silence outside the file
        lo, hi = max(start, 0), min(start + n, frames)
        if lo >= hi:
            return [0.0] * n
        raw = body[lo * align : hi * align]
        if size == 3:  # 24-bit: shifted into 32, low byte empty
            wide4 = bytearray(len(raw) // 3 * 4)
            for k in range(3):
                wide4[k + 1 :: 4] = raw[k::3]
            raw = bytes(wide4)
        v = array.array(kind, raw)
        if sys.byteorder == "big" and v.itemsize > 1:
            v.byteswap()
        if kind == "B":
            v = [x - 128 for x in v]
        mono = list(v) if ch == 1 else [sum(t) for t in zip(*(v[c::ch] for c in range(ch)))]
        return [0.0] * (lo - start) + [x * scale for x in mono] + [0.0] * (start + n - hi)

    rev = [int(format(i, "010b")[::-1], 2) for i in range(n)]
    tw = [complex(math.cos(-2 * math.pi * k / n), math.sin(-2 * math.pi * k / n)) for k in range(n // 2)]

    def fft(z):
        a = [z[i] for i in rev]
        size2 = 2
        while size2 <= n:
            half, step = size2 // 2, n // size2
            ws = tw[::step][:half]
            for s0 in range(0, n, size2):
                for k in range(half):
                    i, j = s0 + k, s0 + k + half
                    t = ws[k] * a[j]
                    a[j] = a[i] - t
                    a[i] += t
            size2 *= 2
        return a

    top = min(rate / 2, 16000)
    df = rate / n

    def mel(f):
        return 2595 * math.log10(1 + f / 700)

    def hz(m):
        return 700 * (10 ** (m / 2595) - 1)

    bands = []  # the FFT bins each row of pixels covers, lowest pitch first
    for r in range(tall):
        f0, f1 = hz(mel(top) * r / tall), hz(mel(top) * (r + 1) / tall)
        b0 = min(int(f0 / df), n // 2)
        bands.append((b0, max(b0 + 1, min(math.ceil(f1 / df), n // 2 + 1))))
    cols = []
    for c in range(0, wide, 2):  # two real columns go through one complex FFT
        x, y = (heard(int((c + d + 0.5) * frames / wide) - n // 2) for d in (0, 1))
        z = fft([complex(p * w, q * w) for p, q, w in zip(x, y, hann)])
        for part in (0, 1):
            power = []
            for k in range(n // 2 + 1):
                zk, zn = z[k % n], z[-k % n].conjugate()
                v = (zk + zn) / 2 if part == 0 else (zk - zn) / 2j
                power.append(v.real * v.real + v.imag * v.imag)
            cols.append([sum(power[b0:b1]) / (b1 - b0) for b0, b1 in bands])
    cols = cols[:wide]
    loud = max(max(c) for c in cols)
    peak = 10 * math.log10(loud) if loud > 0 else 0
    lut = []
    for i in range(256):
        f = i / 255 * (len(MAGMA) - 1)
        lo_c, hi_c, t = MAGMA[int(f)], MAGMA[min(int(f) + 1, len(MAGMA) - 1)], f - int(f)
        lut.append(bytes(round(p + (q - p) * t) for p, q in zip(lo_c, hi_c)))
    rows = []
    for r in range(tall - 1, -1, -1):  # high pitches at the top
        line = bytearray()
        for c in cols:
            v = (10 * math.log10(c[r]) - peak + 80) / 80 if c[r] > 0 and loud > 0 else 0
            line += lut[max(0, min(255, int(v * 255)))]
        rows.append(bytes(line))
    secs = frames / rate
    note = f"the sound as a spectrogram: {length_text(secs)} across, 0-{top / 1000:g} kHz up"
    return (len(cols), tall, rows), note + (" (silent)" if not loud else "")


def ffmpeg():
    """-> ffmpeg to use ($RECEIPT_FFMPEG first; "none" there means don't), or None"""
    v = os.environ.get("RECEIPT_FFMPEG")
    if v is not None:
        return None if v.strip().lower() in ("", "none", "off") else v
    return shutil.which("ffmpeg")


def run_ffmpeg(args, what, timeout=600):
    exe = ffmpeg()
    try:
        p = subprocess.run([exe, "-v", "error", "-nostdin", "-y", *args], capture_output=True, timeout=timeout)
    except OSError as e:
        sys.exit(f"receipt: couldn't start ffmpeg ({exe}): {e.strerror}")
    except subprocess.TimeoutExpired:
        sys.exit(f"receipt: ffmpeg took over {timeout} s on {what}")
    if p.returncode:
        said = p.stderr.decode("utf-8", "replace").strip()[-300:]
        sys.exit(f"receipt: ffmpeg couldn't make {what} ({said})")


def probe(path, what):
    """-> (seconds or None, width, height) of a sound or video, as ffmpeg reads it (0, 0 with no picture)"""
    try:
        p = subprocess.run([ffmpeg(), "-hide_banner", "-nostdin", "-i", path], capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        sys.exit(f"receipt: ffmpeg couldn't read {what} ({e})")
    said = p.stderr.decode("utf-8", "replace")
    if "Stream #" not in said:
        sys.exit(f"receipt: ffmpeg couldn't read {what} ({said.strip()[-300:]})")
    d = re.search(r"Duration: (\d+):(\d\d):(\d\d(?:\.\d+)?)", said)
    v = re.search(r"Stream #[^\n]*Video:[^\n]*?(\d{2,5})x(\d{2,5})", said)
    secs = int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3)) if d else None
    return secs, (int(v.group(1)) if v else 0), (int(v.group(2)) if v else 0)


def frames(path, what, n=4):
    """-> (n frames of a video side by side, a line saying what they are), taken with ffmpeg"""
    secs, w, h = probe(path, what)
    if not w:
        sys.exit(f"receipt: {what} has no pictures in it")
    tmp = tempfile.mkdtemp(prefix="receipt-")
    try:
        got = []
        for i, t in enumerate([secs * (k + 0.5) / n for k in range(n)] if secs else [0]):
            out = os.path.join(tmp, f"{i}.png")
            run_ffmpeg(["-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", "-vf", "scale=480:-2", "-pix_fmt", "rgb24",
                        out], f"a frame of {what}")  # fmt: skip
            if os.path.isfile(out):
                with open(out, "rb") as fh:
                    got.append(pixels(fh.read(), f"a frame of {what}"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not got:
        sys.exit(f"receipt: ffmpeg found no frames in {what}")
    tall, gap = min(g[1] for g in got), bytes(INKS[0]) * 8
    rows = [gap.join(g[2][y] for g in got) for y in range(tall)]
    long_ = f", {length_text(secs)} long" if secs else ""
    many_ = f"{len(got)} frames" if len(got) > 1 else "a frame"
    return (len(rows[0]) // 3, tall, rows), f"{many_} from the video{long_}, {w}×{h}"


def look(path, what, data=None):
    """--picture's file, or the one --shot picks -> (picture, note): a PNG as it is, a WAV as its spectrogram; with
    ffmpeg, other pictures as they are, other sounds as spectrograms and videos as frames"""
    if data is None:
        with open(path, "rb") as fh:
            data = fh.read(16)
            if data[8:12] == b"WAVE" or data[:8] == b"\x89PNG\r\n\x1a\n":
                data += fh.read()
    if data[8:12] == b"WAVE":
        return sound(data, what)
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return pixels(data, what), None
    ext = os.path.splitext(path)[1].lower()
    kind = ("a video" if ext in VIDEO_TYPES else "a sound" if ext in AUDIO_TYPES else
            "a picture" if ext in IMAGE_TYPES and ext != ".svg" else None)  # fmt: skip
    if not kind:
        sys.exit(f"receipt: {what} isn't a PNG or a WAV, or a picture, sound or video ffmpeg could read; save it as one")
    if not ffmpeg():
        sys.exit(f"receipt: {what} is {kind}; receipt.py reads PNGs and WAVs itself and needs ffmpeg for others: "
                 "install it, or set RECEIPT_FFMPEG to where it is")  # fmt: skip
    if kind == "a video":
        return frames(path, what)
    tmp = tempfile.mkdtemp(prefix="receipt-")
    try:
        out = os.path.join(tmp, "x.wav" if kind == "a sound" else "x.png")
        if kind == "a sound":
            run_ffmpeg(["-i", path, "-vn", "-ac", "1", "-c:a", "pcm_s16le", out], f"a WAV of {what}")
        else:
            run_ffmpeg(["-i", path, "-frames:v", "1", "-pix_fmt", "rgb24", out], f"a PNG of {what}")
        with open(out, "rb") as fh:
            data = fh.read()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return sound(data, what) if kind == "a sound" else (pixels(data, what), None)


def shot_picture(outputs, tmp):
    """-> (picture, note) of what the run made, for --shot on a .png: a screenshot of the page it made; with no
    page, frames of its video or its sound's spectrogram"""
    kinds = [os.path.splitext(o["name"])[1].lower() for o in outputs]
    if any(k in (".html", ".htm", ".svg") for k in kinds) or not outputs:
        return pixels(shot(outputs, tmp), "the screenshot"), None
    for want in (VIDEO_TYPES, AUDIO_TYPES):
        these = [(o, k) for o, k in zip(outputs, kinds) if k in want]
        if these:
            (o, k), n = these[0], len(these)
            pic, note = look(o["path"], o["name"], o["body"] if k == ".wav" else None)
            return pic, note + (f" (the first of {n})" if n > 1 else "")
    sys.exit("receipt: --shot found no page (.html or .svg), video or sound among the files the run made")


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


FOOT = "made with receipt.py {} · musharna.github.io/prompt-receipts"


def parts(s):
    """a receipt's text -> (head, asked, made, took): [(label, value lines)] each, a line that starts with 9 spaces
    going on with the one above"""
    head, *body = s.split("\n")
    entries = []
    for line in body:
        if entries and line[:9] == " " * 9:
            entries[-1][1].append(line[9:])
        else:
            entries.append((line[:9], [line[9:]]))
    asked = [e for e in entries if e[0].strip() in ("prompt", "prompts", "given")]
    made = [e for e in entries if e[0].strip() in ("files", "made", "page")]
    took = [e for e in entries if e not in asked and e not in made]
    return head, asked, made, took


def stamp(took):
    """a reported receipt's REPORTED line and the post it names, out of IT TOOK -> (the rest, note, post)"""
    note = [" ".join(v.strip() for v in values) for label, values in took if label.strip() == "REPORTED"]
    if not note:
        return took, None, None
    post = [" ".join(v.strip() for v in values) for label, values in took if label.strip() == "post"]
    return [e for e in took if e[0].strip() not in ("REPORTED", "post")], note[0], (post[0] if post else None)


def picture(s, table=False, pic=None, total=None, note=None, no=None):
    """a receipt's lines wrap under their label (s is made at PNG_COLS); a comparison table keeps its columns.
    A receipt reads like one from a shop: what was asked for, what it made (with a picture of it if given),
    what it took, the total, and a barcode of its number"""
    head, *body = s.split("\n")
    foot = FOOT.format(VERSION)
    if table:
        heads = fold(head, max([PNG_COLS] + [len(b) for b in body]))
        cols = max(len(x) for x in body + heads)
        rows = [(x, 1) for x in heads] + [("-" * cols, 3)] + [(x, 1) for x in body]
        return png(rows + [("-" * cols, 3), (foot, 3)])
    head, asked, made, took = parts(s)
    rule = ("-", 3)  # drawn as wide as the widest line
    rows = [(x, 1) for x in fold(head, PNG_COLS)] + [rule]
    took, said, post = stamp(took)
    if said:  # what a post says, not a log: stamped at the top
        rows += [("REPORTED", 5)] + [(x, 1) for x in textwrap.wrap(said, PNG_COLS)]
        rows += [(x, 1) for x in fold(post, PNG_COLS)] if post else []
        rows.append(("", 1))
    for label, values in asked:
        if label.strip() == "given":  # whose words the prompt above is, faint under it
            rows[-1:-1] = [(x, 3) for x in textwrap.wrap(" ".join(v.strip() for v in values), PNG_COLS)]
            continue
        rows.append(("ASKED FOR", 5))
        if label.strip() == "prompt":  # one prompt: the whole width
            rows += [(x, 1) for x in textwrap.wrap(" ".join(v.strip() for v in values), PNG_COLS,
                                                   break_long_words=False, break_on_hyphens=False)]  # fmt: skip
        else:  # numbered prompts keep their numbers
            rows += [(v, 1) for v in values]
        rows.append(("", 1))
    if made or pic:
        rows.append(("MADE", 5))
        if pic:
            rows.append((None, 0))
            if note:
                rows += [(x, 3) for x in textwrap.wrap(note, PNG_COLS)]
        for label, values in made:
            rows += [(x, 3 if label.strip() == "page" else 1) for x in fold(" ".join(v.strip() for v in values), PNG_COLS)]
        rows.append(rule)
    if asked or made or pic:
        rows.append(("IT TOOK", 5))
    rows += [
        ((label if i == 0 else " " * 9) + piece, 3 if label.strip() == "cost" and j else 1)  # the cost's lines, faint
        for label, values in took
        for j, value in enumerate(values)
        for i, piece in enumerate(fold(value, PNG_COLS - 9), j)
    ]
    if total:
        rows += [rule, (total, 4)]
    rows.append(rule)
    if no:
        rows.append((no, 6))
    rows.append((foot, 3))
    # the width is known only once every line is in; then the rules span it and the total sits at its right edge
    cols = max(len(t) if isinstance(t, str) else 2 * (len(t[0]) + len(t[1]) + 1)
               for t, ink in rows if t not in (None, "-") and ink != 6)  # fmt: skip
    cols += cols % 2  # even, so the total at twice the size ends where the rules do

    def drawn(t, ink):
        if t == "-":
            return "-" * cols
        if isinstance(t, tuple):  # twice the size: half as many letters span it
            return t[0] + " " * (cols // 2 - len(t[0]) - len(t[1])) + t[1]
        return t

    return png([(drawn(t, ink), ink) for t, ink in rows], pic=pic)


def stats(took):
    """IT TOOK's lines -> the few a glance needs: the model, how long, how many tool calls"""
    first = {label.strip(): values[0].split(" · ")[0] for label, values in took}
    out = []
    if "model" in first and not first["model"].startswith("not "):
        out.append(first["model"].split(" (")[0])
    if "time" in first and not first["time"].startswith("not "):
        out.append(first["time"].split(" (")[0])
    if "work" in first:
        out.append(first["work"].split(", ")[0])
    return out


def named(took):
    """is the model the sender's word (--model), not the log's?"""
    return any(label.strip() == "model" and "with --model" in values[0] for label, values in took)


CARD_W, CARD_H = 1080, 1350  # 4:5, which X, Bluesky and LinkedIn show whole in a feed


def card(s, pic=None, total=None, note=None, no=None):
    """--look card: the receipt cut down for a feed: the prompt large, the picture as big as the rest leaves room
    for, the model, time and tool calls, the total, a barcode of its number. 1080 wide and at most 1350 tall (4:5),
    as tall as it needs. The full receipt is the strip"""
    head, asked, made, took = parts(s)
    pad, tooth = 48, 10
    inner = CARD_W - 2 * pad

    def lh(size):
        return 8 * size + max(8, 3 * size)

    items = []  # (kind, text, size, ink); kinds: line, right, tag, gap, pic, bars

    def say(text, size, ink=1, most=None, kind="line"):
        cols = inner // (8 * size)
        lines = fold(text, cols) if " · " in text else textwrap.wrap(text, cols, break_on_hyphens=False) or [""]
        if most and len(lines) > most:
            lines = lines[:most]
            lines[-1] = lines[-1][: cols - 1].rstrip() + "…"
        items.extend((kind, x, size, ink) for x in lines)

    rule = ("line", "-" * (inner // 16), 2, 3)
    edge = pad + inner // 16 * 16 - 2  # where the rules' ink ends: the right edge of the card's text
    say(head, 2, 3, most=2)
    items.append(rule)
    took, said, post = stamp(took)
    if said:
        items.append(("tag", "REPORTED", 3, 0))
        say(said, 2, most=2)
        if post:
            say(post, 2, most=2)
        items.append(("gap", "", 2, 0))
    prompt = [" ".join(v.strip() for v in values) for label, values in asked if label.strip() != "given"]
    given = [" ".join(v.strip() for v in values) for label, values in asked if label.strip() == "given"]
    if prompt:
        items.append(("tag", "ASKED FOR", 3, 0))
        say(" ".join(prompt), 4, most=5)
        if given:  # the given line's whole note is on the strip
            say("prompt from the sender, not from the log", 3, 3)
    made = [m for m in made if " ".join(v.strip() for v in m[1]) != "not stated"]  # a card has no label to say what
    if pic or made:
        items.append(("gap", "", 2, 0))
        if pic:
            items.append(("pic", "", 0, 0))
            if note:
                say(note, 2, 3, most=2)
        for label, values in made:
            say(" ".join(v.strip() for v in values), 2, 3 if label.strip() == "page" else 1, most=3)
    items.append(rule)
    glance = stats(took)
    if glance:
        say(" · ".join(glance), 4, most=3)
    if named(took):
        say("model named by the sender, not from the log", 2, 3)
    if total:
        word, _, rest = total[0].partition(" ")
        if rest == "as reported":  # the post's figure: the word stays as large as it, so a cropped card keeps it
            word, rest = "REPORTED", ""
        items.append(("gap", "", 2, 0))
        items.append(("total", (word, total[1]), 6, 1))
        if rest:
            items.append(("right", rest, 2, 3))
    elif any(label.strip() == "cost" and values[0] == "not stated" for label, values in took):
        say("cost not stated", 4)
    items.append(rule)
    if no and all(" " <= c <= "~" for c in no):
        items.append(("bars", no, 2, 1))
    say(FOOT.format(VERSION), 2, 3, most=2)

    def height(kind, size):
        return {"gap": 16, "pic": 0, "bars": 84, "tag": lh(size) + 8}.get(kind, lh(size))

    fixed = sum(height(k, size) for k, _, size, _ in items) + 2 * (pad + tooth)
    if pic:
        room = CARD_H - fixed - 20  # the frame and the space around it
        pic = shrink(*pic, inner - 4, max(room, 120))
    h = fixed + (pic[1] + 20 if pic else 0)  # a short picture makes a shorter card, not one with empty bands
    box = h - fixed - 20 if pic else 0
    img = [bytearray(CARD_W) for _ in range(h)]
    cache, pics = {}, []
    y = tooth + pad
    for kind, t, size, ink in items:
        if kind == "pic":
            pw, ph, _ = pic
            x0, at = (CARD_W - pw) // 2, y + 10 + (box - ph) // 2
            for yy in range(at - 2, at + ph + 2):
                img[yy][x0 - 2 : x0 + pw + 2] = b"\x01" * (pw + 4)
            pics.append((x0, at, pic))
            y += box + 20
            continue
        if kind == "tag":
            wide = len(t) * 8 * size
            for yy in range(y, y + 8 * size + 4 * size):
                img[yy][pad - 2 * size : pad + wide + 2 * size] = b"\x01" * (wide + 4 * size)
            letters(img, pad, y + 2 * size, t, size, 0, 1, cache)
        elif kind == "bars":
            bars(img, y + 12, t, 2, 56)
        elif kind == "total":  # right-aligned to the last inked column: a letter's cell has one blank column
            letters(img, pad, y, t[0], size, 1, 0, cache)
            letters(img, edge - (len(t[1]) * 8 - 1) * size, y, t[1], size, 1, 0, cache)
        elif kind == "right":
            letters(img, edge - (len(t) * 8 - 1) * size, y, t, size, ink, 0, cache)
        elif kind == "line":
            letters(img, pad, y, t, size, ink, 0, cache)
        y += height(kind, size)
    torn(img, tooth)
    return encode(img, pics)


def alt_text(s, total=None, note=None, pic=None, most=1000):
    """what the picture of the receipt shows, in words, for people who can't see it: 1,000 characters at most,
    as X and Mastodon take"""
    head, asked, made, took = parts(s)
    took, stamped, post = stamp(took)
    said = [f"A receipt of what a post says about an AI coding run, not read from a log{f' ({post})' if post else ''}."
            if stamped else "A receipt for an AI coding run, made with receipt.py."]  # fmt: skip
    prompt = " ".join(" ".join(v.strip() for v in values) for label, values in asked if label.strip() != "given")
    if any(label.strip() == "given" for label, _ in asked):
        said.append("(The sender gave the prompt; the log doesn't hold it.)")
    if pic:
        said.append(f"It shows what the run made: {note}." if note else "It shows a picture of what the run made.")
    things = ["; ".join(" ".join(v.strip() for v in values) for label, values in made if label.strip() != "page")]
    if things[0]:
        said.append(f"Made: {things[0]}.")
    glance = stats(took)
    if glance:
        said.append("It took: " + ", ".join(glance) + (" (the model named by the sender)" if named(took) else "") + ".")
    if total:
        said.append(f"{total[0][:1]}{total[0][1:5].lower()}{total[0][5:]}: {total[1]}.")  # TOTAL at API prices
    rest = " ".join(said)
    if prompt:
        prompt = prompt.rstrip(".")
        room = most - len(rest) - len(" Asked for: .")
        if len(prompt) > room:
            prompt = prompt[: max(room - 1, 0)].rstrip() + "…"
        said.insert(1, f"Asked for: {prompt}.")
    return " ".join(said)[:most]


PRINT_W = 640  # CSS pixels; the picture is twice that


def print_page(s, pic=None, total=None, note=None, no=None):
    """--look print as a page: the receipt laid out in a real font, for a browser to draw"""
    head, asked, made, took = parts(s)
    e = html.escape

    def dots(v):  # a wrapped line ends with its "·" rather than starting with one, and keeps a short (…) whole
        v = re.sub(r"\([^()]{1,24}\)", lambda m: m.group(0).replace(" ", "\u00a0"), v)
        return e(v).replace(" · ", "\u00a0· ")

    paper, ink, back, faint = ("#%02x%02x%02x" % c for c in INKS)
    out = [f'<div class="head">{e(head)}</div><hr>']
    took, said, post = stamp(took)
    if said:
        out += ["<h2>REPORTED</h2>", f"<p>{e(said)}</p>"] + ([f"<p>{dots(post)}</p>"] if post else [])
    prompt = [" ".join(v.strip() for v in values) for label, values in asked if label.strip() != "given"]
    if prompt:
        out.append('<h2>ASKED FOR</h2>')
        out += [f'<p class="ask">{e(p)}</p>' for p in prompt]
        out += [f'<p class="faint">{e(" ".join(v.strip() for v in values))}</p>'
                for label, values in asked if label.strip() == "given"]  # fmt: skip
    if pic or made:
        out.append("<h2>MADE</h2>")
        if pic:
            pw, ph, _ = pic = shrink(*pic, 2 * (PRINT_W - 64))
            data = base64.b64encode(rgb_png(pw, ph, pic[2])).decode()
            out.append(f'<img src="data:image/png;base64,{data}" width="{pw / 2:g}" height="{ph / 2:g}" alt="">')
            if note:
                out.append(f'<p class="faint">{e(note)}</p>')
        for label, values in made:
            out.append(f'<p class="{"faint" if label.strip() == "page" else ""}">{dots(" ".join(v.strip() for v in values))}</p>')
        out.append("<hr>")
    if asked or made or pic:
        out.append("<h2>IT TOOK</h2>")
    out.append("<dl>")
    for label, values in took:
        first, *more = values
        rest = "".join(f'<span class="{"faint" if label.strip() == "cost" else ""}">\n{dots(v)}</span>' for v in more)
        out.append(f"<dt>{e(label.strip())}</dt><dd>{dots(first)}{rest}</dd>")
    out.append("</dl>")
    if total:
        out.append(f'<hr><div class="total"><span>{e(total[0])}</span><span>{e(total[1])}</span></div>')
    out.append("<hr>")
    if no and all(" " <= c <= "~" for c in no):
        x, rects = 0, []
        for i, n in enumerate(code128(no)):
            if i % 2 == 0:
                rects.append(f'<rect x="{x}" width="{n}" height="1"/>')
            x += n
        plate, bar = (ink, paper) if dark_paper() else (paper, ink)  # scanners read dark bars on light
        out.append(f'<svg class="bars" viewBox="-10 0 {x + 20} 1" width="{(x + 20) * 2}" height="56" '
                   f'preserveAspectRatio="none"><rect x="-10" width="{x + 20}" height="1" fill="{plate}"/>'
                   f'<g fill="{bar}">{"".join(rects)}</g></svg>')  # fmt: skip
    out.append(f'<div class="foot">{e(FOOT.format(VERSION))}</div>')
    tooth = 8  # torn paper: a row of paper triangles, pointing away from the receipt
    zig = ("url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='8'%3E"
           f"%3Cpath d='M0 8L8 0L16 8Z' fill='%23{paper[1:]}'/%3E%3C/svg%3E\") repeat-x")  # fmt: skip
    return f"""<!doctype html><meta charset="utf-8"><style>
html,body{{margin:0;background:{back}}}
.r{{background:{paper};color:{ink};padding:22px 32px 26px;
font:14px/1.5 ui-monospace,"Cascadia Mono","SF Mono",Menlo,Consolas,"DejaVu Sans Mono","Liberation Mono",monospace;
overflow-wrap:anywhere}}
.edge{{height:{tooth}px;background:{zig}}}
.edge.bottom{{transform:scaleY(-1)}}
.head{{font-size:12px;color:{faint}}}
hr{{border:0;border-top:2px dashed {faint};margin:12px 0}}
h2{{display:inline-block;margin:10px 0 6px;padding:1px 8px;background:{ink};color:{paper};font-size:13px;
letter-spacing:.12em;font-weight:700}}
p{{margin:0 0 6px}}
.ask{{font-size:19px;line-height:1.4;font-weight:600}}
.faint{{color:{faint}}}
img{{display:block;margin:8px auto;border:2px solid {ink}}}
dl{{display:grid;grid-template-columns:9ch 1fr;margin:0;column-gap:1ch}}
dt{{color:{faint}}}
dd{{margin:0;white-space:pre-wrap}}
.total{{display:flex;justify-content:space-between;font-size:28px;font-weight:800;letter-spacing:.03em}}
.bars{{display:block;margin:6px auto 14px}}
.foot{{text-align:center;font-size:11px;color:{faint}}}
</style><div class="edge"></div><div class="r">{"".join(out)}</div><div class="edge bottom"></div>
"""


def print_look(s, pic=None, total=None, note=None, no=None):
    """--look print: the receipt drawn by a browser, in a real font, cut where the paper ends"""
    b = browser()
    if not b:
        sys.exit("receipt: --look print is drawn by Chrome, Edge or Chromium, and none was found; "
                 "set RECEIPT_BROWSER to the browser's path, or use --look strip or card")  # fmt: skip
    page = print_page(s, pic, total, note, no)
    lines = s.count("\n") + 1
    tall = 600 + 26 * lines + (pic[1] * (PRINT_W - 64) // max(pic[0], 1) if pic else 0)
    tmp = tempfile.mkdtemp(prefix="receipt-")
    try:
        path = os.path.join(tmp, "receipt.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(page)
        shot_png = snap(b, pathlib.Path(path).as_uri(), os.path.join(tmp, "print.png"), tmp, "--look print",
                        f"{PRINT_W},{tall}", ["--force-device-scale-factor=2"])  # fmt: skip
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    w, h, rows = pixels(shot_png, "the browser's picture of the receipt")
    blank = bytes(INKS[2]) * w

    def near(row):  # the browser may round a colour by one
        return all(abs(a - c) <= 2 for a, c in zip(row[::97], blank[::97]))

    if not near(rows[-1]):
        sys.exit(f"receipt: --look print: {b} drew the receipt taller than its window ({h} pixels); "
                 "please report it")  # fmt: skip
    end = h
    while end and near(rows[end - 1]):
        end -= 1
    if not end:
        sys.exit(f"receipt: --look print: {b} drew nothing")
    return rgb_png(w, end, rows[:end])


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
    global PRICES, PRICES_FROM, INKS
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="parts for --hide: " + ", ".join(PARTS),
    )
    ap.add_argument("session", nargs="?")
    ap.add_argument("--version", action="version", version=f"receipt.py {VERSION}")
    ap.add_argument("--codex", action="store_true")
    ap.add_argument("--opencode", action="store_true")
    ap.add_argument("--qwen", action="store_true")
    ap.add_argument("--page", metavar="FILE.html")
    ap.add_argument("--output-url", metavar="URL")
    ap.add_argument("--gemini", action="store_true")
    ap.add_argument("--copilot", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--pick", type=int)
    ap.add_argument("--last", type=int)
    ap.add_argument("--turns", nargs="?", const="all", metavar="A-B")
    ap.add_argument("--hide", default="")
    ap.add_argument("--counts", action="store_true")
    ap.add_argument("--rename", action="append", default=[])
    ap.add_argument("--prompt", action="store_true")
    ap.add_argument("--asked", metavar="FILE")
    ap.add_argument("--model", metavar="NAME")
    ap.add_argument("--reported", metavar="FILE")
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
    ap.add_argument("--share", action="store_true")
    ap.add_argument("--bundle", metavar="FILE.zip")
    ap.add_argument("--shot", action="store_true")
    ap.add_argument("--picture", metavar="FILE.png")
    ap.add_argument("--look", choices=("strip", "card", "print"))
    ap.add_argument("--theme", choices=tuple(THEMES))
    ap.add_argument("--statusline", action="store_true")
    ap.add_argument("--totals", nargs="?", const="day", choices=BY)
    ap.add_argument("--since", metavar="DATE")
    ap.add_argument("--until", metavar="DATE")
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
    a.link = a.link or a.share
    if a.reported:  # no log: only what makes, shows or signs the receipt goes with it
        keep = ("reported", "out", "png", "json", "md", "look", "theme", "picture", "link", "share", "redact", "prices",
                "sign", "report")  # fmt: skip
        clash = ["a session" if k == "session" else "--" + k.replace("_", "-")
                 for k, v in vars(a).items() if k not in keep and v not in (None, False, [], "")]  # fmt: skip
        if clash:
            sys.exit(f"receipt: --reported makes a receipt from what a post says, so it can't go with {', '.join(clash)}")
    if a.prices:
        try:
            with open(os.path.expanduser(a.prices), encoding="utf-8") as fh:
                PRICES = price_table(json.load(fh))
        except (OSError, ValueError) as e:
            sys.exit(f"receipt: can't read {a.prices} as a price file ({e})")
        if not PRICES:
            sys.exit(
                f"receipt: no Anthropic, OpenAI, Gemini or Qwen prices in {a.prices}; it should be a copy of LiteLLM's "
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
    picked = [t for t in TOOLS if t != "claude" and getattr(a, t)]
    if len(picked) > 1:
        flags = [f"--{t}" for t in TOOLS if t != "claude"]
        sys.exit(f"receipt: pick one of {', '.join(flags[:-1])} and {flags[-1]}")
    if a.redact and not (a.prompt or a.asked or a.reply or a.outcome or a.recipe or a.page or a.reported):
        sys.exit(
            "receipt: --redact changes text the receipt shows, so it needs --prompt, --reply, --recipe, --outcome "
            "or --page"
        )
    asked = None
    if a.asked:  # read it now, so a file it can't use stops it before anything is made
        if a.list or a.totals or a.hook or a.combine or a.compare:
            sys.exit("receipt: --asked gives one session's prompt, so it can't go with --list, --totals, --hook, "
                     "--combine or --compare")  # fmt: skip
        try:
            if a.asked == "-":
                asked = sys.stdin.read()
            else:
                with open(os.path.expanduser(a.asked), encoding="utf-8") as fh:
                    asked = fh.read()
        except (OSError, UnicodeDecodeError) as e:
            sys.exit(f"receipt: can't read --asked {a.asked} ({getattr(e, 'strerror', None) or e})")
        asked = asked.strip()
        if not asked:
            sys.exit(f"receipt: --asked {a.asked} is empty")
        a.prompt = True  # giving the prompt is asking for it on the receipt
    if a.model and (a.list or a.totals or a.hook or a.combine or a.compare):
        sys.exit("receipt: --model names one log's model, so it can't go with --list, --totals, --hook, --combine "
                 "or --compare")  # fmt: skip
    if a.out and a.out.lower().endswith(".png"):
        a.png = True
    if a.out and a.out.lower().endswith(".json"):
        a.json = True
    if a.out and a.out.lower().endswith(".md"):
        a.md = True
    if a.output_url and not a.page:
        sys.exit("receipt: --output-url fingerprints the page you put there, so add --page FILE.html and upload that file")
    if a.output_url and not re.match(r"https://|http://(localhost|127\.0\.0\.1)[:/]", a.output_url):
        sys.exit("receipt: --output-url needs an https:// address, so anyone opening the receipt can fetch it")
    if a.png and not a.out:
        sys.exit("receipt: a picture needs a file: --out receipt.png")
    if sum(map(bool, (a.png, a.json, a.md))) > 1:
        sys.exit("receipt: pick one of --md, --json and --png")
    if a.hook and not a.out:
        sys.exit(
            "receipt: --hook needs --out (a file or folder), since hooks' output isn't shown"
        )
    many_in = a.combine or a.compare
    if a.share and a.compare:
        sys.exit("receipt: --share sends one run to the gallery, so it can't go with --compare")
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
    if a.shot and not (a.bundle or a.png):
        sys.exit("receipt: --shot goes into a --bundle or onto a picture of the receipt, so add --bundle FILE.zip "
                 "or --out receipt.png")  # fmt: skip
    if a.picture and not a.png:
        sys.exit("receipt: --picture goes on a picture of the receipt, so add --out receipt.png")
    if (a.look or a.theme) and not a.png:
        sys.exit("receipt: --look and --theme are for a picture of the receipt, so add --out receipt.png")
    if a.look not in (None, "strip") and (a.compare or a.totals or a.list):
        sys.exit(f"receipt: --look {a.look} draws one receipt, so it can't go with --compare, --totals or --list")
    INKS = THEMES[a.theme or "paper"]  # before any picture is read: see-through parts are laid on the paper
    if a.picture and (many_in or a.list or a.totals):
        sys.exit("receipt: --picture goes on one session's receipt, so it can't go with --combine, --compare, "
                 "--list or --totals")  # fmt: skip
    pic = note = None
    if a.picture:  # read it now, so a file it can't use stops it before anything is made
        try:
            pic, note = look(os.path.expanduser(a.picture), a.picture)
        except OSError as e:
            sys.exit(f"receipt: can't read --picture {a.picture} ({e.strerror})")
    if a.reported:
        r = read_report(a.reported, a.redact)
        s = reported_text(r, PNG_COLS - 9) if a.png else reported_text(r)
        saved = emit(a, r, s, json.dumps(r, indent=1) if a.json else None, pic=pic, note=note)
        if a.sign and saved:
            sign(a.sign, saved)
        if a.link:
            print(link(reported_text(r), a.share))
        return
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
    tool = picked[0] if picked else "claude"

    if a.statusline:
        if any(v not in (None, False, [], "") for k, v in vars(a).items() if k != "statusline"):
            sys.exit("receipt: --statusline reads Claude Code's status-line input and takes no other options")
        try:
            d = json.load(sys.stdin)
        except ValueError as e:
            sys.exit(f"receipt: --statusline expects Claude Code's status-line input on stdin ({e})")
        print(statusline(d if isinstance(d, dict) else {}))
        return
    if (a.since or a.until) and not a.totals:
        sys.exit("receipt: --since and --until go with --totals")
    if a.totals:
        clash = [f for f, v in (("a session", a.session), ("--list", a.list), ("--pick", a.pick), ("--last", a.last),
                 ("--turns", a.turns), ("--prompt", a.prompt), ("--reply", a.reply), ("--recipe", a.recipe),
                 ("--outcome", a.outcome), ("--record", a.record), ("--bundle", a.bundle), ("--hook", a.hook),
                 ("--report", a.report), ("--combine", a.combine), ("--compare", a.compare), ("--rename", a.rename),
                 ("--counts", a.counts), ("--prompt-id", a.prompt_id), ("--file-names", a.file_names),
                 ("--share (the gallery takes one run)", a.share))
                 if v]  # fmt: skip
        if clash:
            sys.exit(f"receipt: --totals adds up many sessions, so it can't go with {', '.join(clash)}")
        dates = []
        for flag, v in (("--since", a.since), ("--until", a.until)):
            try:
                dates.append(datetime.date.fromisoformat(v) if v else None)
            except ValueError:
                sys.exit(f"receipt: {flag} needs a date like 2026-10-01, not {v!r}")
        since, until = dates
        if since and until and since > until:
            sys.exit("receipt: --since is after --until")
        keys = sessions(tool, a.all)
        if not keys:
            nothing_found(tool, a.all)
        if since:  # a log last changed before the first day can't hold a prompt from it
            keys = [k for k in keys if changed(tool, k).date() >= since]
        if len(keys) > 100:
            print(f"receipt: reading {len(keys):,} sessions…", file=sys.stderr)
        rows, all_priced = totals(tool, keys, a.totals, since, until) if keys else ({}, True)
        if not rows:
            sys.exit("receipt: no prompts in those dates" if since or until else f"receipt: no prompts in {TOOLS[tool]}'s sessions")
        billing = claude_billing() if tool == "claude" else None
        scope = "every folder" if a.all else f"folder {base_name(os.getcwd())}"
        s, payload = totals_text(tool, scope, a.totals, rows, all_priced, hide, billing, since, until)
        r = {"tool": "totals-" + TOOLS[tool]}
        saved = emit(a, r, s, json.dumps(payload, indent=1) if a.json else None, table=True)
        if a.link:
            print(link(s))
        if a.sign and saved:
            sign(a.sign, saved)
        return

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
            if not picked:
                where_ = os.path.abspath(path).replace(os.sep, "/")
                under = lambda d, name: where_.startswith(d.replace(os.sep, "/") + "/") or f"/{name}/" in where_  # noqa: E731
                if a.session.startswith("ses_") and not os.path.exists(a.session):
                    tool = "opencode"
                elif under(qwen_dir(), ".qwen"):
                    tool = "qwen"
                elif under(gemini_dir(), ".gemini"):
                    tool = "gemini"
                elif under(copilot_dir(), ".copilot"):
                    tool = "copilot"
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
        reader = {"opencode": opencode, "codex": codex, "qwen": qwen, "gemini": gemini, "copilot": copilot, "claude": claude}[
            tool
        ]
        if tool in ("claude", "codex") and is_exec_json(path):
            reader, tool = codex_exec, "codex"
        r = reader(path, part)
        r["receipt_version"] = VERSION
        r["duration_ms"] = (
            round((when(r["ended"]) - when(r["started"])).total_seconds() * 1000) if r.get("started") else None
        )  # fmt: skip
        r.setdefault("extras", {})
        r["receipt_no"] = receipt_no(r["tool"], r.pop("session_key"), r["part"])
        if tool == "claude":
            use = plan_use(os.path.splitext(os.path.basename(path))[0], r.get("started"), r.get("ended"))
            if use:
                r["plan_use"] = use
        check(r)
        made_part(r, folder_of(tool, path))
        rows = []
        if (
            "output" not in hide
            or a.page
            or a.turns is not None
            or a.prompt
            or a.reply
            or a.recipe
            or a.record
            or a.bundle
        ):
            rows = (exec_turns if reader is codex_exec else TURNS[tool])(path)
            sel, _ = pick(len(rows), part)
            rows = rows[sel[0] : sel[1]] if sel else rows
        if "output" not in hide:  # the replies the run gave: how many, how long; their text stays off
            said = [t["reply"] for t in rows if t.get("reply")]
            r["replies"], r["reply_words"] = len(said), sum(len(x.split()) for x in said)
        add_turns(r, rows, a, hide)
        if asked is not None:  # a prompt the log doesn't hold, in the sender's words: the receipt says so
            if r.get("first_prompt"):
                sys.exit("receipt: this log holds its own prompt (--prompt shows it); --asked is for a log that "
                         "doesn't, like claude -p output")  # fmt: skip
            r["first_prompt"], r["prompt_given"] = asked, True
        used = r.pop("_usage", None)
        if a.model:  # a model the log doesn't name, in the sender's words: its tokens priced at that model
            if r.get("log_name") != EXEC_JSON:
                sys.exit(f"receipt: this log names its model ({', '.join(r['models']) or 'none replied'}); --model is "
                         f"for one that doesn't, like {EXEC_JSON}")  # fmt: skip
            r["models"], r["model_given"] = [a.model], True
            bill = Bill()
            codex_call(bill, a.model, used or {}, summed=True)  # the turn's total: its calls' sizes aren't logged
            if bill.lines:
                r["cost_usd"] = round(bill.total(), 6)
                r["cost_note"] = "worked out from the logged tokens at API prices for the model you named"
                long = long_from(a.model)
                if long and (used or {}).get("input_tokens", 0) > long:
                    r["cost_note"] += (f", at its standard rate: the log adds up the run's calls, so if one went past "
                                       f"{long // 1000}k tokens it cost more")  # fmt: skip
                priced(r, bill)
            else:
                r["cost_note"] = f"the price table has none for {a.model}"
    if a.rename:
        rename(r, a.rename)
    renames = dict(p.split("=", 1) for p in a.rename)
    if a.recipe and any(not t["prompt"] for t in rows):
        sys.exit("receipt: --recipe needs the prompts, and this log doesn't hold them (claude -p doesn't write them)")
    if a.recipe:
        prompts = [
            scrub(t["prompt"], a.redact, "your prompt", "--recipe") for t in rows
        ]
        r["recipe"] = recipe(r, rows, prompts, hide, renames)
    if a.counts:
        counts_only(r)
    if not a.file_names:
        r.pop("file_names", None)
        r.pop("made_names", None)
    if r.get("first_prompt") and (a.prompt or a.prompt_id) and "prompt_id" not in r:
        r["prompt_id"] = prompt_id(r["first_prompt"])
    if not a.prompt_id and not a.prompt:
        r.pop("prompt_id", None)
    if a.prompt and r.get("first_prompt"):
        given = ("the --asked prompt", "--asked") if r.get("prompt_given") else ()
        r["first_prompt"] = scrub(r["first_prompt"], a.redact, *given)
    else:
        r.pop("first_prompt", None)
    if a.outcome:
        r["outcome"] = scrub(
            a.outcome.strip(), a.redact, "your --outcome note", "--outcome"
        )
    record = None
    if a.record or a.bundle or (a.shot and a.png):  # the record step gathers the files a screenshot needs
        record = make_record(
            r, tool, path, part, a.file_names, a.counts, hide, renames, rows
        )
        if not (a.record or a.bundle):  # made only to find the files: none is saved, so the receipt names none
            record = None
            r.pop("record", None)
    s = text(r, hide, a.prompt)
    if a.png:  # the picture is narrower, so its prompt wraps to fit
        s = text(r, hide, a.prompt, width=PNG_COLS - 9)
    outputs = r.pop("_outputs", [])
    paths, texts = r.pop("_written", ([], {}))
    made = r.pop("_made", [])
    if a.page:
        pp = os.path.expanduser(a.page)
        page = output_page(r, text(r, hide, a.prompt), rows, page_files(paths, texts, a.file_names, made), a, hide)
        page = page.encode("utf-8")  # bytes, so Windows doesn't turn its line ends into others the hash didn't see
        before = None
        if a.output_url and os.path.isfile(pp):  # the gist route uploads the page, then makes it again with its address
            with open(pp, "rb") as fh:
                before = fh.read()
        with open(pp, "wb") as fh:  # written only once it's whole: a stop leaves no half page
            fh.write(page)
        print(f"receipt: page saved to {pp}; open it in a browser", file=sys.stderr)
        if before is not None and before != page:
            print(f"receipt: {pp} isn't the same as the copy that was there before; if you uploaded that one, "
                  "upload this one in its place, or the site won't show it", file=sys.stderr)  # fmt: skip
        if not a.output_url:
            print("receipt: to show it with the receipt without a site of your own, put it in a public gist, "
                  "then make the receipt again with the gist file's raw address:\n"
                  f"  gh gist create --public {pp}\n"
                  "  gh api gists/ID --jq '.files[].raw_url'      (ID ends the address it printed)\n"
                  f"  receipt … --page {pp} --output-url RAW_ADDRESS --link", file=sys.stderr)  # fmt: skip
        if a.output_url:  # the page holds the receipt, so the receipt can hold the page's fingerprint only after
            r["output_url"], r["output_sha256"] = a.output_url, sha(page)
            s = text(r, hide, a.prompt, width=PNG_COLS - 9) if a.png else text(r, hide, a.prompt)
            print(f"receipt: put {pp} at {a.output_url} as it is: one changed byte and the receipt won't vouch for it",
                  file=sys.stderr)  # fmt: skip
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
            rows,
            hide,
        )
        if not a.json:
            payload = None
    if a.png and a.shot and not pic:  # a picture of what the run made, on the receipt
        tmp = tempfile.mkdtemp(prefix="receipt-")
        try:
            pic, note = shot_picture(outputs, tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    saved = [emit(a, r, s, payload, pic=pic, note=note)]
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
        print(link(text(r, hide, a.prompt), a.share))


def link(s, share=False):
    """-> a link to the site that shows this receipt; the receipt rides in the part after #, which browsers
    never send to the server, so nothing is uploaded. With share, also a link that opens a GitHub issue sending
    it to the gallery (.github/ISSUE_TEMPLATE/receipt.yml)"""
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
    out = f"\nlink (the receipt is inside the link; nothing is uploaded):\n{url}"
    if share:
        title = "Receipt: " + s.split("\n")[0].split(" · ")[1]
        q = urllib.parse.urlencode({"template": "receipt.yml", "title": title, "link": url}, quote_via=urllib.parse.quote)
        out += ("\n\nto add it to the gallery, open this and press Create (everything in it will be public; it goes in "
                f"once it's approved):\n{ISSUES}/new?{q}")
    return out


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
        elif r["tool"] == "Qwen Code":
            mode = re.match(r"approvals (\S+)$", settings)
            tail = f" -m {q(model)}" if model else ""
            tail += f" --approval-mode {q(mode.group(1))}" if mode and mode.group(1) != "default" else ""
            cmds.append(f"qwen{' --continue' if i else ''}{tail} {q(p)}")
        elif r["tool"] == "Gemini CLI":
            tail = f" -m {q(model)}" if model else ""
            cmds.append(f"gemini{' --resume latest' if i else ''}{tail} -p {q(p)}")
        elif r["tool"] == "Copilot CLI":
            tail = (f" --model {q(model)}" if model else "") + (f" --reasoning-effort {effort}" if effort else "")
            cmds.append(f"copilot{' --continue' if i else ''}{tail} -p {q(p)}")
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


def emit(a, r, s, payload, table=False, pic=None, note=None):
    if a.png:
        total = None
        if not table and r.get("cost_usd") is not None and any(x.startswith("cost     $") for x in s.split("\n")):
            word = "TOTAL at API prices" if "API" in r.get("cost_note", "") else "TOTAL as reported" if r.get("reported") else "TOTAL"
            total = (word, money(r["cost_usd"]))
        no = None if table else r.get("receipt_no")
        if table or a.look in (None, "strip"):
            data = picture(s, table, pic, total, note, no)
        else:
            data = (card if a.look == "card" else print_look)(s, pic, total, note, no)
        if not table:
            alt = alt_text(s, total, note, pic)
            data = with_alt(data, alt)
            print(f"receipt: alt text for the picture (also inside the PNG):\n  {alt}", file=sys.stderr)
        ext = "png"
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
