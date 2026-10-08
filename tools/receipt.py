"""Make a receipt for your own Claude Code or Codex run: what ran, how long, what it cost, what was switched on.

usage: python3 receipt.py [SESSION.jsonl] [--codex] [--prompt] [--md] [--json]

  no file    the newest Claude Code session for the current folder (~/.claude/projects/...)
  --codex    the newest Codex session for the current folder (~/.codex/sessions/...)
  --prompt   also print your first prompt (left out by default; it can hold paths or names, so read it first)
  --md       wrap it in a code block for pasting into GitHub or Discord
  --json     machine-readable

It prints names and counts only. Paths, your email, account ids and file contents stay out.
Standard library only. Prompts and page text: https://musharna.github.io/prompt-receipts/ (CC BY 4.0)."""

import argparse
import collections
import datetime
import glob
import json
import os
import re
import sys


def lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def when(ts):
    return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()


def mins(ms):
    s = ms / 1000
    return (
        f"{s:.0f} s"
        if s < 90
        else f"{s / 60:.0f} min"
        if s < 5400
        else f"{s / 3600:.1f} h"
    )


def toks(n):
    for size, unit in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
        if n >= size:
            return f"{n / size:.1f}{unit}" if unit != "k" else f"{n / size:.0f}k"
    return str(n)


def span(vals):
    vals = [v for v in dict.fromkeys(vals) if v]
    return " → ".join(vals) if vals else "not recorded"


def newest(pattern):
    fs = glob.glob(pattern)
    return max(fs, key=os.path.getmtime) if fs else None


def claude(path):
    r = {"tool": "Claude Code"}
    versions, models, efforts, perms, stamps = [], [], [], [], []
    tools = collections.Counter()
    skills, mcp, agents = (
        collections.Counter(),
        collections.Counter(),
        collections.Counter(),
    )
    memory, mcp_servers, invoked = {}, set(), set()
    skill_count, prompts, first_prompt, cost = None, 0, None, None
    server_web = 0
    for d in lines(path):
        t = d.get("type")
        if d.get("timestamp"):
            stamps.append(d["timestamp"])
        if d.get("version"):
            versions.append(d["version"])
        if d.get("effort"):
            efforts.append(str(d["effort"]))
        if d.get("permissionMode"):
            perms.append(d["permissionMode"])
        if t == "cost-state":
            cost = d
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
            elif at == "skill_listing" and a.get("skillCount") is not None:
                skill_count = a["skillCount"]
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
            ):  # skills you started yourself (/name) are listed here, not as Skill calls
                invoked |= {s.get("name", "?") for s in a.get("skills", [])}
        elif (
            t == "user"
            and not d.get("isSidechain")
            and not d.get("isMeta")
            and ((d.get("origin") or {}).get("kind", "human") == "human")
        ):
            c = (d.get("message") or {}).get("content")
            text = c if isinstance(c, str) else None
            if (
                isinstance(c, list)
                and c
                and all(isinstance(b, dict) and b.get("type") == "text" for b in c)
            ):
                text = "\n".join(b.get("text", "") for b in c)
            if (
                text
                and not text.startswith("<")
                and not text.startswith("This session is being continued")
            ):
                prompts += 1
                first_prompt = first_prompt or text
        elif t == "assistant" and not d.get("isSidechain"):
            m = d.get("message") or {}
            if m.get("model") and not m["model"].startswith("<"):
                models.append(m["model"])
            stu = (m.get("usage") or {}).get("server_tool_use") or {}
            server_web += (stu.get("web_search_requests") or 0) + (
                stu.get("web_fetch_requests") or 0
            )
            for b in m.get("content") or []:
                if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                    continue
                n = b.get("name", "?")
                tools[n] += 1
                inp = b.get("input") or {}
                if n == "Skill":
                    skills[inp.get("skill", "?")] += 1
                elif n in ("Agent", "Task"):
                    agents[inp.get("subagent_type", "general-purpose")] += 1
                elif n.startswith("mcp__"):
                    mcp[n.split("__")[1]] += 1
                    mcp_servers.add(n.split("__")[1])
    if not stamps:
        sys.exit(
            f"receipt: {path} has no timestamped entries; is it a Claude Code session log?"
        )
    sub = os.path.join(os.path.splitext(path)[0], "subagents")
    sub_runs = len(glob.glob(os.path.join(sub, "*.jsonl")))
    r["version"] = span(versions[:1] + versions[-1:])
    r["models"] = list(dict.fromkeys(models))
    r["effort"] = span(efforts)
    r["permissions"] = span(perms)
    r["started"], r["ended"] = min(stamps), max(stamps)
    r["prompts"] = prompts
    if cost:
        r["model_time_ms"] = cost.get("totalAPIDuration")
        r["cost_usd"] = round(cost.get("totalCostUSD", 0), 2)
        r["cost_note"] = "Claude Code's estimate at API prices" + (
            "; some model costs unknown" if cost.get("hasUnknownModelCost") else ""
        )
        mu = cost.get("modelUsage") or {}
        r["tokens_in"] = sum(
            v.get("inputTokens", 0)
            + v.get("cacheReadInputTokens", 0)
            + v.get("cacheCreationInputTokens", 0)
            for v in mu.values()
        )
        r["tokens_cached"] = sum(v.get("cacheReadInputTokens", 0) for v in mu.values())
        r["tokens_out"] = sum(v.get("outputTokens", 0) for v in mu.values())
        main = {re.sub(r"\[.*\]$", "", m) for m in models}
        r["background_models"] = sorted({re.sub(r"\[.*\]$", "", m) for m in mu} - main)
        r["lines_changed"] = [
            cost.get("totalLinesAdded", 0),
            cost.get("totalLinesRemoved", 0),
        ]
    else:
        r["cost_note"] = "not in this log (older Claude Code versions don't write it)"
    r["tool_calls"] = sum(tools.values())
    r["shell_commands"] = tools.get("Bash", 0)
    r["web"] = tools.get("WebSearch", 0) + tools.get("WebFetch", 0) + server_web
    for name in invoked:
        skills[name] = max(skills[name], 1)
    r["skills_used"] = dict(skills)
    r["skills_available"] = skill_count
    r["mcp_used"] = dict(mcp)
    r["mcp_connected"] = len(mcp_servers)
    r["subagents"] = max(sum(agents.values()), sub_runs)
    r["memory"] = sorted(
        f"{name} ({kind.lower()})" for name, kind in memory.items() if name
    )
    r["first_prompt"] = first_prompt
    return r


def codex(path):
    r = {"tool": "Codex CLI"}
    versions, models, efforts, sandboxes, approvals, stamps = [], [], [], [], [], []
    calls = collections.Counter()
    skills, mcp = collections.Counter(), collections.Counter()
    prompts, first_prompt, usage, agents_md, web, images, busy = (
        0,
        None,
        None,
        False,
        0,
        0,
        0,
    )
    for d in lines(path):
        t, p = d.get("type"), d.get("payload") or {}
        if d.get("timestamp"):
            stamps.append(d["timestamp"])
        if t == "session_meta":
            versions.append(p.get("cli_version"))
        elif t == "turn_context":
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
        elif t == "event_msg" and p.get("type") == "token_count" and p.get("info"):
            usage = p["info"].get("total_token_usage")
        elif t == "event_msg" and p.get("type") == "task_complete":
            busy += p.get("duration_ms") or 0
        elif t == "response_item":
            pt = p.get("type")
            if pt in ("function_call", "custom_tool_call"):
                n = p.get("name", "?")
                calls[n] += 1
                if "mcp" in n or "__" in n:
                    mcp[n] += 1
                for s in re.findall(
                    r"skills/(?:\.system/)?([\w.-]+)/SKILL\.md",
                    json.dumps(p.get("input") or p.get("arguments") or ""),
                ):
                    skills[s] += 1
            elif pt == "web_search_call":
                web += 1
            elif pt == "image_generation_call":
                images += 1
            elif pt == "message" and p.get("role") == "user":
                # one message holds several blocks (plugin list, AGENTS.md, environment, image tags, your text):
                # judge each block, not the joined text
                blocks = [
                    b.get("text", "")
                    for b in p.get("content") or []
                    if isinstance(b, dict) and b.get("type") == "input_text"
                ]
                if any(b.startswith("# AGENTS.md instructions") for b in blocks):
                    agents_md = True
                for b in blocks:
                    for s in re.findall(r"<skill>\s*<name>([^<]+)</name>", b):
                        skills[s] += 1
                mine = [
                    b
                    for b in blocks
                    if b.strip() and not b.lstrip().startswith(("<", "# AGENTS.md"))
                ]
                if mine:
                    prompts += 1
                    first_prompt = first_prompt or "\n".join(mine)
    if not stamps:
        sys.exit(
            f"receipt: {path} has no timestamped entries; is it a Codex session log?"
        )
    r["version"] = span(versions)
    r["models"] = list(dict.fromkeys(m for m in models if m))
    r["effort"] = span(efforts)
    r["permissions"] = f"sandbox {span(sandboxes)} · approvals {span(approvals)}"
    r["started"], r["ended"] = min(stamps), max(stamps)
    r["prompts"] = prompts
    r["model_time_ms"] = busy or None
    r["cost_note"] = "Codex logs no price (ChatGPT plans don't bill per run)"
    if usage:
        r["tokens_in"] = usage.get("input_tokens", 0)
        r["tokens_cached"] = usage.get("cached_input_tokens", 0)
        r["tokens_out"] = usage.get("output_tokens", 0)
    r["tool_calls"] = sum(calls.values())
    r["shell_commands"] = calls.get("exec", 0) + calls.get("shell", 0)
    r["web"] = web
    r["images_made"] = images
    r["skills_used"] = dict(skills)
    r["mcp_used"] = dict(mcp)
    r["memory"] = ["AGENTS.md"] if agents_md else []
    r["first_prompt"] = first_prompt
    return r


def text(r, with_prompt):
    a, b = when(r["started"]), when(r["ended"])
    took = mins((b - a).total_seconds() * 1000)
    if r.get("model_time_ms"):
        took += f" (model working {mins(r['model_time_ms'])})"
    used = lambda d: (
        ", ".join(f"{k}" + (f" ×{v}" if v > 1 else "") for k, v in sorted(d.items()))
        or "none"
    )
    out = [f"Receipt · {r['tool']} {r['version']} · {a:%-d %b %Y}"]
    bg = r.get("background_models")
    bg = f" (+ {', '.join(bg)} in the background)" if bg else ""
    out.append(
        f"model    {', '.join(r['models']) or 'no model reply in this log'}{bg} · effort {r['effort']}"
    )
    out.append(
        f"time     {took} · {r['prompts']} prompt{'s' if r['prompts'] != 1 else ''} from me"
    )
    if "cost_usd" in r:
        money = f"${r['cost_usd']:.2f}" if r["cost_usd"] >= 0.01 else "<$0.01"
        out.append(f"cost     {money} ({r['cost_note']})")
    else:
        out.append(f"cost     {r['cost_note']}")
    if "tokens_in" in r:
        out.append(
            f"tokens   in {toks(r['tokens_in'])} ({toks(r['tokens_cached'])} cached) · out {toks(r['tokens_out'])}"
        )
    work = f"{r['tool_calls']} tool calls, {r['shell_commands']} shell commands · web {r['web']}"
    if r.get("images_made"):
        work += f" · images made {r['images_made']}"
    if any(r.get("lines_changed") or []):
        work += f" · lines +{r['lines_changed'][0]} -{r['lines_changed'][1]}"
    out.append(f"work     {work}")
    sk = f"skills {used(r['skills_used'])}"
    if r.get("skills_available") is not None:
        sk += f" (of {r['skills_available']} available)"
    mc = f"MCP {used(r['mcp_used'])}"
    if r.get("mcp_connected") is not None:
        mc += f" (of {r['mcp_connected']} connected)"
    extra = f" · subagents {r['subagents']}" if "subagents" in r else ""
    out.append(f"add-ons  {sk} · {mc}{extra}")
    out.append(f"memory   {', '.join(r['memory']) or 'none loaded'}")
    out.append(f"settings {r['permissions']}")
    if with_prompt and r.get("first_prompt"):
        out.append("prompt   " + r["first_prompt"].strip().replace("\n", "\n         "))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("session", nargs="?")
    ap.add_argument("--codex", action="store_true")
    ap.add_argument("--prompt", action="store_true")
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    home = os.path.expanduser("~")
    path = a.session
    is_codex = a.codex
    if not path and a.codex:
        here = os.getcwd()
        fs = sorted(
            glob.glob(f"{home}/.codex/sessions/*/*/*/rollout-*.jsonl"),
            key=os.path.getmtime,
            reverse=True,
        )
        path = next(
            (
                f
                for f in fs
                if any(
                    d.get("type") == "session_meta"
                    and (d.get("payload") or {}).get("cwd") == here
                    for d in lines(f)
                )
            ),
            None,
        )
        if not path:
            sys.exit(
                f"receipt: no Codex session found for {here} under ~/.codex/sessions"
            )
    elif not path:
        slug = re.sub(r"[^A-Za-z0-9]", "-", os.getcwd())
        path = newest(f"{home}/.claude/projects/{slug}/*.jsonl")
        if not path:
            sys.exit(
                f"receipt: no Claude Code session found for this folder (looked in ~/.claude/projects/{slug}/)"
            )
    elif not is_codex:
        is_codex = "/.codex/" in os.path.abspath(path) or os.path.basename(
            path
        ).startswith("rollout-")
    r = codex(path) if is_codex else claude(path)
    if a.json:
        if not a.prompt:
            r.pop("first_prompt", None)
        print(json.dumps(r, indent=1))
        return
    s = text(r, a.prompt)
    print(f"```\n{s}\n```" if a.md else s)


if __name__ == "__main__":
    main()
