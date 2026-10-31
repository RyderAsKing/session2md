# session2md

Export local Claude Code, Codex, and T3 Code sessions to an Obsidian vault. Select a project folder, redact common sensitive content, and browse chats through linked source, project, and monthly indexes.

Runs locally with Python 3.11+. No runtime dependencies, accounts, or API keys.

## Start

```bash
git clone https://github.com/RyderAsKing/session2md.git
cd session2md
python3 -m session2md
```

The interface opens at `http://127.0.0.1:8765`. Choose your history sources, project folder, and destination, then preview or export. Open the destination as a vault in Obsidian. On Windows, use `py -3` instead of `python3`.

For a CLI export:

```bash
python3 -m session2md export --auto \
  --folder ~/projects/my-app \
  --output ~/Obsidian/my-app-chats
```

Add `--dry-run` to preview without writing files. Exporting all chats requires an explicit `--all` instead of `--folder`.

Redaction is always on, but can miss sensitive content. Review before sharing. Changed folder/redaction policies and vaults created under the previous tool name require a fresh destination.

## Guides

- [Setup](docs/setup.md): installation, interface, ports, and sample vault.
- [Exporting](docs/exporting.md): folder matching, worktrees, repeat exports, and edited notes.
- [Privacy](docs/privacy.md): detection rules, custom redactions, reports, and limits.
- [Obsidian](docs/obsidian.md): styling, Graph view, and vault layout.
- [CLI and sources](docs/reference.md): flags, JSON results, exit codes, and supported formats.
- [Troubleshooting](docs/troubleshooting.md): missing chats, conflicts, and import failures.
- [Development](docs/development.md): environment setup, checks, and code layout.
- [Agent instructions](AGENTS.md): setup and configuration workflow for coding agents.

[Sample vault](examples/session2md/session2md%20home.md) · [MIT license](LICENSE)
