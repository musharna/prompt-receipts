# Prompt Receipts

Prompts for making things with Claude Code, each run once on plain Claude Code (Opus, Sonnet and Haiku 5.5) next to GPT-5.6 Sol, Terra and Luna in Codex, all at medium effort, plus GPT-6-Astra, Codex's default model. Every run shows what came out, what it cost and how long it took.

Site: https://musharna.github.io/prompt-receipts/

Tried one? Use the "Tell us how it went" button on its card. Runs that didn't work are as useful as ones that did.

## Make a receipt for your own run

In the folder where you ran Claude Code:

```
curl -sO https://musharna.github.io/prompt-receipts/tools/receipt.py && python3 receipt.py
```

Add `--codex` for a Codex session, `--md` to wrap it for GitHub or Discord, `--prompt` to include your first prompt. It reads the session log Claude Code or Codex already keeps (`~/.claude/projects/` or `~/.codex/sessions/`), needs only Python 3, and prints names and counts, not paths or file contents. Example:

```
Receipt · Codex CLI 0.153.4 · 7 Oct 2026
model    gpt-5.6-sol · effort medium
time     85 s (model working 80 s) · 1 prompt from me
cost     Codex logs no price (ChatGPT plans don't bill per run)
tokens   in 133k (120k cached) · out 1k
work     5 tool calls, 5 shell commands · web 0
add-ons  skills imagegen · MCP none
memory   AGENTS.md
settings sandbox workspace-write, network off · approvals never
```

Prompts and page text are CC BY 4.0. See LICENSE.
