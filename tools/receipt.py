"""Make a receipt for your own Claude Code or Codex run: what ran, how long, what it cost, what was switched on.

usage: python3 receipt.py [SESSION.jsonl] [options]

  no file          the newest Claude Code session for the current folder (~/.claude/projects/...)
  --codex          use Codex sessions instead (~/.codex/sessions/...)
  --list           list this folder's recent sessions; then --pick N to choose one
  --last N         only your last N prompts (cost stays whole-session: Claude Code doesn't log it per prompt)

  leaving things out (check the receipt before you share it):
  --hide a,b       drop parts: version, date, model, time, cost, tokens, work, addons, hooks, memory, settings
  --counts         numbers instead of names for skills, MCP servers, plugins, subagent types and memory files
  --rename a=b     show name a as b (repeatable); fails if a isn't on the receipt, so a typo can't leak it
  --prompt         also print your first prompt (left out by default; it can hold paths or names)

  --md             wrap it in a code block for GitHub or Discord
  --json           machine-readable (the same parts left out)

Paths, your email, account ids and file contents never print. Standard library only.
Prompts and page text: https://musharna.github.io/prompt-receipts/ (CC BY 4.0)."""

import argparse
import collections
import datetime
import glob
import json
import os
import re
import sys

PARTS = [
    "version",
    "date",
    "model",
    "time",
    "cost",
    "tokens",
    "work",
    "addons",
    "hooks",
    "memory",
    "settings",
]


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


def cut_at(stamps, last):
    """-> timestamp of the Nth-last prompt, or None for the whole session"""
    if not last:
        return None
    if last > len(stamps):
        sys.exit(
            f"receipt: --last {last}, but this session has only {len(stamps)} prompts"
        )
    return stamps[-last]


# ---------- Claude Code ----------


def claude_prompt(d):
    """-> your prompt text if this entry is one, else None"""
    if d.get("type") != "user" or d.get("isSidechain") or d.get("isMeta"):
        return None
    if (d.get("origin") or {}).get("kind", "human") != "human":
        return None
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
        return text
    return None


def claude(path, last=None):
    entries = list(lines(path))
    prompt_stamps = [
        d.get("timestamp") or "" for d in entries if claude_prompt(d) is not None
    ]
    cut = cut_at(prompt_stamps, last)
    r = {
        "tool": "Claude Code",
        "part": ("last prompt" if last == 1 else f"last {last} prompts")
        if cut is not None
        else "whole session",
    }
    versions, models, efforts, perms, stamps = [], [], [], [], []
    tools, skills, mcp, agents, hooks = (collections.Counter() for _ in range(5))
    memory, mcp_servers, skill_names = {}, set(), set()
    invoked_before, invoked_after = set(), set()
    skill_count, prompts, first_prompt, cost = None, 0, None, None
    usage_by_msg, server_web, context_hooks = {}, 0, 0
    for d in entries:
        t, ts = d.get("type"), d.get("timestamp") or ""
        inside = cut is None or (ts and ts >= cut)
        # what was loaded: whole session, whatever part the receipt covers
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
        text = claude_prompt(d)
        if text is not None:
            prompts += 1
            first_prompt = first_prompt or text
        elif t == "assistant" and not d.get("isSidechain"):
            m = d.get("message") or {}
            if m.get("model") and not m["model"].startswith("<"):
                models.append(m["model"])
            if m.get("usage"):
                usage_by_msg[m.get("id") or id(d)] = m[
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
    if cut is None and len(metas) > sum(agents.values()):
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
    if cost:
        r["cost_usd"] = round(cost.get("totalCostUSD", 0), 2)
        r["cost_note"] = "Claude Code's estimate at API prices" + (
            "; some model costs unknown" if cost.get("hasUnknownModelCost") else ""
        )
        if cut:
            r["cost_note"] = "whole session; " + r["cost_note"]
        mu = cost.get("modelUsage") or {}
        main = {re.sub(r"\[.*\]$", "", m) for m in models}
        r["background_models"] = sorted({re.sub(r"\[.*\]$", "", m) for m in mu} - main)
        if cut is None:
            r["model_time_ms"] = cost.get("totalAPIDuration")
            r["lines_changed"] = [
                cost.get("totalLinesAdded", 0),
                cost.get("totalLinesRemoved", 0),
            ]
            r["tokens_in"] = sum(
                v.get("inputTokens", 0)
                + v.get("cacheReadInputTokens", 0)
                + v.get("cacheCreationInputTokens", 0)
                for v in mu.values()
            )
            r["tokens_cached"] = sum(
                v.get("cacheReadInputTokens", 0) for v in mu.values()
            )
            r["tokens_out"] = sum(v.get("outputTokens", 0) for v in mu.values())
    else:
        r["cost_note"] = "not in this log (older Claude Code versions don't write it)"
    if cut is not None or "tokens_in" not in r:
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


def codex(path, last=None):
    entries = list(lines(path))
    prompt_at = [i for i, d in enumerate(entries) if codex_prompt(d) is not None]
    cut = cut_at(prompt_at, last)
    if (
        cut is not None
    ):  # a turn's settings are logged just before its prompt: start at the turn
        starts = [
            i
            for i, d in enumerate(entries[: cut + 1])
            if d.get("type") == "event_msg"
            and (d.get("payload") or {}).get("type") == "task_started"
        ]
        cut = starts[-1] if starts else cut
    r = {
        "tool": "Codex CLI",
        "part": ("last prompt" if last == 1 else f"last {last} prompts")
        if cut is not None
        else "whole session",
    }
    versions, models, efforts, sandboxes, approvals, stamps = [], [], [], [], [], []
    calls, skills, mcp = (
        collections.Counter(),
        collections.Counter(),
        collections.Counter(),
    )
    prompts, first_prompt, agents_md, web, images, busy = 0, None, False, 0, 0, 0
    # Codex's running total restarts with each process (every `codex exec resume`), so add up each
    # model call's own usage instead; the same event is often logged twice, so skip unchanged totals
    usage, last_total = collections.Counter(), None
    for i, d in enumerate(entries):
        t, p, ts = d.get("type"), d.get("payload") or {}, d.get("timestamp") or ""
        inside = cut is None or i >= cut
        if t == "session_meta":
            versions.append(p.get("cli_version"))
        elif t == "event_msg" and p.get("type") == "token_count" and p.get("info"):
            total = p["info"].get("total_token_usage")
            if inside and total != last_total:
                usage.update(p["info"].get("last_token_usage") or {})
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
        elif t == "event_msg" and p.get("type") == "task_complete":
            busy += p.get("duration_ms") or 0
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
    if last_total is not None:
        r["tokens_in"] = usage["input_tokens"]
        r["tokens_cached"] = usage["cached_input_tokens"]
        r["tokens_out"] = usage["output_tokens"]
    r["tool_calls"] = sum(calls.values())
    r["shell_commands"] = calls.get("exec", 0) + calls.get("shell", 0)
    r["web"] = web
    r["images_made"] = images
    r["skills_used"] = dict(skills)
    r["mcp_used"] = dict(mcp)
    r["hooks"] = None  # Codex session logs don't record hook runs
    r["memory"] = ["AGENTS.md"] if agents_md else []
    r["first_prompt"] = first_prompt
    return r


# ---------- leaving things out ----------

NAMED = [
    "skills_used",
    "mcp_used",
    "subagents",
    "plugins_used",
    "memory",
    "models",
    "background_models",
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
    r["memory"] = len(r.get("memory") or [])


DROP = {
    "version": ["version"],
    "date": ["started", "ended"],
    "model": ["models", "background_models", "effort"],
    "time": ["started", "ended", "model_time_ms", "prompts"],
    "cost": ["cost_usd", "cost_note"],
    "tokens": ["tokens_in", "tokens_cached", "tokens_out", "tokens_note"],
    "work": ["tool_calls", "shell_commands", "web", "images_made", "lines_changed"],
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


def text(r, hide, with_prompt):
    head = f"Receipt · {r['tool']}"
    if "version" not in hide:
        head += f" {r['version']}"
    if "date" not in hide:
        head += f" · {when(r['started']):%-d %b %Y}"
    if r["part"] != "whole session":
        head += f" · {r['part']}"
    out = [head]
    if "model" not in hide:
        bg = r.get("background_models")
        bg = f" (+ {', '.join(bg)} in the background)" if bg else ""
        out.append(
            f"model    {', '.join(r['models']) or 'no model reply in this log'}{bg} · effort {r['effort']}"
        )
    if "time" not in hide:
        took = mins((when(r["ended"]) - when(r["started"])).total_seconds() * 1000)
        if r.get("model_time_ms"):
            took += f" (model working {mins(r['model_time_ms'])})"
        out.append(
            f"time     {took} · {r['prompts']} prompt{'s' if r['prompts'] != 1 else ''} from me"
        )
    if "cost" not in hide:
        if "cost_usd" in r:
            money = f"${r['cost_usd']:.2f}" if r["cost_usd"] >= 0.01 else "<$0.01"
            out.append(f"cost     {money} ({r['cost_note']})")
        else:
            out.append(f"cost     {r['cost_note']}")
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
        out.append(f"work     {work}")
    if "addons" not in hide:
        sk = f"skills {names(r['skills_used'])}"
        if r.get("skills_available") is not None:
            sk += f" (of {r['skills_available']} available)"
        mc = f"MCP {names(r['mcp_used'])}"
        if r.get("mcp_connected") is not None:
            mc += f" (of {r['mcp_connected']} connected)"
        line = f"add-ons  {sk} · {mc}"
        if "plugins_used" in r:
            pu = r["plugins_used"]
            pu = (f"{pu} used" if isinstance(pu, int) else ", ".join(pu)) or "none"
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
            out.append("hooks    not in Codex logs")
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
        m = r["memory"]
        m = (
            (f"{m} file{'s' if m != 1 else ''}" if m else "none loaded")
            if isinstance(m, int)
            else (", ".join(m) or "none loaded")
        )
        out.append(f"memory   {m}")
    if "settings" not in hide:
        out.append(f"settings {r['permissions']}")
    if with_prompt and r.get("first_prompt"):
        out.append("prompt   " + r["first_prompt"].strip().replace("\n", "\n         "))
    return "\n".join(out)


# ---------- finding sessions ----------


def sessions(codex_mode):
    home, here = os.path.expanduser("~"), os.getcwd()
    if codex_mode:
        out = []
        for f in sorted(
            glob.glob(f"{home}/.codex/sessions/*/*/*/rollout-*.jsonl"),
            key=os.path.getmtime,
            reverse=True,
        ):
            for d in lines(f):
                if d.get("type") == "session_meta":
                    if (d.get("payload") or {}).get("cwd") == here:
                        out.append(f)
                    break
        return out, f"~/.codex/sessions (cwd {here})"
    slug = re.sub(r"[^A-Za-z0-9]", "-", here)
    fs = sorted(
        glob.glob(f"{home}/.claude/projects/{slug}/*.jsonl"),
        key=os.path.getmtime,
        reverse=True,
    )
    return fs, f"~/.claude/projects/{slug}/"


def first_prompt_of(path, codex_mode):
    for d in lines(path):
        t = codex_prompt(d) if codex_mode else claude_prompt(d)
        if t is not None:
            return t.strip().replace("\n", " ")
    return ""


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="parts for --hide: " + ", ".join(PARTS),
    )
    ap.add_argument("session", nargs="?")
    ap.add_argument("--codex", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--pick", type=int)
    ap.add_argument("--last", type=int)
    ap.add_argument("--hide", default="")
    ap.add_argument("--counts", action="store_true")
    ap.add_argument("--rename", action="append", default=[])
    ap.add_argument("--prompt", action="store_true")
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    hide = {h.strip() for h in a.hide.split(",") if h.strip()}
    if hide - set(PARTS):
        sys.exit(
            f"receipt: --hide doesn't know {', '.join(sorted(hide - set(PARTS)))}; parts are: {', '.join(PARTS)}"
        )
    if a.last is not None and a.last < 1:
        sys.exit("receipt: --last needs a number of prompts, 1 or more")
    path, is_codex = a.session, a.codex
    if path:
        is_codex = (
            is_codex
            or "/.codex/" in os.path.abspath(path)
            or os.path.basename(path).startswith("rollout-")
        )
    else:
        fs, where = sessions(a.codex)
        if not fs:
            kind = "Codex" if a.codex else "Claude Code"
            sys.exit(
                f"receipt: no {kind} session found for this folder (looked in {where})"
            )
        if a.list:
            for i, f in enumerate(fs[:15], 1):
                stamp = datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime(
                    "%d %b %H:%M"
                )
                print(f"{i:3}  {stamp}  {first_prompt_of(f, a.codex)[:70]}")
            print(
                "\nthen: python3 receipt.py --pick N" + (" --codex" if a.codex else ""),
                file=sys.stderr,
            )
            return
        n = a.pick or 1
        if not 1 <= n <= len(fs):
            sys.exit(
                f"receipt: --pick {n}, but this folder has {len(fs)} sessions (see --list)"
            )
        path = fs[n - 1]
    r = codex(path, a.last) if is_codex else claude(path, a.last)
    if a.rename:
        rename(r, a.rename)
    if a.counts:
        counts_only(r)
    if a.json:
        for part in hide:
            for key in DROP[part]:
                r.pop(key, None)
        if not a.prompt:
            r.pop("first_prompt", None)
        print(json.dumps(r, indent=1))
        return
    s = text(r, hide, a.prompt)
    print(f"```\n{s}\n```" if a.md else s)
    print(
        "\nreceipt: check it before you share. To leave things out: --hide cost,date,… · --counts (no names) · "
        "--rename name=label · --last N (just your last N prompts). More: --help",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
