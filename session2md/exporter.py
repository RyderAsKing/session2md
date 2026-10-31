"""Deterministic Obsidian notes with an edit-aware manifest."""
from __future__ import annotations
import hashlib
import json
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path
from .readers import Chat, READERS
from .privacy import Redactor, VERSION as PRIVACY_VERSION
from .scope import matches_folder, normalize_folder

LABELS = {'claude': 'Claude Code', 't3': 'T3 Code', 'chatgpt': 'ChatGPT', 'codex': 'Codex'}
MANIFEST = '.session2md-manifest.json'


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def slug(text, limit=75):
    value = re.sub(r'[\x00-\x1f<>:"/\\|?*\[\]#^]', ' ', str(text))
    value = re.sub(r'\s+', ' ', value).strip(' .')[:limit].rstrip(' .')
    return value or 'Untitled'


def label(text):
    return str(text).replace('\n', ' ').replace('\r', ' ').replace('|', ' ').replace(']', '').replace('[', '')


def link(path, title=None):
    return '[[' + str(path).removesuffix('.md') + ('|' + label(title) if title else '') + ']]'


def hub(kind, name):
    return f'Indexes/{kind}/{slug(name)}--{digest(name)[:12]}.md'


def atomic_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.session2md-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def safe_target(root, relative):
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or target == root:
        raise ValueError(f'Path outside vault: {relative}')
    return target


def render(chat: Chat, reasoning=False):
    source = LABELS[chat.source]
    meta = {
        'title': chat.title, 'source': source, 'session_id': chat.id,
        'created': chat.created, 'updated': chat.updated, 'project': chat.project, 'workspace': chat.workspace, 'project_root': chat.project_root,
        'message_count': len(chat.messages), 'cssclasses': ['session2md-chat'],
        'tags': ['chats', f'chats/{chat.source}'],
        'models': sorted({m.model for m in chat.messages if m.model}),
    }
    front = '---\n' + '\n'.join(k + ': ' + json.dumps(v, ensure_ascii=False) for k, v in meta.items()) + '\n---\n\n'
    nav = [link('session2md home.md', 'Home'), link(f'Indexes/Sources/{source}.md', source)]
    if chat.project:
        nav.append(link(hub('Projects', chat.project), chat.project))
    if chat.created:
        nav.append(link(f'Indexes/Months/{chat.created[:7]}.md', chat.created[:7]))
    parts = [front + '# ' + label(chat.title), ' · '.join(nav), '> [!abstract] Session\n> ' + str(len(chat.messages)) + ' recorded messages. ' + (chat.created[:10] or 'Date unknown') + '.']
    alternate = False
    for index, m in enumerate(chat.messages, 1):
        text = m.text
        if not reasoning:
            text = re.sub(r'<details><summary>Reasoning</summary>.*?</details>', '', text, flags=re.S)
        if not text.strip():
            continue
        if m.branch and not alternate:
            parts.append('## Alternate branches\n\nThese messages belong to other paths through this conversation. Each shows its node and parent; they are not a single dialogue.')
            alternate = True
        name = {'user': 'You', 'assistant': source, 'tool': 'Tool', 'system': 'System'}.get(m.role, label(m.role))
        heading = f'### {index:03d} · {name}' + (f' · {m.time[11:19]} UTC' if m.time else '') + f' ^msg-{index}'
        if m.branch:
            heading += '\n\n> Branch node: ' + label(m.branch)
        parts.append(heading + '\n\n' + text.strip())
    return '\n\n'.join(parts) + '\n'


def export_vault(sources: dict, output, *, reasoning=False, style=True, demo=False,
                 folder=None, exact_folder=False, all_chats=False, literals=(), dry_run=False):
    if folder and all_chats:
        raise ValueError('Choose a project folder or all chats, not both')
    if not folder and not all_chats and not demo:
        raise ValueError('Choose a project folder with --folder, or explicitly choose --all')
    if exact_folder and not folder:
        raise ValueError('Exact folder matching requires a project folder')
    redactor = Redactor(literals)
    policy = digest(json.dumps({'folder': normalize_folder(folder) if folder else None,
                                'exact': exact_folder, 'privacy': PRIVACY_VERSION,
                                'literals': sorted(digest(v) for v in set(literals))}, sort_keys=True))
    root = Path(output).expanduser().resolve()
    if (root / '.chatvault-manifest.json').exists():
        raise ValueError('This vault uses the previous tool name. Export to a fresh output folder to keep its notes and indexes separate.')
    manifest_path = root / MANIFEST
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest.get('version') != 1:
            raise ValueError('Unsupported session2md manifest version')
    else:
        manifest = {'version': 1, 'files': {}, 'chats': {}}
    if manifest['chats'] and manifest.get('policy') != policy:
        raise ValueError('This vault has a different scope or redaction policy, or predates redaction. Use a fresh output folder; existing files have not been changed.')
    manifest['policy'] = policy
    warnings, chats = [], {}
    excluded = 0
    missing_workspace = 0
    for source, input_path in sources.items():
        if not input_path:
            continue
        if source not in READERS:
            raise ValueError(f'Unknown source: {source}')
        path = Path(input_path).expanduser()
        if not path.exists():
            warnings.append(f'{LABELS[source]}: path does not exist: {path}')
            continue
        try:
            loaded = 0
            for chat in READERS[source](path, warnings):
                if chat.messages:
                    loaded += 1
                    if folder and not any(matches_folder(path, folder, exact_folder) for path in (chat.workspace, chat.project_root)):
                        excluded += 1
                        missing_workspace += int(not chat.workspace and not chat.project_root)
                        continue
                    key = f'{source}:{digest(chat.id)}'
                    previous = chats.get(key)
                    if previous and source in ('t3', 'codex'):
                        identities = {(m.role, m.text, m.time) for m in previous.messages}
                        merged = previous.messages + [m for m in chat.messages if (m.role, m.text, m.time) not in identities]
                        chat.messages = sorted(merged, key=lambda m: m.time)
                        chat.created = min(filter(None, [previous.created, chat.created]), default='')
                        chat.updated = max(previous.updated, chat.updated)
                    chats[key] = chat
            if not loaded:
                warnings.append(f'{LABELS[source]}: no readable conversations found at {path}')
        except (ValueError, OSError, KeyError, TypeError) as exc:
            warnings.append(f'{LABELS[source]} import failed: {exc}')
        except Exception as exc:
            # SQLite/ZIP errors are reported per source; other selected sources still export.
            warnings.append(f'{LABELS[source]} import failed ({type(exc).__name__}): {exc}')
    if demo:
        from .sample import sample_chats
        chats.update({f'{c.source}:{digest(c.id)}': c for c in sample_chats() if not folder or matches_folder(c.workspace, folder, exact_folder)})
    chats = {key: redactor.chat(chat) for key, chat in chats.items()}
    warnings[:] = [redactor.clean(w) for w in warnings]
    if folder and not chats:
        warnings.append('No conversations matched the selected project folder. Nothing was exported.')
    stats = {'imported': len(chats), 'excluded': excluded, 'missing_workspace': missing_workspace, 'dry_run': dry_run, 'redactions': dict(redactor.counts), 'written': 0, 'unchanged': 0, 'conflicts': 0, 'vault': redactor.clean(str(root)), 'warnings': warnings}
    if dry_run or not chats:
        return stats
    root.mkdir(parents=True, exist_ok=True)

    def write(relative, text, *, scan=True):
        relative = redactor.clean(relative)
        if scan:
            text = redactor.clean(text)
        target = safe_target(root, relative)
        new_hash = digest(text)
        old_hash = manifest['files'].get(relative)
        if target.exists():
            existing = digest(target.read_text(encoding='utf-8'))
            if existing == new_hash:
                manifest['files'][relative] = new_hash
                stats['unchanged'] += 1
                return True
            if existing != old_hash:
                stats['conflicts'] += 1
                warnings.append(redactor.clean(f'Kept locally edited or existing file: {relative}. Export to a fresh vault to compare.'))
                return False
        atomic_write(target, text)
        manifest['files'][relative] = new_hash
        stats['written'] += 1
        return True

    for key, chat in chats.items():
        previous = manifest['chats'].get(key, {})
        relative = redactor.clean(previous.get('path') or f'Chats/{LABELS[chat.source]}/{slug(chat.title)}--{digest(key)[:16]}.md')
        if write(relative, render(chat, reasoning=reasoning)):
            manifest['chats'][key] = {'path': relative, 'title': chat.title, 'source': chat.source,
                                      'project': chat.project, 'workspace': chat.workspace, 'project_root': chat.project_root, 'created': chat.created, 'updated': chat.updated,
                                      'messages': len(chat.messages), 'parent': chat.parent}
    # Retain all previously exported sessions, even when importing one source at a time.
    records = sorted(manifest['chats'].values(), key=lambda c: (c['created'], c['path']), reverse=True)
    groups = defaultdict(list)
    for record in records:
        groups[f"Indexes/Sources/{LABELS[record['source']]}.md"].append(record)
        if record['created']:
            groups[f"Indexes/Months/{record['created'][:7]}.md"].append(record)
        if record['project']:
            groups[hub('Projects', record['project'])].append(record)
    for path, rows in sorted(groups.items()):
        title = rows[0]['project'] if path.startswith('Indexes/Projects/') else Path(path).stem
        lines = [f'# {label(title)}', link('session2md home.md', 'Home'), f'{len(rows)} conversations', '| Conversation | Date | Messages |', '| --- | --- | ---: |']
        lines.extend(f"| {link(r['path'], r['title']).replace(chr(124), chr(92) + chr(124))} | {r['created'][:10] or 'Unknown'} | {r['messages']} |" for r in rows)
        write(path, '\n\n'.join(lines[:3]) + '\n\n' + '\n'.join(lines[3:]) + '\n')
    home = ['---\ncssclasses: [session2md-home]\ntags: [session2md]\n---', '# Your conversation library',
            '> [!tip] Start here\n> Browse by source, project, or month. Open Obsidian Graph view to explore the links between your chats.',
            f'**{len(records)} conversations** · **{sum(r["messages"] for r in records):,} messages**', '## Sources']
    for source, title in LABELS.items():
        count = sum(r['source'] == source for r in records)
        if count:
            home.append(f'- {link(f"Indexes/Sources/{title}.md", title)} · {count} chats')
    for kind in ('Projects', 'Months'):
        home.append('## ' + kind)
        for path, rows in sorted(groups.items(), reverse=kind == 'Months'):
            if path.startswith(f'Indexes/{kind}/'):
                title = rows[0]['project'] if kind == 'Projects' else Path(path).stem
                home.append(f'- {link(path, title)} · {len(rows)} chats')
    home.append('## Recent conversations')
    home.extend(f"- {link(r['path'], r['title'])} · {r['created'][:10]}" for r in records[:25])
    home.append('## Privacy\n\nSensitive-content detection is on. See [[session2md privacy report]] for category counts. Review your files before sharing; detection can miss private data.\n\n## Reading and graph view\n\nEnable the **session2md** CSS snippet in Settings → Appearance → CSS snippets for the reading style. In Graph view, use `path:Chats` to focus on transcripts, or include `path:Indexes` to see source, project, and month connections. Your notes and backlinks work without community plugins.\n\nExports preserve text and media references. Binary attachments are not copied. Reasoning is omitted unless requested. Keep your own annotations in separate linked notes; edited generated files are preserved and reported as conflicts.')
    write('session2md home.md', '\n\n'.join(home) + '\n')
    if style:
        write('.obsidian/snippets/session2md.css', (Path(__file__).parent / 'static/vault.css').read_text(encoding='utf-8'))
    report = {'rules_version': PRIVACY_VERSION, 'categories': dict(redactor.counts),
              'total_replacements': sum(redactor.counts.values()),
              'note': 'Counts cover this run. No matched values or excerpts are stored. Pattern detection is incomplete; review before sharing.'}
    write('session2md privacy report.md', '# Privacy report\n\n' + '\n\n'.join([
        'Sensitive content was replaced with REDACTED markers before writing generated files.',
        '```json\n' + json.dumps(report, indent=2) + '\n```',
        'Existing user files and edited notes are preserved, not scrubbed. This report is not proof that every sensitive value was found.'
    ]) + '\n', scan=False)
    stats['redactions'] = dict(redactor.counts)
    atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return stats
