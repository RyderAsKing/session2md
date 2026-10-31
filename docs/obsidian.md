# Using Obsidian

[Back to README](../README.md)

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
