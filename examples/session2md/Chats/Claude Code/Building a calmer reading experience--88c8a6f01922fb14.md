---
title: "Building a calmer reading experience"
source: "Claude Code"
session_id: "demo-claude"
created: "2026-10-28T09:30:00Z"
updated: "2026-10-28T09:33:00Z"
project: "Reading app"
workspace: ""
project_root: ""
message_count: 3
cssclasses: ["session2md-chat"]
tags: ["chats", "chats/claude"]
models: []
---

# Building a calmer reading experience

[[session2md home|Home]] · [[Indexes/Sources/Claude Code|Claude Code]] · [[Indexes/Projects/Reading app--883d7e4fab3e|Reading app]] · [[Indexes/Months/2026-10|2026-10]]

> [!abstract] Session
> 3 recorded messages. 2026-10-28.

### 001 · You · 09:30:00 UTC ^msg-1

How should we structure a reading app for long articles?

### 002 · Claude Code · 09:31:00 UTC ^msg-2

Start with the reading surface. Keep the article width around 65 characters, let the reader change the font size, and save their place.

```css
.article { max-width: 65ch; line-height: 1.7; }
```

### 003 · You · 09:33:00 UTC ^msg-3

Let’s keep saved articles and reading progress in separate tables.
