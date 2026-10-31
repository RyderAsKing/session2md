# Development

[Back to README](../README.md)

## Environment

From the repository root, create an isolated editable installation when working on the installed command or packaging:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
session2md --help
```

On Windows:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
session2md --help
```

Running `python3 -m session2md` directly from the checkout needs no installation. Node.js is only needed for the JavaScript syntax check below. The HTTP integration test binds to an ephemeral loopback port and uses temporary fictional history.

## Validation

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q session2md
node --check session2md/static/app.js
```

The tests use temporary fictional data. They cover Claude/Codex/T3 readers, conversation branches, archived sessions, duplicate event records, recursive/exact folder selection, missing metadata, external T3 worktrees, path boundaries, redaction rules and custom literals, sensitive values across emitted files and filenames, source immutability, policy changes, no-write previews, edit preservation, stable links, CLI behavior, and the local HTTP interface.

## Code layout

| File | Responsibility |
| --- | --- |
| [readers.py](../session2md/readers.py) | Source-specific parsing into conversations and messages |
| [scope.py](../session2md/scope.py) | Path normalization and folder matching |
| [privacy.py](../session2md/privacy.py) | Redaction rules, literal replacements, and category counts |
| [exporter.py](../session2md/exporter.py) | Scope enforcement, policy checks, redaction, notes/indexes, manifest, and report |
| [server.py](../session2md/server.py) | Local HTTP interface and request validation |
| [__main__.py](../session2md/__main__.py) | CLI arguments and output |
| [static/](../session2md/static/) | Browser interface and optional Obsidian CSS |

The readers target observed local formats. Future application versions may change their storage schemas. New redaction rules should increment `privacy.VERSION` so a changed policy cannot silently reuse an older vault.

## Performance and storage

session2md streams JSONL one line at a time, reads T3 projections rather than replaying its event log, omits large inline binary payloads, and skips unchanged writes. It keeps normalized selected conversations in memory to merge copies and build consistent indexes. This is not a constant-memory importer. Optional ChatGPT JSON chunks must fit in memory.

Folder filtering currently reads source transcripts to inspect metadata before discarding unrelated sessions. It limits what is retained for export and written to the vault; it does not guarantee that unrelated histories are never opened. For a narrower input scan, point at specific transcript files or source subdirectories as well as setting the project filter.

The browser service binds only to `127.0.0.1`, validates Host/Origin, and requires a per-launch token on export requests. It loads no external scripts or fonts. Generated Markdown is ordinary local text, with atomic file replacement to avoid half-written notes. Export writes are not a transaction for the entire vault; keep backups of annotations and rerun an interrupted export with the same policy.
