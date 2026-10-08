# Prompt Receipts

Prompts for making things with Claude Code, each run once on plain Claude Code (Opus, Sonnet and Haiku 5.5) next to GPT-5.6 Sol, Terra and Luna in Codex, all at medium effort, plus GPT-6-Astra, Codex's default model. Every run shows what came out, what it cost and how long it took.

Site: https://musharna.github.io/prompt-receipts/

Tried one? Use the "Tell us how it went" button on its card. Runs that didn't work are as useful as ones that did.

## Make a receipt for your own run

In the folder where you ran Claude Code:

```
curl -sO https://musharna.github.io/prompt-receipts/tools/receipt.py && python3 receipt.py
```

It reads the session log Claude Code or Codex already keeps (`~/.claude/projects/` or `~/.codex/sessions/`), needs only Python 3, and never prints paths, your email, account ids or file contents. For a whole Claude Code session, the cost and token totals are Claude Code's own and include subagents.

You don't need to set anything up first: it works on any past session whose log is still there. Claude Code deletes logs older than 30 days unless you raise `cleanupPeriodDays` in `~/.claude/settings.json`; Codex keeps them. Logs can be large, so check your free disk space before raising it a lot.

Example:

```
Receipt · Codex CLI 0.153.4 · 7 Oct 2026
model    gpt-5.6-sol · effort medium
time     85 s (model working 80 s) · 1 prompt from me
cost     Codex logs no price (ChatGPT plans don't bill per run)
tokens   in 133k (120k cached) · out 1k
work     5 tool calls, 5 shell commands · web 0
add-ons  skills imagegen · MCP none
hooks    not in Codex logs
memory   AGENTS.md
settings sandbox workspace-write, network off · approvals never
```

**Choosing what it covers**

- `--codex` uses Codex sessions instead of Claude Code ones.
- `--list` shows this folder's recent sessions; `--pick N` makes a receipt for one of them.
- `--last N` covers only your last N prompts, for when one session held several tasks. Its cost stays the whole session's, because Claude Code doesn't log cost per prompt, and its token count covers the main conversation only.

**Leaving things out** (read the receipt before you share it)

- `--hide cost,date` drops any of: version, date, model, time, cost, tokens, work, addons, hooks, memory, settings.
- `--counts` shows numbers instead of the names of skills, MCP servers, plugins, subagent types and memory files.
- `--rename my-work-db=database` relabels one name. If the name isn't on the receipt it stops with an error, so a typo can't leave the real name in.
- `--prompt` adds your first prompt. It's off by default because prompts can hold paths or names.
- `--md` wraps the receipt for GitHub or Discord; `--json` gives the same fields, with hidden parts left out.

**Not checked yet**

- Tested on Linux (WSL) only, not macOS or Windows. On Windows you may need `py` instead of `python3`.
- A Claude Code session resumed into a new log file gets its own receipt; the parts aren't joined.
- Codex logs don't record hooks, and Claude Code logs a hook run only when the hook prints something, so hook counts are a floor.
- A receipt is text you can edit. It shows what someone reports, not proof.

Prompts and page text are CC BY 4.0. See LICENSE.
