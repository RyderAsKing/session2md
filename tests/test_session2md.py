import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from session2md.exporter import export_vault as _export_vault, digest, MANIFEST, render
from session2md.readers import read_chatgpt, read_claude, read_t3, Chat, Message


def export_vault(*args, **kwargs):
    kwargs.setdefault("all_chats", True)
    return _export_vault(*args, **kwargs)


def conversation(cid='one', title='Same title'):
    def node(mid, text, parent, role='assistant'):
        return {'parent': parent, 'message': {'id': mid, 'author': {'role': role}, 'create_time': 1730000000, 'content': {'parts': [text]}}}
    return {'id': cid, 'title': title, 'create_time': 1730000000, 'update_time': 1730000030, 'current_node': 'a',
            'mapping': {'root': {'parent': None, 'message': None}, 'u': node('u', 'Hello', 'root', 'user'), 'a': node('a', 'Selected answer', 'u'), 'b': node('b', 'Other answer', 'u')}}


class Exports(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.output = self.base / 'vault'

    def json(self, data, name='conversations.json'):
        path = self.base / name
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def test_chatgpt_zip_chunks_and_branches(self):
        path = self.base / 'export.zip'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('nested/conversations-000.json', json.dumps([conversation()]))
            z.writestr('nested/conversations-001.json', json.dumps([conversation('two')]))
            z.writestr('../../escape.txt', 'must not extract')
        chats = list(read_chatgpt(path, []))
        self.assertEqual(len(chats), 2)
        self.assertEqual([m.text for m in chats[0].messages], ['Hello', 'Selected answer', 'Other answer'])
        self.assertTrue(chats[0].messages[-1].branch)
        self.assertFalse((self.base / 'escape.txt').exists())

    def test_chatgpt_cycle_does_not_loop(self):
        data = conversation()
        data['mapping']['u']['parent'] = 'a'
        chats = list(read_chatgpt(self.json([data]), []))
        self.assertEqual(len(chats[0].messages), 3)

    def test_claude_streaming_blocks_corruption_subagents(self):
        root = self.base / 'projects'
        root.mkdir()
        rows = [
            {'type': 'user', 'uuid': 'u', 'sessionId': 's', 'cwd': '/work/demo', 'timestamp': '2026-10-01T10:00:00Z', 'message': {'role': 'user', 'content': 'Write code'}},
            {'type': 'assistant', 'uuid': 'a', 'sessionId': 's', 'message': {'role': 'assistant', 'content': [{'type': 'text', 'text': 'Here is code'}, {'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'echo hello'}}, {'type': 'thinking', 'thinking': 'private thought'}]}},
            {'type': 'custom-title', 'sessionId': 's', 'customTitle': 'Custom title'},
        ]
        (root / 's.jsonl').write_text('\n'.join(json.dumps(r) for r in rows + [rows[1]]) + '\nbroken\n')
        sub = root / 's/subagents'
        sub.mkdir(parents=True)
        (sub / 'agent-a.jsonl').write_text(json.dumps(rows[0]))
        warnings = []
        chats = list(read_claude(root, warnings))
        self.assertEqual(len(chats), 2)
        parent = next(c for c in chats if c.id == 's')
        self.assertEqual(parent.title, 'Custom title')
        self.assertEqual(len(parent.messages), 2)
        self.assertIn('echo hello', render(parent))
        self.assertNotIn('private thought', render(parent))
        self.assertIn('private thought', render(parent, reasoning=True))
        self.assertEqual(len(warnings), 1)

    def make_t3(self, name, v2=False, extra=False):
        path = self.base / name
        c = sqlite3.connect(path)
        c.execute('CREATE TABLE projection_projects(project_id TEXT, title TEXT)')
        c.execute("INSERT INTO projection_projects VALUES ('p', 'Example project')")
        prefix = 'orchestration_v2_projection_' if v2 else 'projection_'
        messages = prefix + ('messages' if v2 else 'thread_messages')
        c.execute(f'CREATE TABLE {prefix}threads(thread_id TEXT, project_id TEXT, title TEXT, created_at TEXT, updated_at TEXT, deleted_at TEXT, payload_json TEXT)')
        c.execute(f'INSERT INTO {prefix}threads VALUES (?,?,?,?,?,?,?)', ('s', 'p', 'Test thread', '2026-10-01T10:00:00Z', '2026-10-02T10:00:00Z', None, '{}'))
        c.execute(f'CREATE TABLE {messages}(message_id TEXT, thread_id TEXT, role TEXT, text TEXT, created_at TEXT, payload_json TEXT)')
        text = 'New answer' if extra else 'Hello'
        time = '2026-10-02T10:00:00Z' if extra else '2026-10-01T10:00:00Z'
        c.execute(f'INSERT INTO {messages} VALUES (?,?,?,?,?,?)', ('m', 's', 'user', text, time, json.dumps({'text': text, 'attachments': [{'name': 'pic.png'}]})))
        c.commit()
        c.close()
        return path

    def test_t3_v1_and_v2_preserve_both_histories(self):
        self.make_t3('state.sqlite')
        self.make_t3('statev2.sqlite', True, True)
        stats = export_vault({'t3': str(self.base)}, self.output)
        self.assertEqual(stats['imported'], 1)
        manifest = json.loads((self.output / MANIFEST).read_text())
        note = (self.output / manifest['chats']['t3:' + digest('s')]['path']).read_text()
        self.assertIn('Hello', note)
        self.assertIn('New answer', note)
        self.assertIn('pic.png', note)
        self.assertIn('Example project', note)

    def test_t3_source_unchanged(self):
        path = self.make_t3('state.sqlite')
        before = path.read_bytes()
        list(read_t3(path, []))
        self.assertEqual(path.read_bytes(), before)

    def test_repeat_exports_collision_edits_and_incremental_index(self):
        path = self.json([conversation(), conversation('two')])
        first = export_vault({'chatgpt': str(path)}, self.output)
        notes = list((self.output / 'Chats').rglob('*.md'))
        self.assertEqual(len(notes), 2)
        second = export_vault({'chatgpt': str(path)}, self.output)
        self.assertEqual(second['written'], 0)
        notes[0].write_text('My own edit\n')
        third = export_vault({'chatgpt': str(path)}, self.output)
        self.assertEqual(third['conflicts'], 1)
        self.assertEqual(notes[0].read_text(), 'My own edit\n')
        export_vault({}, self.output, demo=True)
        home = (self.output / 'session2md home.md').read_text()
        self.assertIn('5 conversations', home)
        self.assertGreater(first['written'], 0)

    def test_title_change_reuses_path_and_no_rewrites(self):
        path = self.json([conversation(title='../../Bad [title] | a/b')])
        export_vault({'chatgpt': str(path)}, self.output)
        manifest = json.loads((self.output / MANIFEST).read_text())
        old = manifest['chats']['chatgpt:' + digest('one')]['path']
        self.json([conversation(title='Renamed')])
        export_vault({'chatgpt': str(path)}, self.output)
        new = json.loads((self.output / MANIFEST).read_text())
        self.assertEqual(old, new['chats']['chatgpt:' + digest('one')]['path'])
        self.assertIn('Renamed', (self.output / old).read_text())

    def test_existing_files_are_never_taken_over(self):
        self.output.mkdir()
        home = self.output / 'session2md home.md'
        home.write_text('My homepage')
        stats = export_vault({}, self.output, demo=True)
        self.assertEqual(home.read_text(), 'My homepage')
        self.assertEqual(stats['conflicts'], 1)

    def test_unsafe_manifest_paths_rejected(self):
        export_vault({}, self.output, demo=True)
        path = self.output / MANIFEST
        manifest = json.loads(path.read_text())
        manifest['chats']['claude:' + digest('demo-claude')]['path'] = '../outside.md'
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'outside vault'):
            export_vault({}, self.output, demo=True)
        self.assertFalse((self.base / 'outside.md').exists())

    def test_partial_failure_reports_warning_and_exports_valid_source(self):
        path = self.json([conversation()])
        stats = export_vault({'claude': '/missing/source', 'chatgpt': str(path)}, self.output)
        self.assertEqual(stats['imported'], 1)
        self.assertTrue(stats['warnings'])

    def test_wiki_links_have_targets_and_table_alias_escaping(self):
        import re
        export_vault({}, self.output, demo=True)
        for note in self.output.rglob('*.md'):
            for target in re.findall(r'\[\[([^\]|]+)', note.read_text()):
                target = target.rstrip('\\')
                self.assertTrue((self.output / (target + '.md')).exists(), (note, target))
        source = (self.output / 'Indexes/Sources/Claude Code.md').read_text()
        self.assertIn('\\|Building', source)

    def test_cli_demo_end_to_end(self):
        result = subprocess.run([sys.executable, '-m', 'session2md', 'export', '--demo', '-o', str(self.output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['imported'], 3)
        self.assertTrue((self.output / '.obsidian/snippets/session2md.css').exists())


if __name__ == '__main__':
    unittest.main()

class Media(unittest.TestCase):
    def test_inline_media_not_expanded_into_markdown(self):
        from session2md.readers import content
        text = content({'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png', 'data': 'x' * 100000}})
        self.assertLess(len(text), 200)
        self.assertIn('image/png', text)
