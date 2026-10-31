# session2md

session2md turns local Claude Code, T3 Code, and Codex sessions into Markdown files for Obsidian. Choose a project folder, preview the counts, then export a linked conversation library. Common credentials and personal details are redacted before generated files are written.

The app runs on your computer with Python 3.11 or newer. It has a browser interface and a CLI, with no runtime dependencies, API keys, accounts, or cloud processing.

## Contents

- [Quick start](#quick-start)
- [Export one project folder](#export-one-project-folder)
- [How folder matching works](#how-folder-matching-works)
- [Sensitive-content redaction](#sensitive-content-redaction)
- [Add your own private values](#add-your-own-private-values)
- [Use the vault in Obsidian](#use-the-vault-in-obsidian)
- [Command-line reference](#command-line-reference)
- [Supported source files](#supported-source-files)
- [Repeat exports and existing vaults](#repeat-exports-and-existing-vaults)
- [Troubleshooting](#troubleshooting)
- [Performance and storage](#performance-and-storage)
- [Development](#development)

## Quick start

Clone the repository first:

```bash
git clone https://github.com/RyderAsKing/session2md.git
cd session2md
```

Run from the folder containing this README:

```bash
python3 --version
python3 -m session2md
```

On Windows:

```powershell
py -3 --version
py -3 -m session2md
```

The app opens at `http://127.0.0.1:8765`. Keep the terminal running while you use it. Stop it with Ctrl+C.

1. Check the detected history paths for Claude Code, T3 Code, and Codex. Disable sources you do not want to read.
2. Under **Which project do you want to export?**, enter the project working folder, such as `~/projects/reading-app`.
3. Keep **Include sessions started in subfolders** enabled, or turn it off for an exact directory match.
4. Add any private names, paths, or other exact values you want hidden in the custom-redaction field. Automatic detection is already on.
5. Choose a fresh destination, such as `~/Obsidian/reading-app-chats`.
6. Click **Preview counts** to check the selection and redaction counts without writing files.
7. Click **Export to Obsidian** when the selection is right.
8. Open the destination folder as a vault in Obsidian and start with **session2md home**.

The interface defaults to project-folder selection. An empty project field does not mean all chats. To export all available sessions, deliberately select **All chats from the enabled sources**.

To try it without reading your history, click **Create a sample vault**. That button exports three fictional conversations to a separate destination ending in `-demo`. A generated sample is also included in [examples/session2md](examples/session2md/session2md%20home.md).

If the port is busy or you do not want a browser opened automatically:

```bash
python3 -m session2md serve --port 8766 --no-browser
```

You can optionally install a `session2md` command:

```bash
python3 -m pip install .
session2md
```

## Export one project folder

Three paths have different jobs:

| Path | Example | Purpose |
| --- | --- | --- |
| Source history | `~/.codex` | Where the app stores its session records |
| Project folder | `~/projects/reading-app` | Which sessions you want to select |
| Destination vault | `~/Obsidian/reading-app-chats` | Where session2md writes Markdown |

The project folder does not need to contain transcript files. Codex stores history centrally, so you can read `~/.codex` while selecting only sessions whose recorded working directory belongs to your project.

Preview a project across all detected local sources:

```bash
python3 -m session2md export \
  --auto \
  --folder ~/projects/reading-app \
  --output ~/Obsidian/reading-app-chats \
  --dry-run
```

Export the same selection:

```bash
python3 -m session2md export \
  --auto \
  --folder ~/projects/reading-app \
  --output ~/Obsidian/reading-app-chats
```

Export only Codex sessions for that project:

```bash
python3 -m session2md export \
  --codex ~/.codex \
  --folder ~/projects/reading-app \
  --output ~/Obsidian/reading-app-codex
```

For an exact working-directory match, excluding sessions started in child directories:

```bash
python3 -m session2md export \
  --auto \
  --folder ~/projects/reading-app \
  --exact-folder \
  --output ~/Obsidian/reading-app-root-only
```

Windows example:

```powershell
py -3 -m session2md export --auto --folder "C:\Users\You\Projects\Reading App" --output "C:\Users\You\Documents\Reading App Chats"
```

Full-history exports require `--all`:

```bash
python3 -m session2md export --auto --all --output ~/Obsidian/all-chats
```

`--auto` discovers input locations. It does not select all chats or bypass the folder requirement. `--folder` and `--all` cannot be combined. The fictional `--demo` export is the only mode that does not need either one.

## How folder matching works

session2md matches filesystem paths from session metadata. It does not search the conversation for mentions of your folder.

| Source | Metadata used for matching |
| --- | --- |
| Claude Code | Recorded session `cwd` |
| Codex | `cwd` in the rollout's `session_meta` record |
| T3 Code | Thread worktree directory or the associated project's `workspace_root` |
| Optional ChatGPT file importer | No reliable local working-directory field; these chats are excluded from folder selections |

By default, `/work/app` matches sessions in `/work/app`, `/work/app/src`, and other descendants. It does not match `/work/app-other`. `--exact-folder` requires equality with one of the recorded roots.

For T3, a thread can match either its worktree or its project root. This lets an export for `/work/app` include T3 threads using an external worktree such as `/tmp/app-fix`, when T3 records that worktree under the project rooted at `/work/app`. Codex and Claude sessions only provide their recorded session working directory; session2md does not inspect Git to infer a parent repository for an external worktree.

Folder selections exclude sessions without a usable absolute working directory. The result includes a `missing_workspace` count for records without either directory field. Nonempty but relative or invalid metadata can also fail to match.

Paths expand `~` and normalize directory boundaries and `..`. Native paths resolve filesystem symlinks. Windows drive and UNC paths match without case sensitivity, including when importing copied histories on another operating system. POSIX matching is case-sensitive. A copied history can still be filtered using its original absolute path, even if that project is not present on this machine.

A matching session is exported in full, including its tool output and recorded alternate content. Folder filtering selects sessions, not individual messages. If a session later discussed or accessed other projects, those messages remain part of that session. Filtering does not read your project's source code.

If nothing matches, session2md reports that result and writes no vault files. A preview also writes no files, does not create the output folder, and does not update an existing manifest.

## Sensitive-content redaction

Automatic redaction is always enabled for exports and previews. It runs locally using deterministic patterns; no transcript is sent to an external model or service.

| Category | What it detects |
| --- | --- |
| `API_KEY` | Common OpenAI/Anthropic-style `sk-` tokens, GitHub token prefixes, Slack tokens, Google API key prefixes, and AWS access-key IDs |
| `PRIVATE_KEY` | Supported PEM/OpenSSH private-key blocks; a block without a closing marker is hidden through the end of that text field |
| `JWT` | JWT-shaped strings starting with `eyJ` and containing three encoded segments |
| `AUTHORIZATION` | Bearer and Basic authorization values |
| `URL_CREDENTIALS` | Username/password pairs in URLs such as database connection URLs |
| `SECRET_VALUE` | Values assigned to common password, token, secret, API-key, authorization, and cookie names in JSON, shell-style assignments, headers, and similar text |
| `EMAIL` | Common ASCII email-address forms |
| `SSN` | US Social Security number-shaped strings |
| `PAYMENT_CARD` | 13–19 digit card-shaped values that pass a Luhn checksum |
| `PHONE` | Common grouped ten-digit phone formats, optionally with an international prefix |
| `CUSTOM` | Your exact literal values |

For example, a message containing:

```text
DB_PASSWORD="fictional-example-password"
Contact: example.person@example.test
```

becomes:

```text
DB_PASSWORD="REDACTED-SECRET_VALUE"
Contact: REDACTED-EMAIL
```

Redaction covers normalized message bodies, tool calls and results, recorded reasoning text, user-derived titles, session metadata, project/workspace fields, branch labels, generated filenames, and generated indexes. Session IDs used as manifest lookup keys are hashed. User-visible session IDs are scanned before inclusion in frontmatter. Input warnings and export errors are scanned before display.

session2md writes **session2md privacy report.md** with rule-category counts for the current export. It stores no matched values, original excerpts, or recoverable secret map. The result returned by the CLI and interface also includes redaction counts. Counts represent matching occurrences across scanned fields, not unique secrets; a value repeated in a title and a message can count twice. A repeat export with a different set of input sources produces a report for that run, not the entire retained vault history.

Redaction changes the exported copy only. Original JSONL files and SQLite databases remain unchanged.

### Detection limits

Pattern matching can miss unknown token formats, encoded or split secrets, names, street addresses, medical details, proprietary prose, ungrouped phone numbers, and many international identifiers. It can also hide harmless examples and code values that look like credentials or personal details. A passing Luhn checksum does not prove that a number is a real payment card.

Workspace paths and ordinary project names remain visible unless a built-in rule matches them or you add a custom literal. This is a transcript exporter with a redaction pass, not an anonymity guarantee or encrypted vault. Review the generated files before sharing or publishing them.

Existing personal files in the destination are not scanned or scrubbed. A generated file you edited is preserved and reported as a conflict, so sensitive text you added to it remains there. Obsidian Sync, third-party plugins, and backup services operate separately from session2md.

## Add your own private values

Use custom literals for data that automatic patterns cannot identify, such as your name, a client name, an internal hostname, or a project directory.

In the interface, enter one exact value per line in **Also hide these exact values**. In the CLI, create a UTF-8 file, for example `~/private/session2md-redactions.txt`:

```text
Fictional Client Ltd
internal.example.test
/home/example/private-project
```

Then export:

```bash
python3 -m session2md export \
  --auto \
  --folder ~/projects/reading-app \
  --redact-file ~/private/session2md-redactions.txt \
  --output ~/Obsidian/reading-app-private
```

Custom literals are case-sensitive and are not regular expressions. Blank lines are ignored. Every nonblank value must have at least three characters. Leading and trailing spaces on a nonblank line are part of that value. Longer overlapping values take precedence. There is no comment syntax; a line beginning with `#` is still a literal value.

The literal file is read into memory. Its contents are not copied into the vault. The manifest stores a policy fingerprint derived from the literal hashes, not their original text. This fingerprint is not encryption for low-entropy values. Keep your own literal file private and use the same file on repeat exports.

Custom rules work after folder selection, so hiding the project directory does not prevent matching it. Changing the custom rule set requires a fresh output folder, as described below.

## Use the vault in Obsidian

1. Open Obsidian's vault switcher and choose **Open folder as vault**.
2. Select the export destination.
3. Open **session2md home** to browse source, project, month, and recent-conversation links.
4. In Settings → Appearance → CSS snippets, refresh the list and enable **session2md**.
5. Open Graph view to explore shared project and date connections.

The optional CSS snippet narrows transcript width, separates speaker headings, and styles code blocks using your Obsidian theme colors. It only targets session2md's CSS classes. No community plugin is required, and your existing Obsidian configuration is not replaced.

In Graph view, `path:Chats` focuses on transcript notes; `path:Indexes` shows index hubs. Leave both included to see conversations grouped by source, project, and month. Obsidian's normal search can find text inside every exported message.

Source tags are `#chats/claude`, `#chats/t3`, and `#chats/codex`. Properties include title, source, session ID, created/updated timestamps, project, workspace, T3 project root where known, recorded models, and recorded message count. Message counts describe normalized records; some records such as reasoning may be omitted from the visible transcript by your settings.

The vault contains:

```text
session2md home.md
session2md privacy report.md
Chats/
  Claude Code/<redacted title>--<stable hash>.md
  T3 Code/<redacted title>--<stable hash>.md
  Codex/<redacted title>--<stable hash>.md
Indexes/
  Sources/
  Projects/
  Months/
.obsidian/snippets/session2md.css
.session2md-manifest.json
```

Keep your commentary in separate notes linked to transcripts. That lets later exports update generated files without overwriting your annotations.

## Command-line reference

```text
python3 -m session2md
python3 -m session2md serve [--port PORT] [--no-browser]
python3 -m session2md discover
python3 -m session2md export [inputs] (--folder PATH | --all) --output PATH [options]
python3 -m session2md export --demo --output PATH [options]
```

| Option | Purpose |
| --- | --- |
| `--auto` | Detect local Claude Code, T3 Code, and Codex input locations |
| `--claude PATH` | Read a Claude projects directory or one JSONL transcript |
| `--t3 PATH` | Read a T3 userdata directory or SQLite database |
| `--codex PATH` | Read a Codex home, sessions/archive directory, or rollout JSONL |
| `--chatgpt PATH` | Optional legacy importer for a downloaded ChatGPT ZIP, JSON, or extracted directory |
| `--folder PATH` | Select sessions for this project directory, including descendants by default |
| `--exact-folder` | Match only the selected directory; requires `--folder` |
| `--all` | Explicitly select every available session in enabled inputs |
| `--output PATH`, `-o PATH` | Destination Obsidian vault |
| `--dry-run` | Return selection and redaction counts without writing files |
| `--redact-file PATH` | Add exact private values from a UTF-8 file |
| `--reasoning` | Include recorded Claude reasoning and Codex reasoning summaries |
| `--no-style` | Skip writing the Obsidian CSS snippet |
| `--demo` | Use fictional example sessions |

Explicit source paths override that source's `--auto` result. You can combine selected sources, for example `--claude PATH --codex PATH`, while omitting T3 entirely.

CLI export results are JSON:

| Field | Meaning |
| --- | --- |
| `imported` | Unique selected conversations, before any file conflicts |
| `excluded` | Read conversation records rejected by the folder filter |
| `missing_workspace` | Excluded records missing both directory fields |
| `dry_run` | Whether this was a preview |
| `redactions` | Replacement counts by category, without matched content |
| `written` | Generated files created or updated, including indexes and reports |
| `unchanged` | Generated files already matching the proposed content |
| `conflicts` | Existing files preserved because they differ from their last generated version |
| `vault` | Destination path, with sensitive matches hidden if applicable |
| `warnings` | Import, no-match, or conflict notices |

`excluded` and `missing_workspace` count reader records. T3 versions or copied rollouts can contain the same session more than once; those counts are not necessarily unique session counts. `imported` counts the merged selection. In a dry run, file-write and conflict counters remain zero because no writes are attempted.

Exit status is 0 for a clean result, 1 for warnings/conflicts or an export failure, and 2 for invalid CLI arguments. Redaction matches themselves are expected and do not make the command fail. `discover` prints local source locations without exporting chat content; it does not apply export redaction to those location strings.

## Supported source files

| Source | Default location | What session2md reads |
| --- | --- | --- |
| Claude Code | `~/.claude/projects` | Recursive JSONL transcripts and subagent files |
| Codex | `$CODEX_HOME` or `~/.codex` | `sessions` and `archived_sessions`, or a specific rollout file |
| T3 Code | `~/.t3/userdata` | `state.sqlite` and `statev2.sqlite` |

Claude imports text, tool blocks, results, and optionally reasoning. Duplicate recorded blocks are skipped; malformed JSON lines produce notices. Subagent files remain separate conversations even if they share a parent session ID.

Codex imports response messages, function/custom tool calls and outputs, and optional reasoning summaries. Event-only histories have a message fallback; event mirrors are skipped when corresponding response messages exist. Encrypted reasoning is not exported or decrypted. Repeated messages with distinct IDs remain separate.

T3 uses read-only SQLite transactions against recognized V1/V2 projection tables, including current WAL data. A userdata directory imports both database versions, merging distinct messages with matching thread IDs. Archived threads are included; deleted threads are excluded. Exports include messages and attachment references, not the complete activity/checkpoint timeline.

Binary attachments are not copied. Embedded images get placeholders where supported, and recorded media references remain in the Markdown after redaction. This is not a self-contained media backup.

Only history available in the supplied files can be exported. Deleted, expired, remote-only, and source-omitted sessions cannot be recovered. Paths in the interface refer to the computer running session2md, which may differ from the computer where you opened the browser.

## Repeat exports and existing vaults

The manifest records paths, generated-content hashes, and a fingerprint for the folder and redaction policy. Keep `.session2md-manifest.json` with the vault.

- An unchanged file is not rewritten.
- A renamed conversation keeps its generated path.
- Different conversations with the same title get separate files.
- A generated file you edited is preserved and reported as a conflict.
- Importing one source later retains earlier conversations from other sources under the same policy.
- Source transcripts are never modified, and exported files are never automatically pruned.

One vault uses one folder/redaction policy. Changing the selected folder, switching between a folder and all chats, changing exact/recursive matching, changing custom literals, or changing the redaction rules version causes session2md to stop before writing. Use a fresh output folder for the new policy. This prevents a project-specific export from quietly retaining unrelated chats from an earlier all-history export.

**Vaults generated under the previous name or before the redaction feature require a fresh output folder.** Enabling redaction now cannot remove originals already present in old filenames, edited notes, obsolete indexes, backups, or Obsidian history. session2md leaves those existing files unchanged rather than claiming they are sanitized. Do not remove the old manifest as a way to upgrade a sensitive vault.

Files already present in an unrelated destination are not taken over. If an existing generated filename differs from the new content and there is no matching stored hash, it is preserved as a conflict. Prefer a fresh folder for a project archive you plan to share.

Run only one export at a time for a given destination. The browser service serializes its own export requests, but separate CLI processes do not share that lock.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| `No module named session2md` | Run from this repository folder or install it with `python3 -m pip install .` |
| App cannot bind its port | Choose another port with `serve --port 8766` |
| A source is not detected | Enter its path manually; Codex discovery respects `CODEX_HOME`, T3 custom base directories need an explicit path |
| No sessions match | Use the original recorded project directory, check whether you need subfolders, and check missing-workspace counts |
| Source path vs project path confusion | Point sources at transcript storage; use the separate project field for your code directory |
| External Codex/Claude worktree is missing | Select its actual recorded worktree directory; only T3 provides the project-root mapping used here |
| Older files still contain secrets | Generate a fresh vault; existing notes and backups are not scrubbed |
| A harmless example was hidden | Review the source separately; broad pattern matches deliberately hide credential-shaped examples |
| A secret format was missed | Add the exact value to the custom-redaction file and export into a fresh folder |
| A generated file did not update | Check `conflicts`; keep annotations separately or compare against a fresh export |
| Different scope/redaction policy error | Choose a fresh destination, keeping the previous vault intact |
| No transcript styling appears | Refresh and enable the `session2md` CSS snippet in Obsidian Appearance settings |
| SQLite import fails | Check permissions and the reported schema error; upstream format changes may require reader updates |

When copying a live T3 database, use SQLite's backup function, or stop T3 and copy its userdata directory. Copying only the main `.sqlite` file while the app is running can omit messages still in the WAL. Never edit the original database to make an export work.

## Performance and storage

session2md streams JSONL one line at a time, reads T3 projections rather than replaying its event log, omits large inline binary payloads, and skips unchanged writes. It keeps normalized selected conversations in memory to merge copies and build consistent indexes. This is not a constant-memory importer. Optional ChatGPT JSON chunks must fit in memory.

Folder filtering currently reads source transcripts to inspect metadata before discarding unrelated sessions. It limits what is retained for export and written to the vault; it does not guarantee that unrelated histories are never opened. For a narrower input scan, point at specific transcript files or source subdirectories as well as setting the project filter.

The browser service binds only to `127.0.0.1`, validates Host/Origin, and requires a per-launch token on export requests. It loads no external scripts or fonts. Generated Markdown is ordinary local text, with atomic file replacement to avoid half-written notes. Export writes are not a transaction for the entire vault; keep backups of annotations and rerun an interrupted export with the same policy.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q session2md
node --check session2md/static/app.js
```

The tests use temporary fictional data. They cover Claude/Codex/T3 readers, conversation branches, archived sessions, duplicate event records, recursive/exact folder selection, missing metadata, external T3 worktrees, path boundaries, redaction rules and custom literals, sensitive values across emitted files and filenames, source immutability, policy changes, no-write previews, edit preservation, stable links, CLI behavior, and the local HTTP interface.

Implementation map:

| File | Responsibility |
| --- | --- |
| `session2md/readers.py` | Source-specific parsing into conversations and messages |
| `session2md/scope.py` | Path normalization and folder matching |
| `session2md/privacy.py` | Redaction rules, literal replacements, and category counts |
| `session2md/exporter.py` | Scope enforcement, policy checks, redaction, notes/indexes, manifest, and report |
| `session2md/server.py` | Local HTTP interface and request validation |
| `session2md/__main__.py` | CLI arguments and output |
| `session2md/static/` | Browser interface and optional Obsidian CSS |

The readers target observed local formats. Future application versions may change their storage schemas. New redaction rules should increment `privacy.VERSION` so a changed policy cannot silently reuse an older vault.

## License

[MIT](LICENSE).
