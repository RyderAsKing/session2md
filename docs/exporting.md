# Exporting project chats

[Back to README](../README.md)

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
