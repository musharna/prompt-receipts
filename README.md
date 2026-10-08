# Prompt Receipts

Prompts for making things with Claude Code and Codex, each shown with a receipt: what it cost, how long it took and what was switched on. Plus a script that prints the same receipt for your own runs.

**[Browse the prompts](https://musharna.github.io/prompt-receipts/)** · **[Make a receipt for your own run](#make-a-receipt-for-your-own-run)**

[![One prompt, run once on each model: Opus, Sonnet and Haiku 5.5 in Claude Code, and GPT-5.6 Sol, Terra and Luna in Codex](og.png)](https://musharna.github.io/prompt-receipts/)

## Make a receipt for your own run

In the folder where you ran Claude Code:

```
curl -sO https://musharna.github.io/prompt-receipts/tools/receipt.py && python3 receipt.py
```

Add `--codex` for a Codex session. It reads the log Claude Code and Codex already keep, so it works on runs you've already finished. It needs only Python 3 and never prints paths, your email, account ids or file contents.

Here is one prompt from the site, run once on plain Opus 5.5, and its receipt:

<a href="https://musharna.github.io/prompt-receipts/play/1bfe1ef0-9a8/index.html"><img src="m/1bfe1ef0-9a8_opus_0.webp" width="420" alt="A round green blob mascot, with smaller versions in four moods: idle, happy, sleepy and surprised"></a>

```
$ python3 receipt.py --prompt
Receipt · Claude Code 2.1.292 · 6 Oct 2026
model    claude-opus-5-5 · effort medium
time     4 min (model working 4 min) · 1 prompt from me
cost     $0.83 (Claude Code's estimate at API prices)
tokens   in 306k (273k cached) · out 25k
work     13 tool calls, 6 shell commands · web 0 · lines +537 -0
add-ons  skills none (of 14 available) · MCP none (of 0 connected) · plugins none · subagents 0
hooks    none logged
memory   none loaded
settings bypassPermissions
prompt   A mascot for my habit-tracker app: a round blob that breathes, blinks and
         giggles when you poke it. I'd like it in four moods: idle, happy, sleepy and
         surprised.
```

[Play with it](https://musharna.github.io/prompt-receipts/play/1bfe1ef0-9a8/index.html) or [see the other models' versions](https://musharna.github.io/prompt-receipts/#1bfe1ef0-9a8).

### Choosing what it covers

| Option | What it does |
|---|---|
| `--codex` | Use Codex sessions instead of Claude Code ones |
| `--list`, then `--pick N` | List this folder's recent sessions, then make a receipt for one of them |
| `--last N` | Cover only your last N prompts, when one session held several tasks |
| `SESSION.jsonl` | Make a receipt for a log file directly |

### Leaving things out

Read the receipt before you share it. Prompts, tool names and times can say more than you mean to.

| Option | What it does |
|---|---|
| `--hide cost,date` | Drop parts: version, date, model, time, cost, tokens, work, addons, hooks, memory, settings |
| `--counts` | Show numbers instead of the names of skills, MCP servers, plugins, subagent types and memory files |
| `--rename old=new` | Show one name as another. Stops with an error if the name isn't on the receipt, so a typo can't leave the real one in |
| `--prompt` | Add your first prompt. Off by default, because prompts can hold paths or names |
| `--md`, `--json` | Wrap it for GitHub or Discord, or print it as JSON (hidden parts stay out) |

### Good to know

- Claude Code deletes session logs after 30 days unless you raise `cleanupPeriodDays` in `~/.claude/settings.json`. Logs can be large, so check your free disk space before raising it a lot. Codex keeps its logs.
- For a whole Claude Code session, the cost and tokens are Claude Code's own totals and include subagents. With `--last`, the cost stays the whole session's, because Claude Code doesn't log cost per prompt.
- Codex logs don't record hooks. Claude Code logs a hook run only when the hook prints something, so hook counts are a floor.
- Tested on Linux (WSL) only. On Windows you may need `py` instead of `python3`.
- A Claude Code session resumed into a new log file gets its own receipt; the parts aren't joined.
- A receipt is text you can edit. It shows what someone reports, not proof.

## The prompts

Each prompt on [the site](https://musharna.github.io/prompt-receipts/) was run once on plain Claude Code (Opus, Sonnet and Haiku 5.5) and on GPT-5.6 Sol, Terra and Luna in Codex, all at medium effort, plus GPT-6-Astra, Codex's default model. Every run shows what came out, what it cost and how long it took.

Tried one? Use the "Tell us how it went" button on its card. Runs that didn't work are as useful as ones that did.

## License

Prompts and page text are CC BY 4.0 (see [LICENSE](LICENSE)). The outputs were made by the models named on each card.
