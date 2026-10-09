# Prompt Receipts

[![tests](https://github.com/musharna/prompt-receipts/actions/workflows/test.yml/badge.svg)](https://github.com/musharna/prompt-receipts/actions/workflows/test.yml)

Prompts for making things with Claude Code and Codex, each shown with a receipt: what it cost, how long it took and what was switched on. Plus a script that prints the same receipt for your own runs in Claude Code, Codex or OpenCode.

**[Browse the prompts](https://musharna.github.io/prompt-receipts/)** · **[Make a receipt for your own run](#make-a-receipt-for-your-own-run)**

[![One prompt, run once on each model: Opus, Sonnet and Haiku 5.5 in Claude Code, and GPT-5.6 Sol, Terra and Luna in Codex](og.png)](https://musharna.github.io/prompt-receipts/)

## Make a receipt for your own run

In the folder where you ran Claude Code:

```
curl -sO https://musharna.github.io/prompt-receipts/tools/receipt.py && python3 receipt.py
```

On Windows, in PowerShell:

```
curl.exe -sO https://musharna.github.io/prompt-receipts/tools/receipt.py; py receipt.py
```

Add `--codex` for a Codex session or `--opencode` for OpenCode. Run it somewhere else and it tells you where your sessions are; `--list --all` lists them from every folder. It reads the logs these tools already keep, so it works on runs you've already finished. It needs only Python 3 and never prints paths, your email, account ids or file contents; only `--bundle` packs the files a run wrote, and only when you ask.

Here is one prompt from the site, run once on plain Opus 5.5, and its receipt:

<a href="https://musharna.github.io/prompt-receipts/play/1bfe1ef0-9a8/index.html"><img src="m/1bfe1ef0-9a8_opus_0.webp" width="420" alt="A round green blob mascot, with smaller versions in four moods: idle, happy, sleepy and surprised"></a>

```
$ python3 receipt.py --prompt
Receipt v5.0 · Claude Code 2.1.292 · 6 Oct 2026, 8:16 PM EDT · no. 5631-4887
model    claude-opus-5-5 · effort medium
time     4 min (model working 4 min) · 1 prompt from me
cost     $0.83 (Claude Code's own total at API prices; the lines below add up to it)
         claude-opus-5-5
           input                  18 × $4.00/M   <$0.01
           cache read           273k × $0.20/M    $0.05
           cache write (1 h)     33k × $8.00/M    $0.27
           output               25k × $20.00/M    $0.51
extras   thinking 2 min · waiting on retries <1 s
prices   API list prices per million tokens ($/M), from LiteLLM 05166e2, 9 Oct 2026
billing  Max plan: a flat fee, not charged per run (your account today)
tokens   in 306k (273k cached) · out 25k
work     13 tool calls, 6 shell commands · web 0 · lines +537 -0
files    2 files written or edited (.html, .js)
add-ons  skills none (of 14 available) · MCP none (of 0 connected) · plugins none · subagents 0
hooks    none logged
memory   none loaded
settings bypassPermissions
id       680b62f5e76e (prompt fingerprint)
prompt   A mascot for my habit-tracker app: a round blob that breathes, blinks and
         giggles when you poke it. I'd like it in four moods: idle, happy, sleepy and
         surprised.
```

[Play with it](https://musharna.github.io/prompt-receipts/play/1bfe1ef0-9a8/index.html) or [see the other models' versions](https://musharna.github.io/prompt-receipts/#1bfe1ef0-9a8).

### Choosing what it covers

| Option | What it does |
|---|---|
| `--codex`, `--opencode` | Use Codex or OpenCode sessions instead of Claude Code ones |
| `--list`, then `--pick N` | List this folder's recent sessions, then make a receipt for one of them |
| `--all` | With `--list` or `--pick`: sessions from every folder |
| `--last N` | Cover only your last N prompts, when one session held several tasks |
| `--turns A-B` | Cover only prompts A to B (`3`, `3-5`, `3-` or `-5`). Its cost is worked out from those prompts' calls |
| `SESSION.jsonl` or `ses_…` | Make a receipt for a log file, or an OpenCode session id, directly |

### Leaving things out

Read the receipt before you share it. Prompts, tool names and times can say more than you mean to.

| Option | What it does |
|---|---|
| `--hide cost,date` | Drop parts: version, date, model, time, cost, items (the priced lines), billing, tokens, work, files, addons, hooks, memory, settings. Hiding the model or the cost hides the priced lines too, since they name both |
| `--counts` | Show numbers instead of the names of skills, MCP servers, plugins, subagent types and memory files |
| `--rename old=new` | Show one name as another. Stops with an error if the name isn't on the receipt, so a typo can't leave the real one in |
| `--prompt` | Add your prompts, each one numbered. Home folders become `~`, and it stops if a prompt holds an email address or a key |
| `--redact` | With `--prompt`, `--reply`, `--recipe` or `--outcome`: print the text with `[email]` and `[key]` in their place instead of stopping |
| `--file-names` | Name the files the run wrote. Off by default: the receipt shows only how many and their types |

### Prompt by prompt

| Option | What it does |
|---|---|
| `--turns` | Add a line per prompt: when you sent it, how long it ran, its cost (subagents included), tool calls and files. The receipt says whether the lines add up to the cost above |
| `--reply` | Add the model's last reply, checked for email addresses and keys like a prompt |
| `--outcome TEXT` | Add your own word on how it went, marked as yours |
| `--recipe` | Add the commands that send the same prompts again, each with the model and effort it ran on (`claude -p`, `codex exec`, `opencode run`). Models give a different answer each time, so it reruns the run, not its output |

### Saving and sharing

| Option | What it does |
|---|---|
| `--md`, `--json` | Wrap it for GitHub or Discord, or print it as JSON (hidden parts stay out) |
| `--out FILE` | Save it to a `.txt`, `.md`, `.json` or `.png` file, or into a folder |
| `--out receipt.png` | Draw it as a picture, for posting where text gets mangled |
| `--report` | Also print a link to [the report form](https://musharna.github.io/prompt-receipts/) with this receipt filled in |
| `--link` | Also print a link that shows this receipt on the site. The receipt rides in the part after `#`, which your browser never sends, so nothing is uploaded. Long receipts make links too long for some chats; it warns over 2,000 characters |
| `--bundle FILE.zip` | Save one zip with the receipt, its JSON, a record, and the files the run wrote, plus [RO-Crate](https://www.researchobject.org/ro-crate/) metadata and a page that shows the receipt |
| `--shot` | With `--bundle`: add a screenshot of the web page the run made, taken with Chrome, Edge or Chromium if one is installed. It shows the files in the bundle, served to the browser from your own computer only while the picture is taken; pictures the run didn't make aren't in it |
| `--prompt-id` | Add a short fingerprint of the prompt (not the prompt itself), so `--compare` can tell runs of one prompt |
| `--combine A.json B.json` | Add up receipts for one task spread over several sessions |
| `--compare A.json B.json` | Set receipts side by side, for one prompt run on several models or efforts |

### A record of what went in and came out

A receipt says what a run cost. A record says which files it made and what it was given, as SHA-256 fingerprints, so anyone holding a file can check whether it came out of that run. It holds no prompts, file contents or paths: only fingerprints of your prompts, the system prompt, the instruction files as they were loaded (`CLAUDE.md`, `AGENTS.md`), every tool result the model saw, and the files it wrote, plus the model, effort, settings and, for Codex, the git commit.

| Option | What it does |
|---|---|
| `--record FILE` | Save a record of the run. Its fingerprint goes on the receipt. `--hide`, `--counts`, `--rename` and `--file-names` apply to it too |
| `--verify RECORD FILES…` | Say for each file whether it came out of the run, went into it, or isn't in the record. One changed byte and it isn't |
| `--sign KEY` | Sign the receipt (`--out`) and the record with an SSH key (`ssh-keygen -Y sign`); the signature goes next to each as `.sig` |
| `--verify FILE` | Check the signature next to a receipt or record. Add `--signers allowed_signers` to check whose key signed it |
| `--prices FILE` | Price with a newer copy of LiteLLM's `model_prices_and_context_window.json` instead of the one built in |

A record is in-toto's [Statement](https://github.com/in-toto/attestation/blob/main/spec/v1/statement.md) format, written in one byte form (sorted keys, no spaces), so its fingerprint is the same wherever it's made. It makes a run checkable, not repeatable: neither tool lets you fix the model's randomness. Records of short prompts can be guessed by trying likely prompts, and a signature made after the run proves only what the log said when it was signed.

### A receipt after every Claude Code session

Put this in `~/.claude/settings.json` (merge it with any `hooks` you already have) and every session leaves a receipt in `~/receipts` when it ends:

```json
{
  "hooks": {
    "SessionEnd": [
      { "hooks": [{ "type": "command", "command": "python3 ~/receipt.py --hook --out ~/receipts/" }] }
    ]
  }
}
```

Keep `receipt.py` in your home folder for this, or change the path. Sessions with no prompts leave no receipt.

### Good to know

- Claude Code deletes session logs after 30 days unless you raise `cleanupPeriodDays` in `~/.claude/settings.json`. Logs can be large, so check your free disk space before raising it a lot. Codex and OpenCode keep theirs.
- If you moved Claude Code, Codex or OpenCode's folder with `CLAUDE_CONFIG_DIR`, `CODEX_HOME` or `XDG_DATA_HOME`, the receipt looks there.
- For a whole Claude Code session, the cost and tokens are Claude Code's own totals and include subagents, added up over every time the session was opened. The lines under the cost price each call at API list prices, and the receipt says whether they add up to Claude Code's total or by how much they miss; long sessions that were compacted many times can miss. With `--last`, the cost is worked out from that part's calls.
- Codex doesn't log a price, so a Codex cost is worked out from its token counts at API prices. OpenCode's own figure is used when it has one. The built-in prices are LiteLLM's, dated on the receipt; `python3 tools/update_prices.py` refreshes them.
- The billing line reads your account as it is today, so it shows your plan now, not necessarily when the run happened. A run on a local model (Ollama, LM Studio) says so on the model line.
- Files count what the edit tools wrote, subagents' included. Files made by shell commands aren't counted, and what subagents read isn't in a record.
- Codex logs don't record hooks, and OpenCode's record neither hooks nor memory files. Claude Code logs a hook run only when the hook prints something, so hook counts are a floor.
- If a log has your prompts but no replies or token counts, the receipt says so: the tool may have changed how it writes logs. Please [open an issue](https://github.com/musharna/prompt-receipts/issues).
- Checked on Linux, macOS and Windows (Python 3.9 and 3.13) on every change, and by hand on WSL and Windows 11.
- A Claude Code session resumed into a new log file gets its own receipt; `--combine` adds them up.
- A receipt is text you can edit. It shows what someone reports, not proof, unless it's signed by a key you trust.

## The prompts

Each prompt on [the site](https://musharna.github.io/prompt-receipts/) was run once on plain Claude Code (Opus, Sonnet and Haiku 5.5) and on GPT-5.6 Sol, Terra and Luna in Codex, all at medium effort, plus GPT-6-Astra, Codex's default model. Every run shows what came out, what it cost and how long it took.

Tried one? Use the "Tell us how it went" button on its card. Runs that didn't work are as useful as ones that did.

## License

Prompts and page text are CC BY 4.0 (see [LICENSE](LICENSE)). The outputs were made by the models named on each card.
