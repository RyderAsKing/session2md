# Troubleshooting

[Back to README](../README.md)

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
