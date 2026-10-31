import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from session2md.readers import read_codex, discover
from session2md.exporter import export_vault as _export_vault, digest, MANIFEST


def export_vault(*args, **kwargs):
    kwargs.setdefault("all_chats", True)
    return _export_vault(*args, **kwargs)


class CodexImport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)

    def write(self, name, rows):
        path = self.home / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(json.dumps({'timestamp': '2026-10-31T10:00:00Z', 'type': kind, 'payload': payload}) for kind, payload in rows) + '\n', encoding='utf-8')
        return path

    def test_rollout_with_mirrors_tools_reasoning_and_media(self):
        path = self.write('sessions/2026/10/rollout.jsonl', [
            ('session_meta', {'id': 'stable-session', 'cwd': '/work/app'}),
            ('turn_context', {'model': 'test-model'}),
            ('event_msg', {'type': 'user_message', 'message': 'Build a reader'}),
            ('response_item', {'id': 'u', 'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'Build a reader'}]}),
            ('response_item', {'type': 'reasoning', 'summary': [{'type': 'summary_text', 'text': 'Recorded summary'}], 'encrypted_content': 'do-not-export'}),
            ('response_item', {'type': 'function_call', 'call_id': 'call', 'name': 'shell', 'arguments': '{"cmd":"ls"}'}),
            ('response_item', {'type': 'function_call_output', 'call_id': 'call', 'output': 'file.txt'}),
            ('response_item', {'id': 'a', 'type': 'message', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': 'Done'}]}),
            ('event_msg', {'type': 'agent_message', 'message': 'Done'}),
        ])
        before = path.read_bytes()
        result = export_vault({'codex': str(self.home)}, self.home / 'vault')
        self.assertEqual(result['imported'], 1)
        self.assertEqual(result['warnings'], [])
        manifest = json.loads((self.home / 'vault' / MANIFEST).read_text())
        record = manifest['chats']['codex:' + digest('stable-session')]
        note = (self.home / 'vault' / record['path']).read_text()
        self.assertEqual(sum(m.text == 'Build a reader' for m in list(read_codex(path, []))[0].messages), 1)
        self.assertEqual(note.count('\n\nDone'), 1)
        self.assertIn('file.txt', note)
        self.assertIn('test-model', note)
        self.assertNotIn('Recorded summary', note)
        self.assertNotIn('do-not-export', note)
        export_vault({'codex': str(path)}, self.home / 'with-reasoning', reasoning=True)
        note = next((self.home / 'with-reasoning/Chats').rglob('*.md')).read_text()
        self.assertIn('Recorded summary', note)
        self.assertEqual(path.read_bytes(), before)

    def test_archived_event_only_and_corrupt_line(self):
        path = self.write('archived_sessions/old.jsonl', [
            ('session_meta', {'session_id': 'archived', 'cwd': '/work/old'}),
            ('event_msg', {'type': 'user_message', 'message': 'Older prompt'}),
            ('event_msg', {'type': 'agent_message', 'message': 'Older response'}),
        ])
        with path.open('a') as stream:
            stream.write('{incomplete')
        warnings = []
        chats = list(read_codex(self.home, warnings))
        self.assertEqual(chats[0].id, 'archived')
        self.assertEqual([m.text for m in chats[0].messages], ['Older prompt', 'Older response'])
        self.assertEqual(len(warnings), 1)

    def test_discovery_respects_custom_codex_home(self):
        (self.home / 'sessions').mkdir()
        with patch.dict(os.environ, {'CODEX_HOME': str(self.home)}):
            self.assertEqual(discover()['codex'], str(self.home))

    def test_duplicate_message_ids_and_repeated_user_text(self):
        row = {'id': 'u', 'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'Again'}]}
        path = self.write('rollout.jsonl', [('session_meta', {'id': 's'}), ('response_item', row), ('response_item', row), ('response_item', dict(row, id='u2'))])
        self.assertEqual(len(list(read_codex(path, []))[0].messages), 2)
