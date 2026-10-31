"""Read local exports without modifying the source files."""
from __future__ import annotations
import json
import os
import sqlite3
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


@dataclass
class Message:
    role: str
    text: str
    time: str = ''
    branch: str = ''
    model: str = ''


@dataclass
class Chat:
    source: str
    id: str
    title: str
    messages: list[Message]
    created: str = ''
    updated: str = ''
    project: str = ''
    origin: str = ''
    parent: str = ''
    workspace: str = ''
    project_root: str = ''


def timestamp(value) -> str:
    if not value:
        return ''
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, timezone.utc).isoformat().replace('+00:00', 'Z')
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    except (ValueError, OverflowError, OSError):
        return ''


def fence(value, language='json'):
    import re
    size = max([len(x) for x in re.findall(r'`+', value)] + [2]) + 1
    mark = '`' * size
    return f'{mark}{language}\n{value}\n{mark}'


def content(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return '\n\n'.join(filter(None, (content(x) for x in value)))
    if not isinstance(value, dict):
        return ''
    kind = value.get('type', value.get('content_type', ''))
    if kind == 'input_image' and str(value.get('image_url', '')).startswith('data:'):
        return '*Embedded image. Binary data remains in the source transcript.*'
    if kind in ('image', 'document', 'input_image') and isinstance(value.get('source'), dict) and value['source'].get('type') == 'base64':
        media = value['source'].get('media_type', kind)
        return f'*Embedded attachment: {media}. Binary data remains in the source transcript.*'
    if kind == 'redacted_thinking':
        return ''
    if kind == 'thinking':
        return '<details><summary>Reasoning</summary>\n\n' + value.get('thinking', '') + '\n\n</details>'
    if kind in ('tool_use', 'tool_call'):
        return '**Tool: ' + str(value.get('name', 'unknown')) + '**\n\n' + fence(json.dumps(value.get('input', value), ensure_ascii=False, indent=2))
    if kind == 'tool_result':
        return '**Tool result**\n\n' + content(value.get('content', ''))
    if 'parts' in value:
        return content(value['parts'])
    if isinstance(value.get('text'), str):
        return value['text']
    if 'content' in value:
        return content(value['content'])
    # Keep a reference for media, rather than silently dropping the message.
    return '*Non-text content*\n\n' + fence(json.dumps(value, ensure_ascii=False, indent=2))


def chatgpt_conversations(data, origin) -> Iterator[Chat]:
    if isinstance(data, dict):
        data = data.get('conversations', [data])
    if not isinstance(data, list):
        raise ValueError('Expected a ChatGPT conversations array')
    for chat in data:
        mapping = chat.get('mapping')
        if not isinstance(mapping, dict):
            raise ValueError('ChatGPT export is missing the conversation mapping')
        current = chat.get('current_node')
        chain, seen = [], set()
        while current in mapping and current not in seen:
            seen.add(current)
            chain.append(current)
            current = mapping[current].get('parent')
        chain.reverse()
        others = [k for k in mapping if k not in seen]
        others.sort(key=lambda k: (timestamp((mapping[k].get('message') or {}).get('create_time')), k))
        messages = []
        for key in chain + others:
            node = mapping[key]
            msg = node.get('message')
            if not msg:
                continue
            text = content(msg.get('content', ''))
            if not text:
                continue
            branch = '' if key in seen else f"{key}; parent: {node.get('parent') or 'root'}"
            messages.append(Message(msg.get('author', {}).get('role', 'unknown'), text,
                                    timestamp(msg.get('create_time')), branch,
                                    (msg.get('metadata') or {}).get('model_slug', '')))
        cid = chat.get('id') or chat.get('conversation_id')
        if not cid:
            raise ValueError('ChatGPT conversation has no stable ID')
        yield Chat('chatgpt', str(cid), chat.get('title') or 'Untitled chat', messages,
                   timestamp(chat.get('create_time')), timestamp(chat.get('update_time')), origin=origin)


def read_chatgpt(path: Path, warnings: list[str]) -> Iterator[Chat]:
    if path.is_dir():
        files = sorted(set(path.rglob('conversations*.json')))
        if not files:
            raise ValueError('No conversations*.json files found')
        for file in files:
            yield from read_chatgpt(file, warnings)
    elif zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            names = sorted(n for n in archive.namelist() if Path(n).name.startswith('conversations') and n.endswith('.json'))
            if not names:
                raise ValueError('ZIP contains no conversations*.json files')
            for name in names:
                with archive.open(name) as stream:
                    yield from chatgpt_conversations(json.load(stream), str(path))
    else:
        with path.open(encoding='utf-8-sig') as stream:
            yield from chatgpt_conversations(json.load(stream), str(path))


def read_claude(path: Path, warnings: list[str]) -> Iterator[Chat]:
    files = sorted(path.rglob('*.jsonl')) if path.is_dir() else [path]
    for file in files:
        sessions = {}
        seen = set()
        with file.open(encoding='utf-8') as stream:
            for number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    warnings.append(f'{file.name}:{number}: invalid JSON line skipped')
                    continue
                if not isinstance(row, dict):
                    warnings.append(f'{file.name}:{number}: non-object record skipped')
                    continue
                sid = str(row.get('sessionId') or file.stem)
                # Subagents have their own file even when sessionId matches their parent.
                if 'subagents' in file.parts:
                    sid += ':' + file.stem
                chat = sessions.setdefault(sid, Chat('claude', sid, '', [], project=row.get('cwd', ''), origin=str(file)))
                if row.get('type') in ('summary', 'custom-title'):
                    chat.title = row.get('customTitle') or row.get('summary') or chat.title
                msg = row.get('message')
                if not isinstance(msg, dict):
                    continue
                role = msg.get('role', row.get('type', 'unknown'))
                if role not in ('user', 'assistant', 'system', 'tool'):
                    continue
                text = content(msg.get('content', ''))
                if not text:
                    continue
                # Claude may append updates to the same message; retain each distinct block once.
                identity = (row.get('uuid') or msg.get('id'), role, text)
                if identity[0] and identity in seen:
                    continue
                seen.add(identity)
                time = timestamp(row.get('timestamp'))
                chat.messages.append(Message(role, text, time, model=msg.get('model', '')))
                chat.created = min(filter(None, [chat.created, time]), default='')
                chat.updated = max(chat.updated, time)
                chat.project = chat.project or row.get('cwd', '')
        for chat in sessions.values():
            if not chat.messages:
                continue
            chat.title = chat.title or next((m.text.split('\n')[0] for m in chat.messages if m.role == 'user'), 'Claude session')
            chat.workspace = chat.project
            yield chat


def read_t3(path: Path, warnings: list[str]) -> Iterator[Chat]:
    if path.is_dir():
        files = [path / n for n in ('state.sqlite', 'statev2.sqlite') if (path / n).exists()]
        if not files:
            raise ValueError('No state.sqlite or statev2.sqlite in this folder')
        # V2 supersedes migrated V1 IDs when the exporter merges the streams.
        for file in files:
            yield from read_t3(file, warnings)
        return
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute('BEGIN')  # consistent read snapshot, including WAL, with no source writes
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        projects = {}
        project_roots = {}
        if 'projection_projects' in tables:
            for project in db.execute('SELECT * FROM projection_projects'):
                projects[project['project_id']] = project['title']
                if 'workspace_root' in project.keys():
                    project_roots[project['project_id']] = project['workspace_root']
        variants = [('projection_threads', 'projection_thread_messages', False),
                    ('orchestration_v2_projection_threads', 'orchestration_v2_projection_messages', True)]
        supported = False
        for threads, messages, v2 in variants:
            if not {threads, messages} <= tables:
                continue
            supported = True
            for r in db.execute(f'SELECT * FROM {threads} ORDER BY created_at, thread_id'):
                if r['deleted_at']:
                    continue
                payload = json.loads(r['payload_json']) if v2 else dict(r)
                result = []
                for m in db.execute(f'SELECT * FROM {messages} WHERE thread_id=? ORDER BY created_at, message_id', (r['thread_id'],)):
                    p = json.loads(m['payload_json']) if v2 else dict(m)
                    text = p.get('text', '')
                    attachments = p.get('attachments') if v2 else json.loads(p.get('attachments_json') or '[]')
                    if attachments:
                        text += '\n\n**Attachment references**\n\n' + fence(json.dumps(attachments, ensure_ascii=False, indent=2))
                    if text:
                        result.append(Message(m['role'], text, timestamp(m['created_at'])))
                if result:
                    yield Chat('t3', r['thread_id'], r['title'], result, timestamp(r['created_at']), timestamp(r['updated_at']),
                               projects.get(r['project_id'], r['project_id']), str(path),
                               (payload.get('lineage') or {}).get('parentThreadId') or '',
                               workspace=payload.get('worktreePath') or payload.get('worktree_path') or project_roots.get(r['project_id'], ''),
                               project_root=project_roots.get(r['project_id'], ''))
        if not supported:
            raise ValueError('Unsupported T3 database schema: no recognized thread/message tables')
    finally:
        db.close()


def read_codex(path: Path, warnings: list[str]) -> Iterator[Chat]:
    """Read Codex rollout JSONL; response items take precedence over event mirrors."""
    if path.is_dir():
        roots = [path / name for name in ('sessions', 'archived_sessions') if (path / name).is_dir()]
        files = sorted({file for root in (roots or [path]) for file in root.rglob('*.jsonl')})
    else:
        files = [path]
    for file in files:
        chat = Chat('codex', file.stem, '', [], origin=str(file))
        canonical, events = [], []
        model = ''
        seen_ids = set()
        try:
            with file.open(encoding='utf-8') as stream:
                for number, line in enumerate(stream, 1):
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        warnings.append(f'{file.name}:{number}: invalid JSON line skipped')
                        continue
                    if not isinstance(row, dict) or not isinstance(row.get('payload'), dict):
                        continue
                    payload = row['payload']
                    record = row.get('type')
                    kind = payload.get('type')
                    time = timestamp(row.get('timestamp'))
                    if record == 'session_meta':
                        chat.id = str(payload.get('id') or payload.get('session_id') or chat.id)
                        chat.project = payload.get('cwd', '')
                        chat.workspace = chat.project
                        chat.created = timestamp(payload.get('timestamp')) or time
                        chat.parent = payload.get('forked_from_id') or ''
                    elif record == 'turn_context':
                        model = payload.get('model') or model
                    elif record == 'event_msg' and kind in ('user_message', 'agent_message'):
                        text = payload.get('message', '')
                        if isinstance(text, str) and text:
                            events.append(Message('user' if kind == 'user_message' else 'assistant', text, time, model=model))
                    elif record == 'response_item':
                        role, text = '', ''
                        if kind == 'message':
                            role = payload.get('role', 'unknown')
                            text = content(payload.get('content', []))
                        elif kind in ('function_call', 'custom_tool_call'):
                            role = 'assistant'
                            value = payload.get('arguments', payload.get('input', ''))
                            text = '**Tool: ' + str(payload.get('name', 'unknown')) + '**\n\n' + fence(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False), '')
                        elif kind in ('function_call_output', 'custom_tool_call_output'):
                            role = 'tool'
                            value = payload.get('output', '')
                            text = '**Tool result**\n\n' + fence(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False), '')
                        elif kind == 'reasoning':
                            role = 'assistant'
                            summary = content(payload.get('summary', []))
                            if summary:
                                text = '<details><summary>Reasoning</summary>\n\n' + summary + '\n\n</details>'
                        identity = (kind, payload.get('id') or payload.get('call_id'))
                        if identity[1] and identity in seen_ids:
                            continue
                        if text:
                            if identity[1]:
                                seen_ids.add(identity)
                            canonical.append((Message(role, text, time, model=model), kind))
        except OSError as exc:
            warnings.append(f'{file.name}: cannot read transcript: {exc}')
            continue
        roles = {m.role for m, kind in canonical if kind == 'message'}
        chat.messages = [m for m, _ in canonical] + [m for m in events if m.role not in roles]
        chat.messages.sort(key=lambda m: m.time)
        if not chat.messages:
            continue
        user_texts = [m.text.split('\n')[0] for m in chat.messages if m.role == 'user']
        chat.title = next((t for t in user_texts if not t.startswith('<')), next(iter(user_texts), 'Codex session'))
        times = [m.time for m in chat.messages if m.time]
        chat.created = chat.created or min(times, default='')
        chat.updated = max(times, default=chat.created)
        yield chat


READERS = {'claude': read_claude, 't3': read_t3, 'chatgpt': read_chatgpt, 'codex': read_codex}


def discover():
    home = Path.home()
    codex_home = Path(os.environ.get('CODEX_HOME') or home / '.codex').expanduser()
    return {
        'claude': str(home / '.claude/projects') if (home / '.claude/projects').exists() else '',
        't3': str(home / '.t3/userdata') if (home / '.t3/userdata').exists() else '',
        'codex': str(codex_home) if any((codex_home / n).is_dir() for n in ('sessions', 'archived_sessions')) else '',
    }
