from .readers import Chat, Message


def sample_chats():
    return [
        Chat('claude', 'demo-claude', 'Building a calmer reading experience', [
            Message('user', 'How should we structure a reading app for long articles?', '2026-10-28T09:30:00Z'),
            Message('assistant', 'Start with the reading surface. Keep the article width around 65 characters, let the reader change the font size, and save their place.\n\n```css\n.article { max-width: 65ch; line-height: 1.7; }\n```', '2026-10-28T09:31:00Z'),
            Message('user', 'Let’s keep saved articles and reading progress in separate tables.', '2026-10-28T09:33:00Z'),
        ], '2026-10-28T09:30:00Z', '2026-10-28T09:33:00Z', 'Reading app'),
        Chat('t3', 'demo-t3', 'A reliable sync queue', [
            Message('user', 'What happens when an offline edit reaches the server twice?', '2026-10-29T14:00:00Z'),
            Message('assistant', 'Give each change a stable operation ID. The server stores that ID with the result and returns the same result for retries.\n\n1. Write the edit and queue entry in one transaction.\n2. Send the operation ID with the request.\n3. Remove the entry after acknowledgment.', '2026-10-29T14:01:00Z'),
        ], '2026-10-29T14:00:00Z', '2026-10-29T14:01:00Z', 'Reading app'),
        Chat('codex', 'demo-codex', 'Notes on learning in public', [
            Message('user', 'I want a weekly writing habit that I can maintain.', '2026-10-30T17:00:00Z'),
            Message('assistant', 'Keep one running note during the week. On Friday, pick a problem you solved and explain the steps in 300 words. Include the detail you wish someone had told you.', '2026-10-30T17:01:00Z'),
        ], '2026-10-30T17:00:00Z', '2026-10-30T17:01:00Z'),
    ]
