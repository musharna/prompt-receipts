# Changelog

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
