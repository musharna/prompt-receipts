# Changelog

## receipt.py 7.10 (2026-10-13)

The first release on PyPI since 7.8, so 7.9's `--share` and the gallery reach `pip`, `pipx` and `uvx` with it.

- The gallery has 28 more prompts, each run on the same 7 models (196 runs): audio, fonts, game art, carts, Godot shaders and toys, craft charts, video and more. Every run has its receipt, a preview, whether it worked and what it made, and 32 open with **Play it**. Runs that didn't work are in too.
- **What it makes**: filter the gallery by kind (Audio, Image, Video, 3D, Interactive, Game art, Print and craft, Type and text, Web effects, Motion, Generative), from a menu, the chips or a `?what=` link. The main page links to each.
- Fixed: a `claude -p` log that starts with a UI event before its init line (a first launch in an empty home writes one) was read as a session log, so the receipt said "Claude Code not recorded", worked its cost out from the calls instead of Claude Code's own total, and could count a note as a prompt.
- Sent-in receipts of several prompts: the gallery shows the first prompt and how many there were (before, a `--turns` receipt showed no prompt and a `--prompt` list ran its prompts together), and a receipt made with `--turns` links as **how it was made**. **Add yours**, the README and the issue form now lead with `--prompt --turns --recipe --redact --share`, and the form says sent-in prompts are CC BY 4.0, as the site's are.
- A sent-in receipt of one of the site's prompts shows with that prompt's runs. The site's owner can add a picture of what a sent-in run made (`gallery.py picture`), marked as the owner's; senders can't. Fixed: seeding the gallery again dropped the receipts people had sent.
- The runs are now sandboxed with an empty home, `/run`, `/var/tmp` and `/mnt`, and Codex with a fresh `CODEX_HOME` holding only the login. Before, a run could read other folders on the machine; of the new runs, any that did was run again.

## receipt.py 7.9 (2026-10-11)

- [The gallery](https://musharna.github.io/prompt-receipts/g/): the site's 112 runs and ones people send in, each with what it made, whether it worked, what it cost and how long it took, grouped by prompt, with a summary for each model. The 34 runs that made something a browser opens (a page, a toy, a 3D scene) open it with **Play it**, as the run left it. Search it, filter it by tool, model or result, or sort it by cost or time.
- `--share` prints the receipt's link and a link that sends it to the gallery: a GitHub issue with the link filled in. A bot replies with what the gallery will show, and it goes in once the site's owner approves it. A receipt page on the site has an **Add to the gallery** button that does the same, and the gallery has a box to paste a link into. The issue asks whether the run worked and what it made, shown in the gallery as the sender's word.

## receipt.py 7.8 (2026-10-11)

- `--reported FILE` makes a receipt of what someone's post says about a run: its prompt, model, cost, tokens, time and what it made, with the post's address. Every look carries a REPORTED stamp. Anything the post doesn't give reads "not stated". Stated tokens are priced next to the post's own figure, as the least the run could have cost. It has no receipt number, barcode or record.
- Reads `codex exec --json` output: replies, commands, files and tokens. The prompt, model, version and times aren't in it, and the receipt says so. `--model NAME` names the model, as the sender's word, and prices the tokens.
- Every run on the site links to its receipt.
- Fixed: Claude Code's own note after reading a picture counted as a prompt in `claude -p` output, so `--asked` refused the log and the receipt said 2 prompts.

## receipt.py 7.7 (2026-10-11)

- `--look card` makes a short receipt for a feed: the prompt in large letters, the picture as big as the rest leaves room for, the model, time and tool calls, and the total. It is 1080 pixels wide and at most 1350 tall (4:5), which X, Bluesky and LinkedIn show without cutting it; a short picture makes a shorter card. The cost breakdown and the rest stay on the full receipt.
- `--look print` sets the receipt in a real font, drawn by Chrome, Edge or Chromium (the one `--shot` uses), and cut where the paper ends. It still needs no extra packages.
- `--theme` picks the paper and ink: `paper`, `night`, `terminal`, `blueprint` or `pink`.
- The receipt picture reads more easily: ASKED FOR, MADE and IT TOOK on dark tags, the total twice the size, the cost breakdown faint, and the apostrophe no longer leaves a gap after it ("doesn't", not "doesn' t").
- A barcode (Code 128) of the receipt's number sits at the bottom of every look. On dark themes it is drawn dark on a light plate, so scanners read it.
- Every picture comes with alt text (what was asked for, what it shows, what it made, what it took, the total; 1,000 characters at most). It is printed to paste in with the picture and kept inside the PNG.

## receipt.py 7.6 (2026-10-10)

- `--asked FILE` puts the prompt on a receipt whose log doesn't hold it (`claude -p` output never does): from a file, or `-` for what you pipe in. It is checked for home folders, email addresses and keys like a logged prompt. The receipt adds a `given` line saying the prompt is the sender's words, not the log's; on a `.png` it sits faint under ASKED FOR, and `--page` shows it with the same note. A `--record` still fingerprints only what the log holds. It stops if the log holds its own prompt.
- The galaxy slime example on the site now shows its prompt, given with `--asked`.

## receipt.py 7.5 (2026-10-10)

- Files a run's programs made are counted: a new `made` line lists the files that changed in the run's folder while it ran and that its own tools didn't write (a script's sound, ffmpeg's video), with their size and, for sounds and videos, how long they are. They go in the record, the bundle and the page too. Hidden folders, `node_modules`, `__pycache__`, virtual environments and the home folder aren't looked in.
- `--page` plays sounds and videos: the files list has players for them, and a page the run made gets the sounds and videos it names put inside it. Pictures, sounds and videos go in up to 16 MB in all; past that, with ffmpeg installed, a sound or video is a smaller copy, made the same way each time so a page made again matches its gist copy. A bundle's page plays them from its `outputs/` folder.
- With ffmpeg (on the PATH, or `RECEIPT_FFMPEG`): `--picture` takes other pictures, other sounds (shown as spectrograms) and videos (shown as 4 frames), and `--shot` on a `.png` shows a run's video or sound when it made no page.
- Fixed: `--page` looked for keys and emails in the base64 of the pictures put inside a page, so a page with a picture or sound could stop with "key-like strings" it didn't have, and `--redact` could break the picture.

## receipt.py 7.4 (2026-10-10)

- `--picture` takes a `.wav` too, and puts its spectrogram on the receipt: time across, pitch up (on the mel scale, as ears hear it), louder brighter, with a line saying how long it is and the pitches it shows. It reads the WAVs most programs save (whole-number samples of 8 to 32 bits, or floats), any number of channels, and still needs no extra packages.
- `--picture` reads 16-bit PNGs, which some programs save, instead of stopping.
- A tall picture is made smaller to fit, as a wide one is; a tall sprite sheet made a receipt 3,620 pixels tall.

## receipt.py 7.3 (2026-10-10)

- A `.png` receipt reads like one from a shop: what was asked for (with `--prompt`), what the run made, what it took, and the total at the bottom.
- `--picture FILE.png` puts a picture of what the run made on it, and `--shot` now works with a `.png` too, putting a screenshot of the page the run made there. Pictures wider than the receipt are made smaller; it still needs no extra packages.
- Fixed: `--shot` could wait until its 60-second limit and give up on a page that draws in 3D. The browser's helper processes kept its output open after the browser was done, and the time budget it was given could take over 90 seconds to use up without a GPU. It now waits on the browser itself, stops its helpers, and gives a page 10 seconds to load.
- Fixed: on some Macs `--shot` took about 35 seconds longer than it should. The small web server that shows the browser the page looked up the name of 127.0.0.1 first; it no longer does.

## receipt.py 7.2 (2026-10-10)

- `--page` says how to share the page without a site of your own: put it in a public GitHub gist and make the receipt again with `--output-url` and the gist file's raw address. The receipt site checks gists like any other address.
- With `--output-url`, if a page was already saved at that path and the new one differs, it says so, since a copy uploaded before won't match the receipt.
- The receipt site wraps long addresses in its notes instead of running past the box.

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
