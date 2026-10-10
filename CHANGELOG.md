# Changelog

## receipt.py 7.1 (2026-10-10)

- Reads the output of `claude -p --output-format stream-json --verbose` saved to a file, like a session log: cost and output tokens from its result, time from its duration, subagents' files included. The prompt, effort, hooks and memory files aren't in that output, and the receipt says so.
- Fixed: a file the run wrote and then changed with a shell command was measured, shown and recorded as first written. It is now taken as the run left it on disk, when the file was last changed before the run ended.

## receipt.py 7.0 (2026-10-10)

- The files line says how much the run wrote (lines and size) and whether one file is a web page, and a new replies line counts the model's replies and their words. No names or text. `--hide output` drops both.
- `--page FILE.html`: one page with the receipt, every prompt and full reply, the files the run wrote, and each web page it made running in a sandboxed frame with its own .js, .css and pictures inside. The text is checked for email addresses and keys like `--prompt`. A bundle's preview page is now this page.
- `--output-url URL`: with `--page`, the receipt carries where the page will live and its SHA-256, and the receipt site fetches the page and shows it only if it matches.
- `--record` and `--bundle` now cover Qwen Code, Gemini CLI and Copilot CLI.
- On PyPI: `pipx install prompt-receipts`, or `uvx prompt-receipts` to run it without installing.

## receipt.py 6.0 (2026-10-09)

- `--totals`: cost, sessions, prompts, time and tokens added up by day, `week`, `month`, `folder` or `model`, over this folder's sessions or every folder's (`--all`). `--since DATE` and `--until DATE` set the range.
- New tools: Qwen Code (`--qwen`), Gemini CLI (`--gemini`) and GitHub Copilot CLI (`--copilot`), with `--turns`, `--recipe`, `--list` and `--totals`. A log file passed directly is recognized by where it lives. Qwen Code's background calls are counted; Copilot's AI credits go on the billing line when the log has them.
- `--statusline`: a status line for Claude Code (model, cost, time, and your plan's 5-hour and weekly use on Pro and Max). It keeps the readings, so later receipts for those sessions say how much of the plan the run took.
- Installs as a command: `uvx --from git+https://github.com/musharna/prompt-receipts receipt`, or `pipx install` from the same address. The commands are `receipt` and `prompt-receipts`.
- Prices for Google's Gemini models and Alibaba Cloud's Qwen models (priced by prompt size), from the same LiteLLM copy. Copilot's model names (`claude-opus-4.7`) are matched to them.
- The code is now under the MIT License (`LICENSE`). Prompts and page text stay CC BY 4.0, now in `LICENSE-prompts`.
- Fixed: with `--turns`, a prompt's time could run on until the next prompt (one showed 120 hours for a 2-minute run). Time now ends at the prompt's last reply, tool result or interruption.

## receipt.py 5.0 (2026-10-09)

- `--turns`: a line per prompt with when it was sent, how long it ran, its cost at API prices (subagents included), tool calls and files, and whether the lines add up to the cost above. `--turns A-B` covers only those prompts, receipt and record both.
- `--prompt` shows every prompt, numbered, each checked for email addresses and keys. `--reply` adds the model's last reply, checked the same way; `--outcome TEXT` adds your own word on how it went.
- `--recipe`: the commands that send the same prompts again (`claude -p`, `codex exec`, `opencode run`), each with the model and effort it ran on, quoted for the shell.
- `--link`: a link that shows the receipt on the site, carried in the part after `#`, so nothing is uploaded.
- `--bundle FILE.zip`: the receipt, its JSON, a record and the files the run wrote in one RO-Crate zip; `--shot` adds a screenshot of the web page the run made.
- Records hold a fingerprint of each prompt's last reply, so `--verify` can say a pasted answer came out of the run.
- Files written by subagents are counted and recorded.
- Fixed: `--hide model` left the model names in the priced lines, and `--rename` didn't rename them there.
- Fixed: a long prompt could be wrapped in the middle of a path or link, at a hyphen, so it no longer worked when copied.
- Fixed: `--prompt` left your user name in a WSL home folder written the Windows way (`\\wsl.localhost\Ubuntu\home\you`); it shows as `~` now.

## receipt.py 4.0 (2026-10-09)

- The cost is itemized: tokens of each kind (input, cache read, cache write at 5 minutes and 1 hour, output, web searches) per model, at API list prices per million, with the price source and date. Fast mode, US-only processing and long-context rates are priced and shown when used; thinking time and time waiting on retries too.
- An add-up check: the receipt says whether its lines add up to Claude Code's own total, or by how much they miss.
- Codex runs get a cost, worked out from their token counts (Codex logs no price). `--last` is priced from that part's own calls. `--prices FILE` uses a newer LiteLLM price file; `tools/update_prices.py` refreshes the built-in one.
- A receipt number (the same for the same session and part, and it gives nothing away) and the time of day with its time zone.
- `--record FILE`: an in-toto Statement holding SHA-256 fingerprints of the prompts, system prompt, instruction files as loaded, tool results the model saw and files it wrote, plus model and settings. No text, no paths. `--verify RECORD FILES…` says which files came out of the run or went into it.
- `--sign KEY` signs receipts and records with an SSH key; `--verify` checks the signature, and `--signers` checks whose key it was.
- Fixed: a Claude Code session opened more than once showed only the cost since it was last opened (one session showed $5.33 of $70.34). Costs are now added up over every time it was opened.
- Fixed: costs under a cent showed as $0.00, and waits under half a second as "0 s".

## receipt.py 3.0 (2026-10-09)

- Reads OpenCode sessions (`--opencode`, or an `ses_…` id).
- Run in the wrong folder, it says where your sessions are; `--list --all` and `--pick N --all` cover every folder. Honors `CLAUDE_CONFIG_DIR`, `CODEX_HOME` and `XDG_DATA_HOME`.
- New lines: billing (your plan, read from the account as it is today), files written or edited (count and types; names with `--file-names`), failed tool calls and interrupted prompts. Runs on a local model say so.
- `--prompt` turns home folders into `~` and stops if the prompt holds an email address or a key; `--redact` prints it with those blanked instead.
- `--version`, and the version on every receipt. Warns when a log has prompts but no replies or token counts.
- `--out` saves to a `.txt`, `.md`, `.json` or `.png` file, or into a folder. The PNG needs no extra packages.
- `--report` prints a link to the report form with the receipt filled in.
- `--hook` writes a receipt when a Claude Code session ends (see the README for the settings snippet).
- `--prompt-id`, `--combine` and `--compare`: add up one task over several sessions, or set runs of one prompt side by side.
- Reads logs as a stream, so large logs use far less memory.
- Fixed: Claude Code's "[Request interrupted by user]" was counted as a prompt.
- Tests run on Linux, macOS and Windows with Python 3.9 and 3.13 on every push.

## Before 3.0 (2026-10-07, unnumbered)

- The site: 16 prompts, each run once on Claude Opus, Sonnet and Haiku 5.5 and on GPT-5.6 Sol, Terra and Luna and GPT-6-Astra in Codex, with what came out, cost, time and receipt details per run.
- `tools/receipt.py`: a receipt for your own Claude Code or Codex run, from its session log.
- Leaving things out (`--hide`, `--counts`, `--rename`) and covering part of a session (`--last`, `--list`/`--pick`); hooks, plugins and subagent types on the receipt.
- Fixed: Codex token totals across resumed runs; a crash on Windows, plus UTF-8 output and a PowerShell install line.
- `tools/tally.py` counts form reports per page version, prompt and model.
