---
title: "A reliable sync queue"
source: "T3 Code"
session_id: "demo-t3"
created: "2026-10-29T14:00:00Z"
updated: "2026-10-29T14:01:00Z"
project: "Reading app"
workspace: ""
project_root: ""
message_count: 2
cssclasses: ["session2md-chat"]
tags: ["chats", "chats/t3"]
models: []
---

# A reliable sync queue

[[session2md home|Home]] · [[Indexes/Sources/T3 Code|T3 Code]] · [[Indexes/Projects/Reading app--883d7e4fab3e|Reading app]] · [[Indexes/Months/2026-10|2026-10]]

> [!abstract] Session
> 2 recorded messages. 2026-10-29.

### 001 · You · 14:00:00 UTC ^msg-1

What happens when an offline edit reaches the server twice?

### 002 · T3 Code · 14:01:00 UTC ^msg-2

Give each change a stable operation ID. The server stores that ID with the result and returns the same result for retries.

1. Write the edit and queue entry in one transaction.
2. Send the operation ID with the request.
3. Remove the entry after acknowledgment.
