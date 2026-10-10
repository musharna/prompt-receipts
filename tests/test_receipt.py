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
        self.assertIn("Receipt v7.0 · Claude Code 2.1.300", out)
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
        self.assertIn("Receipt v7.0 · OpenCode 1.18.31", out)
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
        self.assertEqual(r["receipt_version"], "7.0")
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
        self.assertEqual(self.ok("--version").stdout.strip(), "receipt.py 7.0")

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
        self.assertIn("entry.1393206370=Receipt%20v7.0", url)

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
            self.assertIn("Receipt v7.0 · Claude Code", f.read())

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
        self.assertIn("no Anthropic, OpenAI, Gemini or Qwen prices", p.stderr)

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
        path = self.claude_log(
            total=0.0613
        )  # plus background work Claude Code priced itself, with no calls logged
        with open(path, encoding="utf-8") as f:
            log = f.read().replace(
                '"costUSD": 0.0613}',
                '"costUSD": 0.0113}, "claude-haiku-5-5": {"costUSD": 0.05}',
            )
        with open(path, "w", encoding="utf-8") as f:
            f.write(log)
        self.assertIn("the turns add up to $0.01; the other $0.05 is background work the tool priced\n"
                      "         itself, not tied to one prompt", self.ok("--turns").stdout)  # fmt: skip
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
        self.claude_log(
            said="Open \\\\wsl.localhost\\Ubuntu\\home\\alice\\proj\\index.html in Edge"
        )
        out = self.ok(
            "--reply"
        ).stdout  # a WSL home as Windows names it is a home folder too
        self.assertIn("reply    Open ~\\proj\\index.html in Edge", out)
        self.assertNotIn("alice", out)
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


class Totals(Base):
    """--totals adds up prompts across sessions; three days, two folders, two models"""

    def call(self, at, mid, model, inp=0, out=0):
        return {"type": "assistant", "timestamp": at, "message": {"id": mid, "model": model,
                "usage": {"input_tokens": inp, "output_tokens": out, "cache_read_input_tokens": 0,
                          "cache_creation_input_tokens": 0}, "content": [{"type": "text", "text": "ok"}]}}  # fmt: skip

    def prompt(self, at, text, cwd):
        return {"type": "user", "timestamp": at, "cwd": cwd, "version": "2.1.300",
                "message": {"role": "user", "content": text}}  # fmt: skip

    def write(self, name, cwd, entries):
        folder = os.path.join(self.claude_dir, "projects", slug(cwd))
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"{name}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write("".join(json.dumps(e) + "\n" for e in entries))
        return path

    def setUp(self):
        super().setUp()
        opus, sonnet = "claude-opus-5-5", "claude-sonnet-5-5"
        self.a = self.write("a", self.proj, [
            self.prompt("2026-10-01T12:00:00.000Z", "make a page", self.proj),
            self.call("2026-10-01T12:01:00.000Z", "a1", opus, inp=1_000_000),  # $4.00
            self.prompt("2026-10-03T12:00:00.000Z", "make it blue", self.proj),
            self.call("2026-10-03T12:03:00.000Z", "a2", opus, out=100_000),  # $2.00
            # /compact: done in 2 minutes; then the session is reopened days later, which writes a
            # "<synthetic>" reply and bookkeeping entries that aren't the prompt's work
            self.prompt("2026-10-03T12:10:00.000Z", "/compact", self.proj),
            {"type": "system", "subtype": "compact_boundary", "timestamp": "2026-10-03T12:12:00.000Z"},
            {"type": "attachment", "timestamp": "2026-10-08T12:00:00.000Z", "attachment": {"type": "x"}},
            {"type": "assistant", "timestamp": "2026-10-08T12:00:01.000Z", "message": {
                "id": "syn", "model": "<synthetic>", "content": [{"type": "text", "text": "No response requested."}]}},
        ])  # fmt: skip
        self.write("b", self.other, [
            self.prompt("2026-10-03T12:00:00.000Z", "a game", self.other),
            self.call("2026-10-03T12:02:00.000Z", "b1", sonnet, inp=1_000_000),
        ])

    def test_by_day_in_this_folder(self):
        out = self.ok("--totals").stdout
        self.assertIn("Totals v7.0 · Claude Code · folder proj · 1 – 3 Oct 2026 · by day", out)
        self.assertRegex(out, r"\nThu 1 Oct 2026 +\$4\.00 +1 +1 ")
        self.assertRegex(out, r"\nSat 3 Oct 2026 +\$2\.00 +1 +2 ")
        self.assertRegex(out, r"\ntotal +\$6\.00 +1 +3 ")
        self.assertNotIn("a game", out)  # the other folder's session, and prompts never print

    def test_by_model_and_folder_everywhere(self):
        out = self.ok("--totals", "model", "--all").stdout
        rows = [l.split()[0] for l in out.splitlines()[2:4]]
        self.assertEqual(sorted(rows), ["claude-opus-5-5", "claude-sonnet-5-5"])
        self.assertIn("(no model call)", out)  # the /compact prompt
        self.assertRegex(out, r"\nclaude-opus-5-5 +\$6\.00 +1 +2 ")
        out = self.ok("--totals", "folder", "--all").stdout
        self.assertRegex(out, r"\nproj +\$6\.00 ")
        self.assertRegex(out, r"\nelsewhere +\$")
        self.assertNotIn(self.home, out)  # folder names only, never paths

    def test_since_until_and_json(self):
        out = self.ok("--totals", "--since", "2026-10-02").stdout
        self.assertNotIn("1 Oct", out)
        self.assertRegex(out, r"\ntotal +\$2\.00 ")
        r = json.loads(self.ok("--totals", "--json", "--until", "2026-10-02").stdout)
        self.assertEqual([x["bucket"] for x in r["rows"]], ["2026-10-01"])
        self.assertEqual(r["total"]["cost_usd"], 4.0)
        self.assertEqual((r["from"], r["to"], r["kind"]), ("2026-10-01", "2026-10-02", "totals"))
        r = json.loads(self.ok("--totals", "--json", "--hide", "cost,date").stdout)
        self.assertNotIn("cost_usd", r["total"])
        self.assertIsNone(r["from"])

    def test_wrong_input_stops(self):
        for args, said in (
            (["--totals", "--since", "10/02/2026"], "needs a date like 2026-10-01"),
            (["--since", "2026-10-02"], "go with --totals"),
            (["--totals", "--prompt"], "can't go with --prompt"),
            (["--totals", "--since", "2026-10-05", "--until", "2026-10-01"], "--since is after --until"),
            (["--totals", "--since", "2026-11-01"], "no prompts in those dates"),
        ):
            p = self.run_receipt(*args)
            self.assertNotEqual(p.returncode, 0, args)
            self.assertIn(said, p.stderr, args)
        self.ok("--totals", "--since", "2026-10-03")  # and a right one still works

    def test_a_prompt_ends_with_its_last_work(self):
        """late bookkeeping and a resumed session's "<synthetic>" reply don't stretch the /compact prompt"""
        turns = json.loads(self.ok(self.a, "--turns", "--json").stdout)["turns"]
        self.assertEqual([t["time_ms"] for t in turns], [60000, 180000, 120000])

    def test_overlapping_durations_are_capped(self):
        """Claude Code's turn_duration entries can overlap; a prompt can't run past its last work"""
        path = self.write("c", self.proj, [
            self.prompt("2026-10-05T12:00:00.000Z", "go", self.proj),
            self.call("2026-10-05T12:05:00.000Z", "c1", "claude-opus-5-5", inp=10),
            {"type": "system", "subtype": "turn_duration", "durationMs": 240000, "timestamp": "2026-10-05T12:04:00.000Z"},
            {"type": "system", "subtype": "turn_duration", "durationMs": 280000, "timestamp": "2026-10-05T12:05:00.000Z"},
        ])  # fmt: skip
        turns = json.loads(self.ok(path, "--turns", "--json").stdout)["turns"]
        self.assertEqual(turns[0]["time_ms"], 300000)  # not 520000
        path = self.write("d", self.proj, [  # a positive control: durations inside the span are kept
            self.prompt("2026-10-05T13:00:00.000Z", "go", self.proj),
            self.call("2026-10-05T13:05:00.000Z", "d1", "claude-opus-5-5", inp=10),
            {"type": "system", "subtype": "turn_duration", "durationMs": 200000, "timestamp": "2026-10-05T13:05:00.000Z"},
        ])  # fmt: skip
        turns = json.loads(self.ok(path, "--turns", "--json").stdout)["turns"]
        self.assertEqual(turns[0]["time_ms"], 200000)


class StatusLine(Base):
    """--statusline prints a line for Claude Code and keeps plan-limit readings; receipts read them back"""

    def setUp(self):
        super().setUp()
        self.cache = os.path.join(self.home, "cache")
        self.env["XDG_CACHE_HOME"] = self.cache
        self.limits = os.path.join(self.cache, "prompt-receipts", "limits")

    def line(self, rl=None, sid="s1"):
        d = {"session_id": sid, "model": {"id": "claude-opus-5-5", "display_name": "Opus 5.5"},
             "cost": {"total_cost_usd": 0.42, "total_duration_ms": 720000}}  # fmt: skip
        if rl:
            d["rate_limits"] = rl
        return self.ok("--statusline", stdin=json.dumps(d)).stdout.strip()

    def kept(self, sid="s1"):
        try:
            with open(os.path.join(self.limits, sid + ".jsonl"), encoding="utf-8") as f:
                return [json.loads(x) for x in f]
        except FileNotFoundError:
            return []

    def test_prints_and_keeps_readings(self):
        self.assertEqual(self.line(), "Opus 5.5 · $0.42 · 12 min")  # before the first reply: no limits yet
        self.assertEqual(self.kept(), [])
        rl = {"five_hour": {"used_percentage": 20, "resets_at": 100}, "seven_day": {"used_percentage": 51, "resets_at": 900}}
        self.assertEqual(self.line(rl), "Opus 5.5 · $0.42 · 12 min · 5-hour 20% · weekly 51%")
        self.line(rl)  # the same reading again isn't kept twice
        rl["five_hour"]["used_percentage"] = 23
        self.assertEqual(self.line(rl), "Opus 5.5 · $0.42 · 12 min · 5-hour 23% (+3% this session) · weekly 51%")
        self.assertEqual([k["five_hour"] for k in self.kept()], [[20, 100], [23, 100]])
        p = self.run_receipt("--statusline", "--json", stdin="{}")
        self.assertIn("takes no other options", p.stderr)
        p = self.run_receipt("--statusline", stdin="not json")
        self.assertIn("expects Claude Code's status-line input", p.stderr)

    def readings(self, sid, rows):
        os.makedirs(self.limits, exist_ok=True)
        with open(os.path.join(self.limits, sid + ".jsonl"), "w", encoding="utf-8") as f:
            for t, five, week in rows:
                f.write(json.dumps({"t": t, "five_hour": five, "seven_day": week}) + "\n")

    def test_receipt_says_how_far_the_limits_moved(self):
        path = self.claude_log()  # prompts at 14:00 and 14:04, last entry 14:05 (UTC)
        out = self.ok(path).stdout
        self.assertNotIn("limits", out)  # a positive control: no readings, no line
        self.readings("s1", [
            ("2026-10-09T13:50:00+00:00", [10, 1000], [40, 9000]),  # before the run: where it started from
            ("2026-10-09T14:02:00.250000+00:00", [14, 1000], [41, 9000]),
            ("2026-10-09T14:04:00+00:00", [3, 2000], [42, 9000]),  # the 5-hour window reset: 3 points since
            ("2026-10-09T14:30:00+00:00", [50, 2000], [60, 9000]),  # after the run: not this run's
        ])  # fmt: skip
        out = self.ok(path).stdout
        self.assertIn("limits   5-hour +7%, weekly +2% while this ran, from the status line's readings", out)
        r = json.loads(self.ok(path, "--json").stdout)
        self.assertEqual(r["plan_use"], {"5-hour": 7.0, "weekly": 2.0})
        self.assertNotIn("limits", self.ok(path, "--hide", "billing").stdout)
        self.assertNotIn("plan_use", json.loads(self.ok(path, "--json", "--hide", "billing").stdout))


class Qwen(Base):
    """Qwen Code: one JSONL per session; each API call logged on the reply and as an api_response event"""

    def setUp(self):
        super().setUp()
        self.qhome = os.path.join(self.home, "qwen-home")
        self.env["QWEN_HOME"] = self.qhome

    def qwen_log(self, telemetry=True, auth="qwen-oauth", name="q1", thoughts=0):
        def rec(t, ts_, **kw):
            return {"uuid": f"u{ts_}", "sessionId": name, "timestamp": ts(ts_), "type": t, "cwd": self.proj,
                    "version": "0.25.0", **kw}  # fmt: skip

        def api(ts_, inp, cached, out, thoughts=0, sub=None):
            ev = {"event.name": "qwen-code.api_response", "model": "qwen3-coder-plus", "duration_ms": 2000,
                  "input_token_count": inp, "cached_content_token_count": cached, "output_token_count": out,
                  "thoughts_token_count": thoughts, "auth_type": auth}  # fmt: skip
            if sub:
                ev["subagent_name"] = sub
            return rec("system", ts_, subtype="ui_telemetry", systemPayload={"uiEvent": ev})

        def reply(ts_, inp, cached, out, parts, thoughts=0):
            return rec("assistant", ts_, model="qwen3-coder-plus", message={"role": "model", "parts": parts},
                       usageMetadata={"promptTokenCount": inp, "cachedContentTokenCount": cached,
                                      "candidatesTokenCount": out, "thoughtsTokenCount": thoughts})  # fmt: skip

        call = lambda cid, n, args: {"functionCall": {"id": cid, "name": n, "args": args}}  # noqa: E731
        shown = lambda cid, n, **res: {"role": "user", "parts": [{"functionResponse": {"id": cid, "name": n, "response": res}}]}  # noqa: E731
        es = [
            rec("user", 0, executionContext={"modelId": "qwen3-coder-plus", "authType": auth, "approvalMode": "yolo"},
                message={"role": "user", "parts": [{"text": "make hello.txt"}]}),
            rec("user", 0, subtype="notification", message={"role": "user", "parts": [{"text": "a notice"}]}),
            api(1, 20000, 0, 100, thoughts),
            reply(1, 20000, 0, 100, [{"text": "thinking", "thought": True}, {"text": "ok"},
                                     call("c1", "write_file", {"file_path": os.path.join(self.proj, "hello.txt"), "content": "hi"}),
                                     call("c2", "run_shell_command", {"command": "ls"}),
                                     call("c3", "write_file", {"file_path": os.path.join(self.proj, "nope.txt"), "content": "x"})]),
            rec("tool_result", 2, toolCallResult={"callId": "c1", "status": "success"}, message=shown("c1", "write_file", output="wrote")),
            rec("tool_result", 2, toolCallResult={"callId": "c2", "status": "success"}, message=shown("c2", "run_shell_command", output="x")),
            rec("tool_result", 2, toolCallResult={"callId": "c3", "status": "error", "error": {"message": "denied"}},
                message=shown("c3", "write_file", error="denied")),
            api(3, 21000, 20000, 20),
            reply(3, 21000, 20000, 20, [{"text": "made hello.txt"}]),
            api(4, 5000, 0, 200, sub="managed-auto-memory-extractor"),  # in the background: no reply logged
            rec("user", 5, executionContext={"authType": auth, "approvalMode": "yolo"},
                message={"role": "user", "parts": [{"text": "stop"}]}),
            rec("system", 6, subtype="turn_result", systemPayload={"state": "cancelled"}),
        ]  # fmt: skip
        if not telemetry:
            es = [e for e in es if e.get("subtype") != "ui_telemetry"]
        folder = os.path.join(self.qhome, "projects", slug(self.proj), "chats")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"{name}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write("".join(json.dumps(e) + "\n" for e in es))
        return path

    def test_receipt(self):
        self.qwen_log()
        out = self.ok("--qwen").stdout
        self.assertIn("Receipt v7.0 · Qwen Code 0.25.0", out)
        self.assertIn("2 prompts from me", out)  # Qwen Code's own notice isn't a prompt
        # all three calls, the memory extractor's too: 46k in (20k cached), 320 out
        self.assertIn("tokens   in 46k (20k cached) · out 320", out)
        self.assertIn("work     3 tool calls, 1 shell command · web 0 · 1 failed call · interrupted 1×", out)
        self.assertIn("files    1 file written or edited (.txt)", out)  # the failed write isn't one
        self.assertIn("billing  Qwen OAuth: a free daily allowance", out)
        self.assertIn("settings approvals yolo", out)
        r = json.loads(self.ok("--qwen", "--json").stdout)
        # 26k uncached at $1/M, 20k cached at $0.10/M, 320 out at $5/M
        self.assertAlmostEqual(r["cost_usd"], 0.026 + 0.002 + 0.0016, places=6)

    def test_replies_when_there_is_no_telemetry(self):
        self.qwen_log(telemetry=False)
        out = self.ok("--qwen").stdout
        self.assertIn("tokens   in 41k (20k cached) · out 120", out)  # no background call to see

    def test_google_reasoning_is_extra_output(self):
        self.qwen_log(auth="gemini", thoughts=50)
        r = json.loads(self.ok("--qwen", "--json").stdout)
        self.assertEqual(r["tokens_out"], 370)  # Google counts reasoning apart from the output
        self.assertIn("a Gemini API key", r["billing"])
        self.qwen_log(thoughts=50)  # the same session on Qwen's own login: reasoning is inside the output
        self.assertEqual(json.loads(self.ok("--qwen", "--json").stdout)["tokens_out"], 320)

    def test_turns_recipe_list_and_totals(self):
        path = self.qwen_log()
        out = self.ok(path, "--turns", "--recipe").stdout  # found as Qwen Code from where it lives
        self.assertRegex(out, r"turns    1  \d+:\d\d [AP]M · 4 min · \$0\.03 · 3 tool calls, 1 shell command · 1 file")
        self.assertIn("rerun    qwen -m qwen3-coder-plus --approval-mode yolo 'make hello.txt'", out)
        self.assertIn("qwen --continue -m qwen3-coder-plus --approval-mode yolo stop", out)
        self.assertIn("make hello.txt", self.ok("--qwen", "--list").stdout)
        self.assertRegex(self.ok("--qwen", "--totals").stdout, r"\ntotal +\$0\.03 +1 +2 ")
        rec, hello = os.path.join(self.home, "r.json"), os.path.join(self.home, "hello.txt")
        self.ok("--qwen", "--record", rec)
        with open(hello, "w", encoding="utf-8") as f:
            f.write("hi")
        out = self.ok("--verify", rec, hello).stdout
        self.assertIn("came out of the run", out)  # the text write_file wrote
        with open(rec, encoding="utf-8") as f:
            pred = json.load(f)["predicate"]
        self.assertEqual(len(pred["prompts"]), 2)
        self.assertEqual(sum(1 for t in pred["tool_results"] if t.get("failed")), 1)
        p = self.run_receipt("--qwen", "--codex")
        self.assertIn("pick one of --codex, --opencode, --qwen, --gemini and --copilot", p.stderr)


class Gemini(Base):
    """Gemini CLI: one JSONL per session, each message written again as it changes; a subagent's in its own file"""

    def setUp(self):
        super().setUp()
        self.ghome = os.path.join(self.home, "gemini-home")
        self.env["GEMINI_CLI_HOME"] = self.ghome
        self.tmpdir = os.path.join(self.ghome, ".gemini", "tmp")

    def gemini_log(self):
        folder = os.path.join(self.tmpdir, "proj")
        os.makedirs(os.path.join(folder, "chats", "g-1"), exist_ok=True)
        with open(os.path.join(folder, ".project_root"), "w", encoding="utf-8") as f:
            f.write(self.proj)

        def msg(id_, m, kind, **kw):
            return {"id": id_, "timestamp": ts(m), "type": kind, **kw}

        def tok(i, c, o, th=0):
            return {"input": i, "output": o, "cached": c, "thoughts": th, "tool": 0, "total": i + o + th}

        def call(n, args, status):
            return {"id": n + status, "name": n, "args": args, "status": status, "timestamp": ts(2)}

        calls = [call("write_file", {"file_path": "hello.txt", "content": "hi"}, "success"),
                 call("run_shell_command", {"command": "ls"}, "success"),
                 call("write_file", {"file_path": "nope.txt", "content": "x"}, "error")]  # fmt: skip
        es = [
            {"sessionId": "g-1", "projectHash": "x", "startTime": ts(0), "lastUpdated": ts(0), "kind": "main"},
            {"$set": {"messages": [msg("ctx", 0, "user", content=[{"text": "<session_context>\nsetup"}])]}},
            msg("u1", 0, "user", content=[{"text": "make hello.txt"}]),
            msg("g1", 1, "gemini", content="", model="gemini-2.5-flash", tokens=tok(10000, 0, 20, 40)),
            {"$set": {"lastUpdated": ts(1)}},
            # the same reply again, now with its tool calls: read once
            msg("g1", 1, "gemini", content="", model="gemini-2.5-flash", tokens=tok(10000, 0, 20, 40), toolCalls=calls),
            msg("r1", 2, "user", content=[{"functionResponse": {"id": "c1", "name": "write_file", "response": {}}}]),
            msg("g2", 3, "gemini", content="made hello.txt", model="gemini-2.5-flash", tokens=tok(11000, 9000, 21)),
            {},
            msg("u2", 5, "user", content=[{"text": "stop"}]),
            msg("g3", 6, "gemini", content="", model="gemini-2.5-flash", tokens=tok(12000, 9000, 5),
                toolCalls=[call("run_shell_command", {"command": "sleep 9"}, "cancelled")]),
        ]  # fmt: skip
        path = os.path.join(folder, "chats", "session-2026-10-09T14-00-g-1.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write("".join(json.dumps(e) + "\n" for e in es))
        sub = [{"sessionId": "s-1", "projectHash": "x", "startTime": ts(3), "kind": "subagent"},
               msg("s1", 3, "gemini", content="found it", model="gemini-2.5-flash", tokens=tok(3000, 0, 100))]  # fmt: skip
        with open(os.path.join(folder, "chats", "g-1", "s-1.jsonl"), "w", encoding="utf-8") as f:
            f.write("".join(json.dumps(e) + "\n" for e in sub))
        return path

    def test_receipt(self):
        self.gemini_log()
        out = self.ok("--gemini").stdout
        self.assertIn("Receipt v7.0 · Gemini CLI · ", out)  # no version is logged
        self.assertIn("2 prompts from me", out)  # its opening message and the tool results aren't prompts
        # each reply once, and the subagent's: 36k in (18k cached); out counts the 40 tokens of reasoning
        self.assertIn("tokens   in 36k (18k cached) · out 186", out)
        self.assertIn("work     4 tool calls, 2 shell commands · web 0 · 1 failed call · interrupted 1×", out)
        self.assertIn("files    1 file written or edited (.txt)", out)
        r = json.loads(self.ok("--gemini", "--json").stdout)
        # 18k uncached at $0.30/M, 18k cached at $0.03/M, 186 out at $2.50/M
        self.assertAlmostEqual(r["cost_usd"], 0.0054 + 0.00054 + 0.000465, places=6)

    def test_turns_recipe_and_path(self):
        path = self.gemini_log()
        out = self.ok(path, "--turns", "--recipe").stdout  # found as Gemini CLI from where it lives
        self.assertRegex(out, r"turns    1  \d+:\d\d [AP]M · 3 min · <?\$0\.01 · 3 tool calls, 1 shell command · 1 file")
        self.assertIn("the turns add up to the cost above", out)
        self.assertIn("rerun    gemini -m gemini-2.5-flash -p 'make hello.txt'", out)
        self.assertIn("gemini --resume latest -m gemini-2.5-flash -p stop", out)
        self.assertRegex(self.ok("--gemini", "--totals").stdout, r"\ntotal +<?\$0\.01 +1 +2 ")

    def test_older_whole_json_file_in_a_hash_folder(self):
        folder = os.path.join(self.tmpdir, hashlib.sha256(self.proj.encode()).hexdigest(), "chats")
        os.makedirs(folder)
        doc = {"sessionId": "old-1", "projectHash": hashlib.sha256(self.proj.encode()).hexdigest(), "startTime": ts(0),
               "messages": [{"id": "c", "timestamp": ts(0), "type": "user", "content": "<session_context>\nsetup"},
                            {"id": "u", "timestamp": ts(0), "type": "user", "content": "an old prompt"},
                            {"id": "g", "timestamp": ts(1), "type": "gemini", "content": "ok", "model": "gemini-2.5-flash",
                             "tokens": {"input": 500, "output": 7, "cached": 0, "thoughts": 0, "tool": 0, "total": 507}}]}  # fmt: skip
        with open(os.path.join(folder, "session-old.json"), "w", encoding="utf-8") as f:
            json.dump(doc, f)
        self.assertIn("an old prompt", self.ok("--gemini", "--list").stdout)  # matched to this folder by the hash
        out = self.ok("--gemini").stdout
        self.assertIn("tokens   in 500 (0 cached) · out 7", out)
        self.assertIn("1 prompt from me", out)  # its opening message isn't one


class Copilot(Base):
    """GitHub Copilot CLI: one events.jsonl per session, with a usage record for every API call"""

    def setUp(self):
        super().setUp()
        self.chome = os.path.join(self.home, "copilot-home")
        self.env["COPILOT_HOME"] = self.chome

    def copilot_log(self, sid="c-1", byok=False):
        def ev(kind, m, **data):
            return {"type": kind, "id": f"{kind}{m}", "parentId": None, "timestamp": ts(m), "data": data}

        def use(m, i, read, write, out, ms, effort, nano):
            u = {"model": "claude-opus-4.7", "inputTokens": i, "cacheReadTokens": read, "cacheWriteTokens": write,
                 "outputTokens": out, "reasoningTokens": out // 2, "duration": ms, "reasoningEffort": effort,
                 "isByok": byok, "aiCreditsStatus": "unavailable" if byok else "complete"}  # fmt: skip
            if not byok:
                u["copilotUsage"] = {"totalNanoAiu": nano}
            return ev("session.usage_record", m, usage=u)

        def req(cid, n, **args):
            return {"toolCallId": cid, "name": n, "arguments": args}

        hello = os.path.join(self.proj, "hello.txt")
        es = [
            ev("session.start", 0, sessionId=sid, copilotVersion="1.0.95", selectedModel="claude-opus-4.7",
               reasoningEffort="high", context={"cwd": self.proj}),
            ev("user.message", 0, content="make hello.txt"),
            ev("user.message", 0, content="a skill's own text", source="skill-pdf"),
            ev("assistant.message", 1, content="", toolRequests=[
                req("t1", "create", path=hello, file_text="hi"), req("t2", "bash", command="ls"),
                req("t3", "edit", path=os.path.join(self.proj, "x.py"), old_str="a", new_str="b"),
                dict(req("t4", "search_code", q="x"), mcpServerName="github")]),
            use(1, 10000, 0, 8000, 100, 3000, "high", 2 * 10**9),
            ev("tool.execution_complete", 2, toolCallId="t1", success=True),
            ev("tool.execution_complete", 2, toolCallId="t2", success=True),
            ev("tool.execution_complete", 2, toolCallId="t3", success=False, error={"message": "no such file"}),
            ev("tool.execution_complete", 2, toolCallId="t4", success=True),
            ev("assistant.message", 3, content="made it", toolRequests=[]),
            use(3, 12000, 8000, 0, 20, 1000, "high", 10**9),
            # running totals for the session: not added again
            ev("session.shutdown", 4, modelMetrics={"claude-opus-4.7": {"usage": {"inputTokens": 999999}}}),
            ev("session.resume", 5, reasoningEffort="xhigh", context={"cwd": self.proj}),
            ev("user.message", 5, content="now delete it"),
            ev("abort", 6, reason="user"),
            ev("assistant.message", 6, content="", toolRequests=[req("t5", "bash", command="rm hello.txt")]),
            use(6, 5000, 4000, 0, 10, 500, "xhigh", 0),
            ev("tool.execution_complete", 7, toolCallId="t5", success=True, fileEdits=[{"path": hello, "kind": "delete"}]),
        ]  # fmt: skip
        folder = os.path.join(self.chome, "session-state", sid)
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "events.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write("".join(json.dumps(e) + "\n" for e in es))
        return path

    def test_receipt(self):
        self.copilot_log()
        out = self.ok("--copilot").stdout
        self.assertIn("Receipt v7.0 · Copilot CLI 1.0.95", out)
        self.assertIn("model    claude-opus-4.7 · effort high → xhigh", out)
        self.assertIn("2 prompts from me", out)  # the skill's message isn't one
        # the three calls only: the input counts include cache reads and writes, the output the reasoning
        self.assertIn("tokens   in 27k (12k cached) · out 130", out)
        self.assertIn("work     5 tool calls, 2 shell commands · web 0 · 1 failed call · interrupted 1×", out)
        self.assertIn("billing  GitHub Copilot: 3.00 AI credits by the log, $0.03 at $0.01 a credit", out)
        r = json.loads(self.ok("--copilot", "--json").stdout)
        # priced as claude-opus-4-7: 7k uncached at $5/M, 12k read at $0.50/M, 8k written at $6.25/M, 130 out at $25/M
        self.assertAlmostEqual(r["cost_usd"], 0.035 + 0.006 + 0.05 + 0.00325, places=6)
        self.assertEqual((r["files_written"], r["files_deleted"]), (1, 1))  # x.py's edit failed
        self.assertEqual(r["mcp_used"], {"github": 1})
        self.assertEqual(r["model_time_ms"], 4500)

    def test_own_key(self):
        self.copilot_log(byok=True)
        self.assertIn("billing  your own API key: charged per token", self.ok("--copilot").stdout)

    def test_turns_recipe_and_path(self):
        path = self.copilot_log()
        out = self.ok(path, "--turns", "--recipe").stdout
        self.assertRegex(out, r"turns    1  \d+:\d\d [AP]M · 3 min · \$0\.09 · 4 tool calls, 1 shell command · 1 file")
        self.assertIn("rerun    copilot --model claude-opus-4.7 --reasoning-effort high -p 'make hello.txt'", out)
        self.assertIn("copilot --continue --model claude-opus-4.7 --reasoning-effort xhigh -p 'now delete it'", out)
        self.assertIn("make hello.txt", self.ok("--copilot", "--list").stdout.split("\n")[0])


class OutputShape(Base):
    """how much a run wrote, without its text: lines, size, a web page, and how long its replies were"""

    def test_measured_from_the_text_the_log_holds(self):
        self.claude_log(subagent=True, said="all done now")  # index.html "x" and style.css "b{}", neither on disk
        out = self.ok().stdout
        self.assertIn("files    2 files written or edited (.css, .html) · 2 lines, 4 bytes · a web page", out)
        self.assertIn("replies  1 reply, 3 words", out)

    def test_an_edited_file_is_measured_as_it_is_now(self):
        app, gone = os.path.join(self.proj, "app.js"), os.path.join(self.proj, "gone.js")
        with open(app, "w", encoding="utf-8") as f:
            f.write("a\nb\nc\n")

        def use(i, name, **inp):
            return {"type": "tool_use", "id": i, "name": name, "input": inp}

        es = [
            {"type": "user", "timestamp": ts(0), "cwd": self.proj, "version": "2.1.300", "sessionId": "e1",
             "message": {"role": "user", "content": "fix app.js"}},
            {"type": "assistant", "timestamp": ts(1), "message": {"id": "m1", "model": "claude-opus-5-5",
             "usage": {"input_tokens": 10, "output_tokens": 5}, "content": [
                 use("w", "Write", file_path=app, content="x"),  # written, then edited: the text is out of date
                 use("e", "Edit", file_path=app, old_string="x", new_string="a\nb\nc"),
                 use("g", "Edit", file_path=gone, old_string="1", new_string="2")]}},
            {"type": "assistant", "timestamp": ts(2), "message": {"id": "m2", "model": "claude-opus-5-5",
             "usage": {"input_tokens": 10, "output_tokens": 5}, "content": [{"type": "text", "text": "fixed"}]}},
        ]  # fmt: skip
        folder = os.path.join(self.claude_dir, "projects", slug(self.proj))
        os.makedirs(folder)
        with open(os.path.join(folder, "e1.jsonl"), "w", encoding="utf-8") as f:
            f.write("".join(json.dumps(e) + "\n" for e in es))
        out = self.ok().stdout
        self.assertIn("files    2 files written or edited (.js ×2) · 3 lines, 6 bytes · 1 not on disk now", out)
        self.assertNotIn("a web page", out)

    def test_hide_output(self):
        self.claude_log()
        out = self.ok("--hide", "output").stdout
        self.assertIn("files    1 file written or edited (.html)\n", out)
        self.assertNotIn("replies", out)
        r = json.loads(self.ok("--hide", "output", "--json").stdout)
        self.assertFalse({"output_lines", "output_bytes", "web_page", "replies", "reply_words"} & set(r))
        r = json.loads(self.ok("--json").stdout)
        self.assertEqual((r["output_lines"], r["output_bytes"], r["web_page"], r["replies"]), (1, 1, True, 1))

    def test_other_tools(self):
        self.qhome = self.env["QWEN_HOME"] = os.path.join(self.home, "qwen-home")
        Qwen.qwen_log(self)  # hello.txt "hi", written by write_file
        self.assertIn("(.txt) · 1 line, 2 bytes", self.ok("--qwen").stdout)


class OutputPage(Base):
    """--page: one HTML file with the receipt, every prompt and reply, the files, and the page it made running"""

    def site_log(self, prompt="make a page <script>alert(1)</script>", reply="Made it. Open index.html."):
        def use(i, name, **inp):
            return {"type": "tool_use", "id": i, "name": name, "input": inp}

        page = ('<!doctype html><link rel="stylesheet" href="style.css"><img src="./pic.svg">'
                '<script src="app.js"></script><script src="missing.js"></script><script src="https://x.test/a.js"></script>')
        es = [
            {"type": "user", "timestamp": ts(0), "cwd": self.proj, "version": "2.1.300", "sessionId": "p1",
             "message": {"role": "user", "content": prompt}},
            {"type": "assistant", "timestamp": ts(1), "message": {"id": "m1", "model": "claude-opus-5-5",
             "usage": {"input_tokens": 10, "output_tokens": 5}, "content": [
                 use("a", "Write", file_path=os.path.join(self.proj, "index.html"), content=page),
                 use("b", "Write", file_path=os.path.join(self.proj, "style.css"), content="b{color:red}"),
                 use("c", "Write", file_path=os.path.join(self.proj, "app.js"), content="document.title='</script>hi'"),
                 use("d", "Write", file_path=os.path.join(self.proj, "pic.svg"), content="<svg/>")]}},
            {"type": "assistant", "timestamp": ts(2), "message": {"id": "m2", "model": "claude-opus-5-5",
             "usage": {"input_tokens": 10, "output_tokens": 5}, "content": [{"type": "text", "text": reply}]}},
        ]  # fmt: skip
        folder = os.path.join(self.claude_dir, "projects", slug(self.proj))
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "p1.jsonl"), "w", encoding="utf-8") as f:
            f.write("".join(json.dumps(e) + "\n" for e in es))
        return os.path.join(self.home, "page.html")

    def page(self, *args):
        out = self.site_log()
        self.ok("--page", out, *args)
        with open(out, encoding="utf-8") as f:
            return f.read()

    def frame(self, page):
        import html as h
        m = re.search(r'<iframe sandbox="allow-scripts" srcdoc="([^"]*)"', page)
        self.assertIsNotNone(m, "no sandboxed frame")
        return h.unescape(m.group(1))

    def test_the_page_runs_with_its_own_files_inside(self):
        page = self.page()
        inner = self.frame(page)
        self.assertIn("<style>b{color:red}</style>", inner)
        self.assertIn("<script>document.title='<\\/script>hi'</script>", inner)  # can't end its own script early
        self.assertIn('src="data:image/svg+xml;base64,' + base64.b64encode(b"<svg/>").decode() + '"', inner)
        self.assertNotIn('src="app.js"', inner)
        self.assertIn('src="https://x.test/a.js"', inner)  # a page on the web loads as it would
        self.assertIn("so they aren't here: missing.js", page)
        self.assertIn("<summary>file1.js · as written · 28 bytes</summary>", page)  # names stay off by default
        self.assertNotIn("app.js · as written", page)
        self.assertIn("<summary>app.js · as written", self.page("--file-names"))

    def test_prompts_and_replies_as_text(self):
        page = self.page()
        self.assertIn("Made it. Open index.html.", page)
        self.assertIn("make a page &lt;script&gt;alert(1)&lt;/script&gt;", page)  # shown, never run
        self.assertNotIn("<script>alert(1)", page)
        self.assertIn("files    4 files written or edited", page)  # the receipt itself
        r = json.loads(self.ok("--json").stdout)
        self.assertFalse([k for k in r if k.startswith("_")])

    def test_a_reply_with_an_email_stops_it(self):
        out = self.site_log(reply="mail me@example.com")
        p = self.run_receipt("--page", out)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("the model's reply holds 1 email address", p.stderr)
        self.assertFalse(os.path.exists(out))
        self.ok("--page", out, "--redact")
        with open(out, encoding="utf-8") as f:
            self.assertIn("mail [email]", f.read())

    def test_hide_files(self):
        page = self.page("--hide", "files")
        self.assertNotIn("<iframe", page)
        self.assertNotIn("<h2>Files</h2>", page)
        self.assertIn("Made it.", page)

    def test_output_url_fingerprints_the_page_as_written(self):
        out = self.site_log()
        p = self.ok("--page", out, "--output-url", "https://me.github.io/run/page.html")
        with open(out, "rb") as f:
            want = hashlib.sha256(f.read()).hexdigest()  # the file's own bytes, line ends and all
        self.assertIn(f"page     https://me.github.io/run/page.html · sha256 {want[:16]}\n", p.stdout)
        self.assertIn("one changed byte", p.stderr)
        r = json.loads(self.ok("--page", out, "--output-url", "https://me.github.io/run/page.html", "--json").stdout)
        self.assertEqual(r["output_sha256"], want)
        hid = self.ok("--page", out, "--output-url", "https://me.github.io/run/page.html", "--hide", "output").stdout
        self.assertNotIn("sha256", hid)
        self.assertIn("files    4 files written or edited", hid)
        self.assertNotIn("page     ", self.ok("--page", out).stdout)

    def test_output_url_needs_a_page_and_https(self):
        out = self.site_log()
        p = self.run_receipt("--output-url", "https://me.github.io/page.html")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("add --page FILE.html", p.stderr)
        p = self.run_receipt("--page", out, "--output-url", "http://me.example/page.html")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("needs an https:// address", p.stderr)
        self.assertFalse(os.path.exists(out))
        self.ok("--page", out, "--output-url", "http://localhost:8000/page.html")  # testing on your own machine


if __name__ == "__main__":
    unittest.main()
