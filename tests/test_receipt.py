"""Runs tools/receipt.py the way a user does, on small made-up logs shaped like real ones.

Each test gets its own home folder with Claude Code, Codex and OpenCode logs in it, so nothing on
the machine running the tests is read. python -m unittest discover -s tests"""

import base64
import hashlib
import json
import os
import re
import shlex
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest
import zipfile
import zlib

RECEIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "tools", "receipt.py"
)
T0 = "2026-10-09T14:00:00.000Z"


def ts(minute):
    return f"2026-10-09T14:{minute:02d}:00.000Z"


def slug(path):
    return re.sub(r"[^A-Za-z0-9]", "-", path)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = os.path.realpath(self.tmp.name)
        self.home = os.path.join(root, "home")
        self.proj = os.path.join(root, "home", "proj")
        self.other = os.path.join(root, "home", "elsewhere")
        self.claude_dir = os.path.join(
            root, "moved-claude"
        )  # CLAUDE_CONFIG_DIR, not ~/.claude
        self.codex_dir = os.path.join(root, "moved-codex")
        self.data_dir = os.path.join(root, "data")
        for d in (
            self.proj,
            self.other,
            self.claude_dir,
            self.codex_dir,
            self.data_dir,
        ):
            os.makedirs(d, exist_ok=True)
        self.env = dict(
            os.environ,
            HOME=self.home,
            USERPROFILE=self.home,
            CLAUDE_CONFIG_DIR=self.claude_dir,
            CODEX_HOME=self.codex_dir,
            XDG_DATA_HOME=self.data_dir,
        )
        self.env.pop("ANTHROPIC_API_KEY", None)

    def tearDown(self):
        self.tmp.cleanup()

    def run_receipt(self, *args, cwd=None, stdin=None, env=None):
        return subprocess.run(
            [sys.executable, "-I", RECEIPT, *args],
            cwd=cwd or self.proj,
            env=env or self.env,
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def ok(self, *args, **kw):
        p = self.run_receipt(*args, **kw)
        self.assertEqual(p.returncode, 0, f"receipt failed: {p.stderr}")
        return p

    # ---------- made-up logs ----------

    def claude_log(
        self,
        prompt="Make a page for my habit tracker",
        name="s1",
        replies=True,
        total=1.234,
        resumed=False,
        rich=False,
        model="claude-opus-5-5",
        usage=None,
        second="now make it blue",
        said="done",
        subagent=False,
    ):
        entries = [
            {"type": "user", "timestamp": ts(0), "cwd": self.proj, "version": "2.1.300", "sessionId": name,
             "permissionMode": "default", "effort": "high", "message": {"role": "user", "content": prompt}},
        ]  # fmt: skip
        if rich:  # what a record fingerprints: loaded instructions, the system prompt, a file the model read
            entries += [
                {"type": "attachment", "timestamp": ts(0), "attachment": {"type": "instructions", "files": [
                    {"path": os.path.join(self.proj, "CLAUDE.md"), "type": "Project", "content": "be kind"}]}},
                {"type": "attachment", "timestamp": ts(0), "attachment": {
                    "type": "prompt_snapshot", "systemPrompt": ["You are Claude Code.", "Be brief."]}},
                {"type": "attachment", "timestamp": ts(0), "attachment": {"type": "environment", "snapshot": {
                    "platform": "linux", "shell": "zsh", "osVersion": "Linux 6.18",
                    "workingDirectory": self.proj}}},
                {"type": "assistant", "timestamp": ts(1), "message": {"id": "m0", "model": "claude-opus-5-5",
                    "content": [{"type": "tool_use", "id": "r1", "name": "Read",
                                 "input": {"file_path": os.path.join(self.proj, "notes.txt")}}]}},
                {"type": "user", "timestamp": ts(1), "message": {"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": "r1", "content": "     1\thello"}]},
                 "toolUseResult": {"type": "text", "file": {
                     "filePath": os.path.join(self.proj, "notes.txt"), "content": "hello",
                     "numLines": 1, "startLine": 1, "totalLines": 1}}},
            ]  # fmt: skip
        if replies:
            entries += [
                {"type": "assistant", "timestamp": ts(1), "message": {
                    "id": "m1", "model": model,
                    "usage": {"input_tokens": 1000, "output_tokens": 200,
                              "cache_read_input_tokens": 500, "cache_creation_input_tokens": 0, **(usage or {})},
                    "content": [
                        {"type": "tool_use", "id": "t1", "name": "Write",
                         "input": {"file_path": os.path.join(self.proj, "index.html"), "content": "x"}},
                        {"type": "tool_use", "id": "t2", "name": "Bash", "input": {"command": "ls"}},
                        {"type": "tool_use", "id": "t3", "name": "Edit",
                         "input": {"file_path": os.path.join(self.proj, "broken.js"), "old_string": "a", "new_string": "b"}},
                    ]}},
                {"type": "user", "timestamp": ts(2), "message": {"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": "t3", "is_error": True, "content": "no match"}]}},
                {"type": "user", "timestamp": ts(3), "message": {"role": "user", "content": [
                    {"type": "text", "text": "[Request interrupted by user]"}]}},
                {"type": "user", "timestamp": ts(4), "message": {"role": "user", "content": second}},
                {"type": "assistant", "timestamp": ts(5), "message": {
                    "id": "m2", "model": "claude-opus-5-5",
                    "usage": {"input_tokens": 300, "output_tokens": 100,
                              "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
                    "content": [{"type": "text", "text": said}]}},
                {"type": "cost-state", "startTime": 1, "totalCostUSD": total, "totalAPIDuration": 90000,
                 "modelUsage": {"claude-opus-5-5": {"inputTokens": 1300, "outputTokens": 300,
                                                    "cacheReadInputTokens": 500, "cacheCreationInputTokens": 0,
                                                    "costUSD": total}}},
            ]  # fmt: skip
            if resumed:  # opened again later: Claude Code starts a new running total
                entries.append(
                    {"type": "cost-state", "startTime": 2, "totalCostUSD": 0.5, "totalAPIDuration": 30000,
                     "modelUsage": {"claude-opus-5-5": {"inputTokens": 10, "outputTokens": 10,
                                                        "cacheReadInputTokens": 0, "cacheCreationInputTokens": 0,
                                                        "costUSD": 0.5}}})  # fmt: skip
        folder = os.path.join(self.claude_dir, "projects", slug(self.proj))
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"{name}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write("".join(json.dumps(e) + "\n" for e in entries))
        if (
            subagent
        ):  # a subagent's own log: it wrote style.css, and its write of gone.css failed
            sub = os.path.join(folder, name, "subagents")
            os.makedirs(sub, exist_ok=True)
            with open(os.path.join(sub, "agent-a.jsonl"), "w", encoding="utf-8") as f:
                f.write("".join(json.dumps(e) + "\n" for e in [
                    {"type": "assistant", "timestamp": ts(2), "isSidechain": True, "message": {
                        "id": "sa1", "model": "claude-opus-5-5",
                        "usage": {"input_tokens": 1000, "output_tokens": 0},
                        "content": [
                            {"type": "tool_use", "id": "s1", "name": "Write",
                             "input": {"file_path": os.path.join(self.proj, "style.css"), "content": "b{}"}},
                            {"type": "tool_use", "id": "s2", "name": "Write",
                             "input": {"file_path": os.path.join(self.proj, "gone.css"), "content": "?"}}]}},
                    {"type": "user", "timestamp": ts(2), "isSidechain": True, "message": {"role": "user", "content": [
                        {"type": "tool_result", "tool_use_id": "s2", "is_error": True, "content": "denied"}]}},
                ]))  # fmt: skip
        with open(
            os.path.join(self.claude_dir, ".claude.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(
                {
                    "oauthAccount": {
                        "organizationType": "claude_max",
                        "emailAddress": "me@example.com",
                    }
                },
                f,
            )
        return path

    def codex_log(self, provider="ollama", model="gpt-oss:20b", usage=None):
        usage = usage or {
            "input_tokens": 900,
            "cached_input_tokens": 100,
            "output_tokens": 80,
        }
        entries = [
            {"type": "session_meta", "timestamp": T0, "payload": {
                "id": "cx1", "cwd": self.proj, "cli_version": "0.130.0", "model_provider": provider,
                "base_instructions": {"text": "You are Codex."}, "git": {"commit_hash": "abc123"}}},
            {"type": "turn_context", "timestamp": ts(0), "payload": {
                "model": model, "effort": "medium", "approval_policy": "on-request",
                "sandbox_policy": {"type": "workspace-write", "network_access": False}}},
            {"type": "event_msg", "timestamp": ts(0), "payload": {"type": "task_started"}},
            {"type": "response_item", "timestamp": ts(0), "payload": {
                "type": "message", "role": "user", "content": [{"type": "input_text", "text": "Add a test"}]}},
            {"type": "response_item", "timestamp": ts(1), "payload": {
                "type": "function_call", "name": "exec_command", "call_id": "c1", "arguments": "{}"}},
            {"type": "event_msg", "timestamp": ts(1), "payload": {"type": "exec_command_end", "exit_code": 1}},
            {"type": "response_item", "timestamp": ts(2), "payload": {
                "type": "custom_tool_call", "name": "apply_patch", "call_id": "c2", "input": "*** Begin Patch"}},
            {"type": "event_msg", "timestamp": ts(2), "payload": {
                "type": "patch_apply_end", "success": True,
                "changes": {os.path.join(self.proj, "test_a.py"): {"type": "add"}}}},
            {"type": "event_msg", "timestamp": ts(3), "payload": {"type": "token_count", "info": {
                "total_token_usage": usage, "last_token_usage": usage}}},
            {"type": "event_msg", "timestamp": ts(4), "payload": {"type": "turn_aborted", "reason": "interrupted"}},
            {"type": "event_msg", "timestamp": ts(4), "payload": {"type": "task_complete", "duration_ms": 60000}},
        ]  # fmt: skip
        folder = os.path.join(self.codex_dir, "sessions", "2026", "10", "09")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "rollout-2026-10-09T14-00-00-abc.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write("".join(json.dumps(e) + "\n" for e in entries))
        return path

    def opencode_db(self):
        folder = os.path.join(self.data_dir, "opencode")
        os.makedirs(folder, exist_ok=True)
        db = sqlite3.connect(os.path.join(folder, "opencode.db"))
        db.executescript(
            """create table session (id text primary key, parent_id text, directory text, version text,
                 agent text, permission text, time_updated integer);
               create table message (id text primary key, session_id text, time_created integer, data text);
               create table part (id text primary key, message_id text, session_id text,
                 time_created integer, data text);"""
        )
        t = 1791640800000
        db.execute(
            "insert into session values ('ses_1', null, ?, '1.18.31', 'build', null, ?)",
            (self.proj, t + 9000),
        )
        msgs = [
            ("m1", t, {"role": "user", "time": {"created": t}}),
            ("m2", t + 1000, {"role": "assistant", "modelID": "qwen3:8b", "providerID": "ollama", "cost": 0,
                              "time": {"created": t + 1000, "completed": t + 5000},
                              "tokens": {"input": 400, "output": 50, "reasoning": 10, "cache": {"read": 0, "write": 0}}}),
            ("m3", t + 6000, {"role": "user", "time": {"created": t + 6000}}),
            ("m4", t + 7000, {"role": "assistant", "modelID": "qwen3:8b", "providerID": "ollama", "cost": 0,
                              "time": {"created": t + 7000}, "error": {"name": "MessageAbortedError"}}),
        ]  # fmt: skip
        for mid, created, data in msgs:
            db.execute(
                "insert into message values (?, 'ses_1', ?, ?)",
                (mid, created, json.dumps(data)),
            )
        parts = [
            ("p1", "m1", {"type": "text", "text": "Write a haiku file"}),
            ("p2", "m2", {"type": "tool", "tool": "write", "state": {"status": "completed",
                                                                     "input": {"filePath": "/x/haiku.txt"}}}),
            ("p3", "m2", {"type": "tool", "tool": "bash", "state": {"status": "error", "input": {}}}),
            ("p4", "m3", {"type": "text", "text": "again"}),
        ]  # fmt: skip
        for pid, mid, data in parts:
            created = next(c for m, c, _ in msgs if m == mid)
            db.execute(
                "insert into part values (?, ?, 'ses_1', ?, ?)",
                (pid, mid, created, json.dumps(data)),
            )
        db.commit()
        db.close()


class Receipts(Base):
    def test_claude_code_receipt(self):
        self.claude_log()
        out = self.ok().stdout
        self.assertIn("Receipt v5.0 · Claude Code 2.1.300", out)
        self.assertIn(
            "2 prompts from me", out
        )  # the "[Request interrupted" line isn't a prompt
        self.assertIn("$1.23", out)
        self.assertIn("billing  Max plan", out)
        self.assertIn("1 failed call", out)
        self.assertIn("interrupted 1×", out)
        self.assertIn(
            "files    1 file written or edited (.html)", out
        )  # the failed Edit doesn't count
        self.assertNotIn("me@example.com", out)

    def test_config_dir_is_honoured(self):
        self.claude_log()
        self.ok()  # found in CLAUDE_CONFIG_DIR...
        env = dict(self.env)
        del env["CLAUDE_CONFIG_DIR"]
        p = self.run_receipt(
            env=env
        )  # ...and not without it, so the variable is what found it
        self.assertEqual(p.returncode, 1)
        self.assertIn("no Claude Code session found", p.stderr)

    def test_wrong_folder_points_elsewhere(self):
        self.claude_log()
        p = self.run_receipt(cwd=self.other)
        self.assertEqual(p.returncode, 1)
        self.assertIn("1 session from 1 other folder", p.stderr)
        self.assertIn("--list --all", p.stderr)
        listed = self.ok("--list", "--all", cwd=self.other).stdout
        self.assertIn("Make a page for my habit tracker", listed)
        self.assertIn(
            "2 prompts from me", self.ok("--all", "--pick", "1", cwd=self.other).stdout
        )

    def test_other_tool_here_is_named(self):
        self.codex_log()
        p = self.run_receipt()
        self.assertEqual(p.returncode, 1)
        self.assertIn("this folder has 1 Codex CLI session: add --codex", p.stderr)

    def test_codex_local_model(self):
        self.codex_log()
        out = self.ok("--codex").stdout
        self.assertIn("gpt-oss:20b via ollama (on this computer)", out)
        self.assertIn("billing  none: the model ran on this computer", out)
        self.assertIn("1 failed call", out)
        self.assertIn("interrupted 1×", out)
        self.assertIn("1 file written or edited (.py)", out)
        self.assertIn("tokens   in 900 (100 cached) · out 80", out)

    def test_opencode(self):
        self.opencode_db()
        out = self.ok("--opencode").stdout
        self.assertIn("Receipt v5.0 · OpenCode 1.18.31", out)
        self.assertIn("qwen3:8b (ollama, on this computer)", out)
        self.assertIn("2 prompts from me", out)
        self.assertIn("1 failed call", out)
        self.assertIn("interrupted 1×", out)
        self.assertIn("1 file written or edited (.txt)", out)
        self.assertIn("out 60", out)  # output + reasoning
        self.assertIn(
            "2 prompts", self.ok("ses_1").stdout
        )  # an OpenCode id works as SESSION

    def test_last_prompt_only(self):
        self.claude_log()
        out = self.ok("--last", "1").stdout
        self.assertIn("last prompt", out)
        self.assertIn("1 prompt from me", out)

    # ---------- privacy ----------

    def test_prompt_with_email_stops(self):
        self.claude_log(
            prompt="Look in /home/jane/proj and mail me@example.com the result"
        )
        p = self.run_receipt("--prompt")
        self.assertEqual(p.returncode, 1)
        self.assertIn("1 email address", p.stderr)
        self.assertNotIn("me@example.com", p.stdout + p.stderr)
        out = self.ok(
            "--prompt", "--redact"
        ).stdout  # positive control: the same prompt, redacted
        self.assertIn("Look in ~/proj and mail [email] the result", out)

    def test_home_in_claude_folder_names_is_hidden(self):
        # Claude Code names project folders after their path: ~/.claude/projects/-home-jane-site/
        self.claude_log(
            prompt="read ~/.claude/projects/-home-jane/memory and C--Users-jane-site/notes"
        )
        out = self.ok("--prompt").stdout
        self.assertNotIn("jane", out)
        self.assertIn("read ~/.claude/projects/~/memory and ~-site/notes", out)

    def test_prompt_with_key_stops(self):
        self.claude_log(prompt="use sk-ant-api03-abcdefghijklmnopqrstuvwxyz0123 for it")
        p = self.run_receipt("--prompt")
        self.assertEqual(p.returncode, 1)
        self.assertIn("1 key-like string", p.stderr)
        self.assertIn("use [key] for it", self.ok("--prompt", "--redact").stdout)

    def test_plain_prompt_prints(self):
        self.claude_log(
            prompt="Draw a cat, commit 3f2a9c1d8e7b6a5f4e3d2c1b0a9f8e7d6c5b4a39"
        )
        self.assertIn(
            "Draw a cat, commit 3f2a9c1d", self.ok("--prompt").stdout
        )  # a git hash isn't a key
        self.claude_log(
            prompt="word " * 40
        )  # wrapped to 80 columns after the label, as in the README
        self.assertIn(
            "prompts  1  " + "word " * 14 + "word\n", self.ok("--prompt").stdout
        )

    def test_json_leaves_out_hidden_and_private(self):
        self.claude_log()
        r = json.loads(self.ok("--json", "--hide", "cost,billing").stdout)
        for k in (
            "cost_usd",
            "billing",
            "first_prompt",
            "file_names",
            "cwd",
            "prompt_id",
        ):
            self.assertNotIn(k, r)
        self.assertEqual(r["receipt_version"], "5.0")
        self.assertEqual(r["tool_errors"], 1)
        names = json.loads(self.ok("--json", "--file-names").stdout)["file_names"]
        self.assertEqual(names, ["index.html"])

    # ---------- checks ----------

    def test_unfamiliar_log_warns(self):
        self.claude_log(replies=False)
        p = self.ok()
        self.assertIn("found your prompts but no model reply", p.stderr)
        self.assertIn("warning  found your prompts but no model reply", p.stdout)

    def test_version(self):
        self.assertEqual(self.ok("--version").stdout.strip(), "receipt.py 5.0")

    # ---------- output ----------

    def test_png(self):
        self.claude_log()
        path = os.path.join(self.home, "r.png")
        self.ok("--out", path)
        with open(path, "rb") as f:
            data = f.read()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        pos, kinds, idat = 8, [], b""
        while pos < len(data):
            n, kind = struct.unpack(">I4s", data[pos : pos + 8])
            body = data[pos + 8 : pos + 8 + n]
            crc = struct.unpack(">I", data[pos + 8 + n : pos + 12 + n])[0]
            self.assertEqual(crc, zlib.crc32(kind + body) & 0xFFFFFFFF)
            kinds.append(kind)
            if kind == b"IHDR":
                w, h = struct.unpack(">II", body[:8])
            if kind == b"IDAT":
                idat += body
            pos += 12 + n
        self.assertEqual(kinds, [b"IHDR", b"PLTE", b"IDAT", b"IEND"])
        self.assertEqual(len(zlib.decompress(idat)), h * (w + 1))
        self.assertGreater(w, 600)

    def test_report_link(self):
        self.claude_log()
        out = self.ok("--report").stdout
        url = out.strip().split("\n")[-1]
        self.assertTrue(url.startswith("https://docs.google.com/forms/"), url)
        self.assertIn("entry.349092046=tool", url)
        self.assertIn("entry.1393206370=Receipt%20v5.0", url)

    def test_hook_saves_a_receipt(self):
        log = self.claude_log()
        folder = os.path.join(self.home, "receipts")
        payload = json.dumps(
            {
                "session_id": "s1",
                "transcript_path": log,
                "hook_event_name": "SessionEnd",
            }
        )
        p = self.ok("--hook", "--out", folder + os.sep, stdin=payload)
        self.assertEqual(p.stdout, "")
        saved = os.listdir(folder)
        self.assertEqual(len(saved), 1)
        with open(os.path.join(folder, saved[0]), encoding="utf-8") as f:
            self.assertIn("Receipt v5.0 · Claude Code", f.read())

    def test_combine_and_compare(self):
        self.claude_log()
        self.codex_log()
        a, b = os.path.join(self.home, "a.json"), os.path.join(self.home, "b.json")
        self.ok("--prompt-id", "--out", a)
        self.ok("--codex", "--prompt-id", "--out", b)
        out = self.ok("--combine", a, b).stdout
        self.assertIn("2 receipts added up", out)
        self.assertIn("3 prompts from me", out)
        self.assertIn("$1.23 (1 of 2 receipts have a cost", out)
        self.assertIn("Claude Code 2.1.300 + Codex CLI 0.130.0", out)
        cmp_ = self.ok("--compare", a, b).stdout
        self.assertIn("2 runs · different prompts", cmp_)
        self.assertIn("2 runs · the same prompt", self.ok("--compare", a, a).stdout)


class LineItems(Base):
    """the itemized cost, and the checks a real receipt has"""

    def test_lines_add_up_or_say_by_how_much(self):
        # opus 5.5: 1,300 in × $4/M + 500 cache read × $0.20/M + 300 out × $20/M = $0.0113
        self.claude_log(total=0.0113)
        out = self.ok().stdout
        self.assertIn("the lines below add up to it", out)
        self.assertRegex(out, r"output +300 × \$20\.00/M +\$0\.01")
        self.assertIn(
            "prices   API list prices per million tokens ($/M), from LiteLLM", out
        )
        self.assertNotIn("check    ", out)
        self.claude_log(
            total=1.234
        )  # a total the calls can't explain is shown, not hidden
        out = self.ok().stdout
        self.assertIn("check    the lines add up to $0.01, not $1.23", out)
        self.assertNotIn("add up to it", out)

    def test_surcharges(self):
        # fast mode ×2 and US-only ×1.1 on opus 5.5's $20/M output
        self.claude_log(usage={"speed": "fast", "inference_geo": "us"})
        out = self.ok().stdout
        self.assertRegex(out, r"output +200 × \$44\.00/M")
        self.assertRegex(
            out, r"output +100 × \$20\.00/M"
        )  # control: the next call was neither
        self.assertIn(
            "extras   fast mode on 1 call · US-only processing on 1 call", out
        )
        # a call over 200k input tokens is billed at sonnet 4.5's long-context rates
        self.claude_log(model="claude-sonnet-4-5", usage={"input_tokens": 250000})
        self.assertRegex(self.ok().stdout, r"input +250k × \$6\.00/M")
        self.claude_log(model="claude-sonnet-4-5", usage={"input_tokens": 150000})
        self.assertRegex(self.ok().stdout, r"input +150k × \$3\.00/M")

    def test_resumed_session_adds_up_each_time_it_was_opened(self):
        self.claude_log(total=1.0, resumed=True)
        out = self.ok().stdout
        self.assertIn(
            "cost     $1.50 (Claude Code's own total at API prices, added up over the 2",
            out,
        )
        self.claude_log(total=1.0)  # control: opened once
        self.assertIn(
            "cost     $1.00 (Claude Code's own total at API prices)", self.ok().stdout
        )

    def test_last_prompts_are_priced_from_their_own_calls(self):
        self.claude_log(total=1.234)
        out = self.ok("--last", "1").stdout
        # the last prompt's call only: 300 in × $4/M + 100 out × $20/M = $0.0032
        self.assertIn(
            "cost     <$0.01 (worked out from the logged calls at API prices; Claude Code's own total",
            out,
        )
        self.assertIn("$1.23", out)

    def test_receipt_number_and_time(self):
        self.claude_log(name="s1")
        first = self.ok().stdout.split("\n")[0]
        self.assertRegex(
            first,
            r"· 9 Oct 2026, \d{1,2}:\d{2} [AP]M \S+ · no\. [0-9a-f]{4}-[0-9a-f]{4}$",
        )
        self.assertEqual(
            first, self.ok().stdout.split("\n")[0]
        )  # the same session, the same number
        os.remove(
            os.path.join(self.claude_dir, "projects", slug(self.proj), "s1.jsonl")
        )
        self.claude_log(name="s2")
        other = self.ok().stdout.split("\n")[0]
        self.assertNotEqual(first.split("no. ")[1], other.split("no. ")[1])
        self.assertNotRegex(self.ok("--hide", "time").stdout.split("\n")[0], r"[AP]M")

    def test_codex_cost_is_worked_out(self):
        self.codex_log(
            provider="openai",
            model="gpt-5.6-sol",
            usage={
                "input_tokens": 100000,
                "cached_input_tokens": 40000,
                "output_tokens": 5000,
            },
        )
        out = self.ok("--codex").stdout
        # 60k × $4/M + 40k cached × $0.40/M + 5k × $20/M = $0.356
        self.assertIn(
            "cost     $0.36 (worked out from the logged calls at API prices; Codex logs no price)",
            out,
        )
        self.assertRegex(out, r"cache read +40k × \$0\.40/M +\$0\.02")
        self.codex_log()  # control: a model on this computer has no price
        self.assertIn(
            "cost     none: the model ran on this computer", self.ok("--codex").stdout
        )

    def test_prices_file(self):
        self.claude_log(total=0.0113)
        prices = os.path.join(self.home, "prices.json")
        with open(prices, "w", encoding="utf-8") as f:
            json.dump({"claude-opus-5-5": {"litellm_provider": "anthropic", "input_cost_per_token": 4e-6,
                                           "output_cost_per_token": 1e-4}}, f)  # fmt: skip
        out = self.ok("--prices", prices).stdout
        self.assertRegex(out, r"output +300 × \$100\.00/M +\$0\.03")
        self.assertIn("from prices.json, given with --prices", out)
        with open(prices, "w", encoding="utf-8") as f:
            json.dump({"some-model": {}}, f)
        p = self.run_receipt("--prices", prices)
        self.assertEqual(p.returncode, 1)
        self.assertIn("no Anthropic or OpenAI prices", p.stderr)

    def test_hiding_the_lines(self):
        self.claude_log()
        out = self.ok("--hide", "items").stdout
        self.assertIn("cost     $1.23", out)
        self.assertNotIn("prices   ", out)
        self.assertNotIn(
            "items", json.loads(self.ok("--json", "--hide", "items").stdout)
        )
        out = self.ok("--hide", "cost").stdout  # the lines would give the total away
        self.assertNotIn("$/M", out)
        self.assertIn("$/M", self.ok().stdout)

    def test_combine_adds_up_lines(self):
        self.claude_log(total=0.0113)
        a = os.path.join(self.home, "a.json")
        self.ok("--out", a)
        r = json.loads(self.ok("--combine", a, a, "--json").stdout)
        out_line = next(i for i in r["items"] if i["kind"] == "output")
        self.assertEqual(out_line["count"], 600)
        self.assertEqual(r["cost_check"], {"lines_usd": 0.0226, "own_usd": 0.0226})


class Records(Base):
    """--record: fingerprints of what went in and came out; --verify and --sign"""

    def make(self, *extra):
        self.claude_log(rich=True)
        rec = os.path.join(self.home, "rec.json")
        out = self.ok("--record", rec, *extra).stdout
        with open(rec, "rb") as f:
            data = f.read()
        return rec, data, json.loads(data), out

    def test_record_holds_hashes_not_text(self):
        rec, data, stmt, out = self.make()
        h = lambda s: hashlib.sha256(s.encode()).hexdigest()  # noqa: E731
        self.assertEqual(stmt["_type"], "https://in-toto.io/Statement/v1")
        pred = stmt["predicate"]
        self.assertEqual(
            [p["sha256"] for p in pred["prompts"]],
            [h("Make a page for my habit tracker"), h("now make it blue")],
        )
        self.assertEqual(
            pred["instructions"], [{"name": "CLAUDE.md", "sha256": h("be kind")}]
        )
        self.assertEqual(
            pred["system_prompt"], [{"sha256": h("You are Claude Code.\n\nBe brief.")}]
        )
        read = next(e for e in pred["tool_results"] if e["tool"] == "Read")
        self.assertEqual(
            (read["file"], read["file_sha256"], read["lines"]),
            (".txt", h("hello"), "1-1 of 1"),
        )
        self.assertEqual(
            stmt["subject"][0]["digest"]["sha256"], h("x")
        )  # index.html as the Write wrote it
        self.assertEqual(
            stmt["subject"][0]["name"], "file1.html"
        )  # no names without --file-names
        # one byte form: the record's own hash is the hash of the file, and it's printed on the receipt
        self.assertEqual(
            data,
            json.dumps(
                stmt, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode(),
        )
        self.assertIn(f"record   sha256 {hashlib.sha256(data).hexdigest()[:16]}…", out)
        for private in (
            b"habit tracker",
            b"be kind",
            b"hello",
            b"me@example.com",
            self.home.encode(),
            b"workingDirectory",
        ):
            self.assertNotIn(private, data)
        # --hide reaches the record too
        _, _, hidden, _ = self.make("--hide", "model,cost")
        self.assertNotIn("models", hidden["predicate"])
        self.assertNotIn("cost_micro_usd", hidden["predicate"])
        self.assertIn("models", pred)

    def test_verify_says_what_came_in_and_out(self):
        rec, _, _, _ = self.make()
        made = os.path.join(self.home, "index.html")
        read = os.path.join(self.home, "notes.txt")
        other = os.path.join(self.home, "other.html")
        for path, body in ((made, "x"), (read, "hello\n"), (other, "y")):
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
        p = self.run_receipt("--verify", rec, made, read)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("index.html: came out of the run", p.stdout)
        self.assertIn("notes.txt: went in: the model read it", p.stdout)
        p = self.run_receipt("--verify", rec, other)  # one byte different: not in it
        self.assertEqual(p.returncode, 1)
        self.assertIn("other.html: NOT in this record", p.stdout)

    def test_sign_and_verify(self):
        if not shutil.which("ssh-keygen"):
            self.skipTest("no ssh-keygen")
        key = os.path.join(self.home, "key")
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", key, "-C", "tester"],
            check=True,
        )
        out = os.path.join(self.home, "r.json")
        self.claude_log(rich=True)
        rec = os.path.join(self.home, "rec.json")
        self.ok("--out", out, "--record", rec, "--sign", key)
        for f in (out, rec):
            self.assertTrue(os.path.exists(f + ".sig"))
            p = self.ok("--verify", f)
            self.assertIn("good signature", p.stdout)
        with open(key + ".pub", encoding="utf-8") as f:
            pub = f.read().split()
        signers = os.path.join(self.home, "allowed_signers")
        with open(signers, "w", encoding="utf-8") as f:
            f.write(f'tester namespaces="prompt-receipts" {pub[0]} {pub[1]}\n')
        self.assertIn(
            "good signature by tester",
            self.ok("--verify", rec, "--signers", signers).stdout,
        )
        with open(out, "a", encoding="utf-8") as f:
            f.write(" ")  # one byte added after signing
        p = self.run_receipt("--verify", out)
        self.assertEqual(p.returncode, 1)
        self.assertIn("BAD signature", p.stdout)

    def test_codex_record(self):
        self.codex_log()
        rec = os.path.join(self.home, "rec.json")
        self.ok("--codex", "--record", rec)
        with open(rec, encoding="utf-8") as f:
            pred = json.load(f)["predicate"]
        self.assertEqual(pred["git_commit"], "abc123")
        self.assertEqual(
            pred["system_prompt"],
            [{"sha256": hashlib.sha256(b"You are Codex.").hexdigest()}],
        )
        self.assertEqual(len(pred["prompts"]), 1)


class Turns(Base):
    """--turns, every prompt, --reply, --outcome, --recipe"""

    def test_one_line_per_prompt(self):
        self.claude_log(total=0.0113)
        out = self.ok("--turns").stdout
        # turn 1: 1,000 in + 500 cached + 200 out = $0.0081; turn 2: 300 in + 100 out = $0.0032
        self.assertRegex(
            out,
            r"\nturns    1  \d+:\d\d [AP]M · 3 min · \$0\.01 · 3 tool calls, 1 shell command · 1 file\n",
        )
        self.assertRegex(
            out, r"\n         2  \d+:\d\d [AP]M · 60 s · <\$0\.01 · 0 tool calls\n"
        )
        self.assertIn("         the turns add up to the cost above", out)
        self.claude_log(
            total=1.234
        )  # Claude Code's total disagrees with its calls: the turns say what they match
        self.assertIn(
            "the turns add up to $0.01, as the priced lines do",
            self.ok("--turns").stdout,
        )
        self.assertNotIn("turns    ", self.ok().stdout)  # control: only when asked
        hidden = self.ok("--turns", "--hide", "cost,time").stdout.split("turns    ")[1]
        self.assertNotIn("$", hidden)
        self.assertNotRegex(hidden, r"[AP]M|min")

    def test_a_range_of_prompts(self):
        self.claude_log(total=0.0113)
        out = self.ok("--turns", "2").stdout
        self.assertIn("· prompt 2 ·", out.split("\n")[0])
        self.assertIn("1 prompt from me", out)
        self.assertRegex(out, r"\nturns    2  ")
        self.assertNotRegex(out, r"\n +1  ")
        self.assertNotIn(
            "· prompt", self.ok("--turns", "1-2").stdout.split("\n")[0]
        )  # all of them: the whole session
        for bad in ("3", "x", "0-1"):
            p = self.run_receipt("--turns", bad)
            self.assertEqual(p.returncode, 1, bad)
        p = self.run_receipt("--last", "1", "--turns", "1")
        self.assertIn("pick one of --last N and --turns A-B", p.stderr)
        rec = os.path.join(self.home, "rec.json")
        self.ok("--turns", "2", "--record", rec)
        with open(rec, encoding="utf-8") as f:
            pred = json.load(f)["predicate"]
        self.assertEqual(
            pred["prompts"],
            [{"sha256": hashlib.sha256(b"now make it blue").hexdigest()}],
        )

    def test_every_prompt_is_shown_and_checked(self):
        self.claude_log()
        out = self.ok("--prompt").stdout
        self.assertIn(
            "prompts  1  Make a page for my habit tracker\n         2  now make it blue",
            out,
        )
        self.assertIn(
            "prompt   now make it blue", self.ok("--prompt", "--last", "1").stdout
        )
        out = self.ok("--prompt", "--turns").stdout
        self.assertRegex(out, r"\n         2  [^\n]*\n            now make it blue")
        self.claude_log(
            second="send it to me@example.com"
        )  # a later prompt is checked like the first
        p = self.run_receipt("--prompt")
        self.assertEqual(p.returncode, 1)
        self.assertNotIn("me@example.com", p.stdout + p.stderr)
        self.assertIn("send it to [email]", self.ok("--prompt", "--redact").stdout)

    def test_reply_and_outcome(self):
        self.claude_log(said="Made index.html; it's blue now.")
        out = self.ok("--reply", "--outcome", "worked first try").stdout
        self.assertIn("reply    Made index.html; it's blue now.", out)
        self.assertIn("outcome  worked first try (the sender's own words)", out)
        path = "~/dev-mods/462b7ab3-b198-4b84/sleepy-owl/index.html"  # where a line would break it at a hyphen
        self.claude_log(said="word " * 12 + path)
        self.assertIn(
            "\n         " + path + "\n", self.ok("--reply").stdout
        )  # a path stays whole when wrapped
        self.assertNotIn(
            "blue now", self.ok().stdout
        )  # control: the reply stays off unless asked
        self.claude_log(said="mailed me@example.com")
        p = self.run_receipt("--reply")
        self.assertEqual(p.returncode, 1)
        self.assertIn("the model's reply holds 1 email address", p.stderr)
        p = self.run_receipt("--outcome", "ask me@example.com")
        self.assertEqual(p.returncode, 1)
        self.assertIn("mailed [email]", self.ok("--reply", "--redact").stdout)

    def test_recipe_reruns_each_prompt(self):
        self.claude_log(second="don't use red")
        out = self.ok("--recipe").stdout
        lines = [l for l in out.split("\n") if "claude -p" in l]
        self.assertEqual(len(lines), 2)
        first, second = (
            shlex.split(l.strip().removeprefix("rerun").strip()) for l in lines
        )
        self.assertEqual(
            first,
            [
                "claude",
                "-p",
                "Make a page for my habit tracker",
                "--model",
                "claude-opus-5-5",
                "--effort",
                "high",
            ],
        )
        self.assertEqual(
            second[:4], ["claude", "-p", "-c", "don't use red"]
        )  # quoted so the shell gives it back whole
        self.assertIn("no seed or temperature", out)
        path = self.claude_log(
            model="claude-sonnet-5-5"
        )  # models switched between prompts: each reruns on its own
        with open(path, encoding="utf-8") as f:
            log = f.read().replace(
                '"permissionMode": "default"', '"permissionMode": "acceptEdits"'
            )
        with open(path, "w", encoding="utf-8") as f:
            f.write(log)
        out = self.ok("--recipe").stdout
        cmds = [
            shlex.split(l.strip().removeprefix("rerun").strip())
            for l in out.split("\n")
            if "claude -p" in l
        ]
        self.assertEqual(
            [c[c.index("--model") + 1] for c in cmds],
            ["claude-sonnet-5-5", "claude-opus-5-5"],
        )
        self.assertIn("--permission-mode acceptEdits", out)
        for hidden in (
            self.ok("--recipe", "--hide", "model,settings").stdout,
            json.dumps(
                json.loads(
                    self.ok("--recipe", "--hide", "model,settings", "--json").stdout
                )["recipe"]
            ),
        ):
            self.assertIn("claude -p", hidden)
            self.assertNotRegex(hidden, r"--model|--effort|--permission-mode|claude-opus")  # fmt: skip
        out = self.ok("--recipe", "--rename", "claude-opus-5-5=big").stdout
        self.assertIn("-c 'now make it blue' --model big", out)
        self.assertNotIn("claude-opus", out)
        self.codex_log()
        out = self.ok("--codex", "--recipe").stdout
        self.assertIn(
            "rerun    codex exec -m gpt-oss:20b -c model_reasoning_effort=medium 'Add a test'",
            out,
        )
        self.opencode_db()
        out = self.ok("--opencode", "--recipe").stdout
        self.assertIn(
            "rerun    opencode run -m ollama/qwen3:8b --agent build 'Write a haiku file'",
            out,
        )
        self.assertIn(
            "         opencode run -c -m ollama/qwen3:8b --agent build again", out
        )

    def test_codex_and_opencode_turns(self):
        self.codex_log(provider="openai", model="gpt-5.6-sol")
        out = self.ok("--codex", "--turns").stdout
        self.assertRegex(
            out,
            r"turns    1  \d+:\d\d [AP]M · 60 s · <\$0\.01 · 2 tool calls, 1 shell command · 1 file",
        )
        self.opencode_db()
        out = self.ok("--opencode", "--turns").stdout
        self.assertRegex(
            out,
            r"turns    1  [^\n]*· 2 tool calls, 1 shell command · 1 file\n         2  [^\n]*0 tool calls",
        )
        self.assertNotIn(
            "$", out.split("turns    ")[1]
        )  # a model on this computer has no price

    def test_files_written_by_subagents(self):
        self.claude_log(subagent=True, rich=True)
        out = self.ok("--file-names").stdout
        self.assertIn(
            "files    2 files written or edited (index.html, style.css)", out
        )  # not gone.css: it failed
        shutil.rmtree(
            os.path.join(self.claude_dir, "projects", slug(self.proj), "s1")
        )  # control: no subagent
        self.assertIn(
            "files    1 file written or edited (index.html)",
            self.ok("--file-names").stdout,
        )
        self.claude_log(subagent=True, rich=True)
        rec = os.path.join(self.home, "rec.json")
        self.ok("--record", rec)
        with open(rec, encoding="utf-8") as f:
            stmt = json.load(f)
        self.assertIn(
            hashlib.sha256(b"b{}").hexdigest(),
            [s["digest"]["sha256"] for s in stmt["subject"]],
        )
        self.assertEqual(len(stmt["subject"]), 2)

    def test_a_turn_starts_at_its_prompt(self):
        self.claude_log(subagent=True)
        sub = os.path.join(
            self.claude_dir,
            "projects",
            slug(self.proj),
            "s1",
            "subagents",
            "agent-a.jsonl",
        )
        with open(
            sub, "a", encoding="utf-8"
        ) as f:  # a subagent call stamped the moment prompt 2 was sent
            f.write(json.dumps({"type": "assistant", "timestamp": ts(4), "isSidechain": True, "message": {
                "id": "sa2", "model": "claude-opus-5-5", "usage": {"input_tokens": 0, "output_tokens": 10000},
                "content": [{"type": "text", "text": "ok"}]}}) + "\n")  # fmt: skip
        rows = json.loads(self.ok("--turns", "--json").stdout)["turns"]
        first = json.loads(self.ok("--turns", "1", "--json").stdout)
        second = json.loads(self.ok("--turns", "2", "--json").stdout)
        self.assertGreater(
            rows[1]["cost_usd"], 0.1
        )  # 10,000 output tokens: prompt 2's, subagent or not
        self.assertLess(rows[0]["cost_usd"], 0.05)
        self.assertEqual(
            first["cost_usd"], rows[0]["cost_usd"]
        )  # a part stops where the next prompt starts
        self.assertEqual(second["cost_usd"], rows[1]["cost_usd"])

    def test_record_holds_each_reply(self):
        self.claude_log(rich=True)
        rec = os.path.join(self.home, "rec.json")
        self.ok("--record", rec)
        with open(rec, encoding="utf-8") as f:
            pred = json.load(f)["predicate"]
        self.assertEqual(
            pred["replies"],
            [{"turn": 2, "sha256": hashlib.sha256(b"done").hexdigest()}],
        )
        said = os.path.join(self.home, "said.txt")
        with open(said, "w", encoding="utf-8") as f:
            f.write("done\n")
        self.assertIn(
            "came out: the model's reply to prompt 2",
            self.ok("--verify", rec, said).stdout,
        )


class Sharing(Base):
    """--link and --bundle"""

    def test_link_carries_the_receipt(self):
        self.claude_log()
        p = self.ok("--link")
        receipt, _, url = p.stdout.rstrip("\n").rpartition("\n")
        self.assertTrue(
            url.startswith("https://musharna.github.io/prompt-receipts/r/#r1."), url
        )
        packed = url.split("#r1.")[1]
        self.assertRegex(
            packed, r"^[A-Za-z0-9_-]+$"
        )  # url-safe: + and / would break the link in chat apps
        text = zlib.decompress(
            base64.urlsafe_b64decode(packed + "=" * (-len(packed) % 4)), -15
        ).decode()
        self.assertEqual(
            text, receipt.split("\nlink (")[0].rstrip("\n")
        )  # the link holds what was printed
        self.assertNotIn("Discord", p.stderr)
        long = " ".join(
            hashlib.sha256(str(i).encode()).hexdigest()[:8] for i in range(400)
        )  # doesn't compress
        self.claude_log(prompt=long)  # a long receipt is still made, with a warning
        p = self.ok("--link", "--prompt")
        self.assertIn("Discord cuts messages at 2,000", p.stderr)

    def test_bundle(self):
        self.claude_log(rich=True)
        zp = os.path.join(self.home, "b.zip")
        self.ok("--bundle", zp, "--file-names")
        with zipfile.ZipFile(zp) as z:
            names = set(z.namelist())
            self.assertEqual(
                names,
                {"ro-crate-metadata.json", "ro-crate-preview.html", "receipt.txt", "receipt.json",
                 "record.json", "outputs/index.html"},
            )  # fmt: skip
            self.assertEqual(z.read("outputs/index.html"), b"x")
            meta = json.loads(z.read("ro-crate-metadata.json"))
            receipt_json = z.read("receipt.json")
            z.extractall(os.path.join(self.home, "unzipped"))
        graph = {e["@id"]: e for e in meta["@graph"]}
        self.assertEqual(meta["@context"], "https://w3id.org/ro/crate/1.2/context")
        self.assertEqual(graph["ro-crate-metadata.json"]["about"], {"@id": "./"})
        root = graph["./"]
        for k in ("name", "description", "datePublished", "license"):
            self.assertIn(k, root)
        self.assertEqual(graph["#run"]["result"], [{"@id": "outputs/index.html"}])
        files = {
            i for i, e in graph.items() if e["@type"] == "File"
        }  # rocrate-validator's required rules:
        self.assertEqual(
            {p["@id"] for p in root["hasPart"]}, files
        )  # every file entity is in hasPart, and back
        self.assertEqual(graph["outputs/index.html"]["contentSize"], "1")
        self.assertEqual(
            graph["#tool"]["url"], "https://github.com/anthropics/claude-code"
        )  # software needs a url
        self.assertNotIn(b"me@example.com", receipt_json)
        u = os.path.join(self.home, "unzipped")
        out = self.ok(
            "--verify",
            os.path.join(u, "record.json"),
            os.path.join(u, "outputs", "index.html"),
        ).stdout
        self.assertIn(
            "came out of the run", out
        )  # the bundle checks against its own record
        self.ok("--bundle", zp)
        with zipfile.ZipFile(zp) as z:
            self.assertIn(
                "outputs/file1.html", z.namelist()
            )  # no names unless --file-names
        p = self.run_receipt("--shot")
        self.assertIn("--shot goes into a --bundle", p.stderr)

    def test_shot_uses_a_browser(self):
        if os.name == "nt":
            self.skipTest("the stand-in browser is a shell script")
        self.claude_log(rich=True)
        with open(os.path.join(self.proj, "secret.txt"), "w", encoding="utf-8") as f:
            f.write("not the run's")  # next to the page, but the run didn't write it
        fake = os.path.join(self.home, "fake-browser")
        args = os.path.join(self.home, "args.txt")
        with open(
            fake, "w", encoding="utf-8"
        ) as f:  # asks for the page and for secret.txt, then makes a PNG
            f.write(f"#!{sys.executable}\n" + textwrap.dedent(f"""\
                import sys, urllib.request, urllib.error
                get = urllib.request.build_opener(urllib.request.ProxyHandler({{}})).open
                said = []
                for u in (sys.argv[-1], sys.argv[-1].rsplit("/", 1)[0] + "/secret.txt"):
                    try:
                        said.append("200 " + get(u, timeout=10).read().decode())
                    except urllib.error.HTTPError as e:
                        said.append(str(e.code))
                open({args!r}, "w").write("\\n".join(sys.argv[1:] + said))
                for a in sys.argv:
                    if a.startswith("--screenshot="):
                        open(a.split("=", 1)[1], "wb").write(b"\\x89PNG")
                """))  # fmt: skip
        os.chmod(fake, 0o755)
        zp = os.path.join(self.home, "b.zip")
        self.ok("--bundle", zp, "--shot", env=dict(self.env, RECEIPT_BROWSER=fake))
        with zipfile.ZipFile(zp) as z:
            self.assertEqual(z.read("preview.png"), b"\x89PNG")
            self.assertIn(b'src="preview.png"', z.read("ro-crate-preview.html"))
        with open(args, encoding="utf-8") as f:
            used = f.read().split("\n")
        self.assertIn("--headless", used)
        self.assertRegex(
            used[-3], r"^http://127\.0\.0\.1:\d+/index\.html$"
        )  # served, so module scripts run
        self.assertEqual(used[-2], "200 x")  # the page as the run wrote it
        self.assertEqual(used[-1], "404")  # and nothing it didn't write
        with open(fake, "w", encoding="utf-8") as f:
            f.write(
                "#!/bin/sh\nexit 0\n"
            )  # a browser that makes no picture fails loudly
        p = self.run_receipt(
            "--bundle", zp, "--shot", env=dict(self.env, RECEIPT_BROWSER=fake)
        )
        self.assertEqual(p.returncode, 1)
        self.assertIn("made no picture", p.stderr)


class PictureLines(unittest.TestCase):
    """how the picture breaks a long line under its label"""

    @classmethod
    def setUpClass(cls):
        import importlib.util

        spec = importlib.util.spec_from_file_location("receipt", RECEIPT)
        cls.receipt = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.receipt)

    def test_breaks_between_items_without_a_hanging_dot(self):
        fold = self.receipt.fold
        self.assertEqual(
            fold("13 tool calls · web 0 · lines +537 -0", 22),
            ["13 tool calls · web 0", "lines +537 -0"],
        )

    def test_keeps_a_bracketed_note_whole(self):
        fold = self.receipt.fold
        self.assertEqual(
            fold("Max plan: a flat fee (your account today)", 22),
            ["Max plan: a flat fee", "(your account today)"],
        )
        self.assertEqual(
            fold("MCP none (of 0 connected)", 30), ["MCP none (of 0 connected)"]
        )

    def test_does_not_split_names_at_hyphens(self):
        out = self.receipt.fold("claude-opus-5-5 and claude-haiku-4-5-20251001", 30)
        self.assertEqual(out, ["claude-opus-5-5 and", "claude-haiku-4-5-20251001"])


if __name__ == "__main__":
    unittest.main()
