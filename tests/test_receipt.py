"""Runs tools/receipt.py the way a user does, on small made-up logs shaped like real ones.

Each test gets its own home folder with Claude Code, Codex and OpenCode logs in it, so nothing on
the machine running the tests is read. python -m unittest discover -s tests"""

import json
import os
import re
import sqlite3
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

RECEIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "tools", "receipt.py"
)
T0 = "2026-10-09T14:00:00.000Z"


def ts(minute):
    return f"2026-10-09T14:{minute:02d}:00.000Z"


def slug(path):
    return re.sub(r"[^A-Za-z0-9]", "-", path)


class Receipts(unittest.TestCase):
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
        self, prompt="Make a page for my habit tracker", name="s1", replies=True
    ):
        entries = [
            {"type": "user", "timestamp": ts(0), "cwd": self.proj, "version": "2.1.300",
             "permissionMode": "default", "effort": "high", "message": {"role": "user", "content": prompt}},
        ]  # fmt: skip
        if replies:
            entries += [
                {"type": "assistant", "timestamp": ts(1), "message": {
                    "id": "m1", "model": "claude-opus-5-5",
                    "usage": {"input_tokens": 1000, "output_tokens": 200,
                              "cache_read_input_tokens": 500, "cache_creation_input_tokens": 0},
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
                {"type": "user", "timestamp": ts(4), "message": {"role": "user", "content": "now make it blue"}},
                {"type": "assistant", "timestamp": ts(5), "message": {
                    "id": "m2", "model": "claude-opus-5-5",
                    "usage": {"input_tokens": 300, "output_tokens": 100,
                              "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
                    "content": [{"type": "text", "text": "done"}]}},
                {"type": "cost-state", "totalCostUSD": 1.234, "totalAPIDuration": 90000,
                 "modelUsage": {"claude-opus-5-5": {"inputTokens": 1300, "outputTokens": 300,
                                                    "cacheReadInputTokens": 500, "cacheCreationInputTokens": 0}}},
            ]  # fmt: skip
        folder = os.path.join(self.claude_dir, "projects", slug(self.proj))
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"{name}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write("".join(json.dumps(e) + "\n" for e in entries))
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

    def codex_log(self):
        entries = [
            {"type": "session_meta", "timestamp": T0, "payload": {
                "cwd": self.proj, "cli_version": "0.130.0", "model_provider": "ollama"}},
            {"type": "turn_context", "timestamp": ts(0), "payload": {
                "model": "gpt-oss:20b", "effort": "medium", "approval_policy": "on-request",
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
                "total_token_usage": {"input_tokens": 900},
                "last_token_usage": {"input_tokens": 900, "cached_input_tokens": 100, "output_tokens": 80}}}},
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

    # ---------- the receipts ----------

    def test_claude_code_receipt(self):
        self.claude_log()
        out = self.ok().stdout
        self.assertIn("Receipt v3.0 · Claude Code 2.1.300", out)
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
        self.assertIn("Receipt v3.0 · OpenCode 1.18.31", out)
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
        self.assertEqual(r["receipt_version"], "3.0")
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
        self.assertEqual(self.ok("--version").stdout.strip(), "receipt.py 3.0")

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
        self.assertIn("entry.1393206370=Receipt%20v3.0", url)

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
            self.assertIn("Receipt v3.0 · Claude Code", f.read())

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
