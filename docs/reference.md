# CLI and source reference

[Back to README](../README.md)

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
