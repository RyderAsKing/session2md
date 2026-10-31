import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from session2md.exporter import export_vault, MANIFEST
from session2md.privacy import Redactor
from session2md.readers import read_t3
from session2md.scope import matches_folder


class SelectionPrivacy(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'sessions'
        self.source.mkdir()
        self.output = self.base / 'vault'

    def rollout(self, sid, cwd, text='ordinary message', title=None):
        rows = [('session_meta', {'id': sid, 'cwd': cwd}),
                ('response_item', {'type': 'message', 'id': 'u', 'role': 'user', 'content': [{'type': 'input_text', 'text': title or text}]}),
                ('response_item', {'type': 'function_call_output', 'call_id': 'out', 'output': text})]
        path = self.source / (sid + '.jsonl')
        path.write_text('\n'.join(json.dumps({'type': kind, 'timestamp': '2026-10-31T12:00:00Z', 'payload': payload}) for kind, payload in rows))
        return path

    def test_folder_default_descendants_sibling_and_unknown(self):
        self.rollout('root', '/work/app')
        self.rollout('child', '/work/app/sub')
        self.rollout('sibling', '/work/app-other')
        self.rollout('unknown', '')
        result = export_vault({'codex': str(self.source)}, self.output, folder='/work/app')
        self.assertEqual(result['imported'], 2)
        self.assertEqual(result['excluded'], 2)
        self.assertEqual(result['missing_workspace'], 1)
        self.assertEqual(len(list((self.output / 'Chats').rglob('*.md'))), 2)

    def test_cross_platform_paths_and_symlinks(self):
        self.assertTrue(matches_folder(r'C:\Work\App\sub', r'c:\work\app'))
        self.assertFalse(matches_folder(r'C:\Work\App2', r'C:\Work\App'))
        self.assertFalse(matches_folder('/work/app2', '/work/app'))
        self.assertFalse(matches_folder('relative/app', '/work/app'))
        folder = self.base / 'actual'
        folder.mkdir()
        alias = self.base / 'alias'
        alias.symlink_to(folder, target_is_directory=True)
        self.assertTrue(matches_folder(str(alias), str(folder)))

    def test_exact_folder(self):
        self.rollout('root', '/work/app')
        self.rollout('child', '/work/app/sub')
        result = export_vault({'codex': str(self.source)}, self.output, folder='/work/app', exact_folder=True)
        self.assertEqual(result['imported'], 1)
        self.assertEqual(result['excluded'], 1)

    def test_explicit_scope_required_without_creating_output(self):
        self.rollout('root', '/work/app')
        with self.assertRaisesRegex(ValueError, 'project folder'):
            export_vault({'codex': str(self.source)}, self.output)
        self.assertFalse(self.output.exists())

    def test_no_match_and_preview_write_nothing(self):
        self.rollout('root', '/work/app', text='password="fake-sensitive-value"')
        preview = export_vault({'codex': str(self.source)}, self.output, folder='/work/app', dry_run=True)
        self.assertEqual(preview['imported'], 1)
        self.assertGreater(preview['redactions']['SECRET_VALUE'], 0)
        self.assertFalse(self.output.exists())
        result = export_vault({'codex': str(self.source)}, self.output, folder='/different')
        self.assertEqual(result['imported'], 0)
        self.assertTrue(result['warnings'])
        self.assertFalse(self.output.exists())

    def test_scope_and_custom_policy_changes_fail_without_mutation(self):
        self.rollout('root', '/work/app')
        export_vault({'codex': str(self.source)}, self.output, folder='/work/app')
        before = {str(p): p.read_bytes() for p in self.output.rglob('*') if p.is_file()}
        for options in ({'folder': '/elsewhere'}, {'all_chats': True}, {'folder': '/work/app', 'literals': ['PrivateName']}):
            with self.assertRaisesRegex(ValueError, 'fresh output folder'):
                export_vault({'codex': str(self.source)}, self.output, **options)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.output.rglob('*') if p.is_file()})

    def test_previous_tool_name_requires_fresh_destination(self):
        self.output.mkdir()
        original = self.output / '.chatvault-manifest.json'
        original.write_text('{"version": 1}')
        with self.assertRaisesRegex(ValueError, 'previous tool name'):
            export_vault({}, self.output, demo=True)
        self.assertEqual(list(self.output.iterdir()), [original])
        self.assertEqual(original.read_text(), '{"version": 1}')

    def test_legacy_vault_not_treated_as_redacted(self):
        self.output.mkdir()
        (self.output / MANIFEST).write_text(json.dumps({'version': 1, 'files': {}, 'chats': {'old': {}}}))
        with self.assertRaisesRegex(ValueError, 'predates redaction'):
            export_vault({}, self.output, demo=True)

    def test_all_emitted_bytes_and_names_are_redacted(self):
        key = 'sk-proj-' + 'FAKEfixture' * 5
        email = 'fixture.person@example.test'
        literal = 'PrivateCompanyName'
        text = f'API_KEY="{key}"\ncontact {email}\npassword: "fixture password"\n{literal}'
        source = self.rollout('root', '/work/' + literal, text=text, title=email + ' ' + literal)
        before = source.read_bytes()
        result = export_vault({'codex': str(self.source)}, self.output, folder='/work/' + literal, literals=[literal])
        for file in self.output.rglob('*'):
            if file.is_file():
                emitted = file.read_text() + str(file.relative_to(self.output))
                for sensitive in (key, email, literal, 'fixture password'):
                    self.assertNotIn(sensitive, emitted, file.name)
        self.assertNotIn(literal, json.dumps(result))
        self.assertEqual(source.read_bytes(), before)
        self.assertTrue(result['redactions'])
        report = (self.output / 'session2md privacy report.md').read_text()
        report_data = json.loads(re.search(r'```json\n(.*?)\n```', report, re.S)[1])
        self.assertGreater(report_data['total_replacements'], 0)
        self.assertTrue(all(isinstance(count, int) for count in report_data['categories'].values()))
        second = export_vault({'codex': str(self.source)}, self.output, folder='/work/' + literal, literals=[literal])
        self.assertEqual(second['written'], 0)
        # Every generated wiki link still resolves after redaction.
        for note in self.output.rglob('*.md'):
            for target in re.findall(r'\[\[([^\]|]+)', note.read_text()):
                self.assertTrue((self.output / (target.rstrip('\\') + '.md')).exists(), (note, target))

    def test_claude_filter_uses_cwd_not_text_mentions(self):
        path = self.source / 'claude.jsonl'
        rows = [{'sessionId': sid, 'cwd': cwd, 'type': 'user', 'message': {'role': 'user', 'content': 'mentions /work/app'}} for sid, cwd in [('match', '/work/app'), ('exclude', '/work/other')]]
        path.write_text('\n'.join(json.dumps(r) for r in rows))
        result = export_vault({'claude': str(path)}, self.output, folder='/work/app')
        self.assertEqual(result['imported'], 1)
        self.assertEqual(result['excluded'], 1)

    def test_t3_root_and_external_worktree_v1_v2(self):
        for v2 in (False, True):
            dbpath = self.base / f't3-{v2}.sqlite'
            c = sqlite3.connect(dbpath)
            c.execute('CREATE TABLE projection_projects(project_id TEXT, title TEXT, workspace_root TEXT)')
            c.execute("INSERT INTO projection_projects VALUES ('p', 'My app', '/work/app')")
            prefix = 'orchestration_v2_projection_' if v2 else 'projection_'
            message_table = prefix + ('messages' if v2 else 'thread_messages')
            c.execute(f'CREATE TABLE {prefix}threads(thread_id TEXT, project_id TEXT, title TEXT, created_at TEXT, updated_at TEXT, deleted_at TEXT, worktree_path TEXT, payload_json TEXT)')
            payload = json.dumps({'worktreePath': '/tmp/worktree'})
            c.execute(f'INSERT INTO {prefix}threads VALUES (?,?,?,?,?,?,?,?)', ('s', 'p', 'Thread', '', '', None, '/tmp/worktree', payload))
            c.execute(f'CREATE TABLE {message_table}(message_id TEXT, thread_id TEXT, role TEXT, text TEXT, created_at TEXT, payload_json TEXT)')
            c.execute(f'INSERT INTO {message_table} VALUES (?,?,?,?,?,?)', ('m', 's', 'user', 'hello', '', '{"text":"hello"}'))
            c.commit(); c.close()
            chat = list(read_t3(dbpath, []))[0]
            self.assertEqual(chat.workspace, '/tmp/worktree')
            self.assertEqual(chat.project_root, '/work/app')
            for folder in ('/work/app', '/tmp/worktree'):
                result = export_vault({'t3': str(dbpath)}, self.base / f'vault-{v2}-{folder.split("/")[-1]}', folder=folder)
                self.assertEqual(result['imported'], 1)

    def test_cli_requires_scope_and_dry_run_leaves_no_vault(self):
        self.rollout('root', '/work/app')
        command = [sys.executable, '-m', 'session2md', 'export', '--codex', str(self.source), '-o', str(self.output)]
        denied = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(denied.returncode, 2)
        self.assertFalse(self.output.exists())
        preview = subprocess.run(command + ['--folder', '/work/app', '--dry-run'], capture_output=True, text=True)
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertEqual(json.loads(preview.stdout)['imported'], 1)
        self.assertFalse(self.output.exists())


class RedactionRules(unittest.TestCase):
    def test_credentials_personal_details_and_private_keys(self):
        cases = [
            ('sk-' + 'a' * 35, 'API_KEY'), ('ghp_' + 'b' * 36, 'API_KEY'),
            ('AKIA' + 'C' * 16, 'API_KEY'), ('xoxb-' + 'd' * 25, 'API_KEY'),
            ('eyJabc.defghi.jklmnop', 'JWT'), ('Bearer fixture-long-token', 'AUTHORIZATION'),
            ('Basic ZmFrZTpmYWtlcGFzcw==', 'AUTHORIZATION'),
            ('postgres://fixture:fakepass@localhost/db', 'URL_CREDENTIALS'),
            ('DB_PASSWORD="fake pass"', 'SECRET_VALUE'), ('{"clientSecret":"fixture-value"}', 'SECRET_VALUE'),
            ('Cookie: session=fake-session', 'SECRET_VALUE'), ('?token=fixture-query-token', 'SECRET_VALUE'),
            ('contact+tag@example.test', 'EMAIL'), ('123-45-6789', 'SSN'),
            ('4111 1111 1111 1111', 'PAYMENT_CARD'), ('+1 (415) 555-0132', 'PHONE'),
            ('-----BEGIN OPENSSH PRIVATE KEY-----\nfake-key-body\n-----END OPENSSH PRIVATE KEY-----', 'PRIVATE_KEY'),
        ]
        for original, category in cases:
            with self.subTest(category=category):
                redactor = Redactor()
                cleaned = redactor.clean(original)
                self.assertNotEqual(original, cleaned)
                self.assertIn('REDACTED-' + category, cleaned)
                self.assertEqual(cleaned, redactor.clean(cleaned))

    def test_ordinary_code_and_dates_stay_readable(self):
        text = '2026-10-31\nconst readingWidth = 65;\nSELECT * FROM articles;\ninvalid card 1234 5678 9012 3456'
        self.assertEqual(Redactor().clean(text), text)

    def test_marker_inside_secret_does_not_bypass_redaction(self):
        value = 'password="REDACTED-CUSTOM plus-still-sensitive"'
        self.assertEqual(Redactor().clean(value), 'password="REDACTED-SECRET_VALUE"')

    def test_literal_overlaps_are_stable_and_not_regex(self):
        redactor = Redactor(['private.name', 'private', 'REDACTED'])
        cleaned = redactor.clean('private.name private')
        self.assertEqual(cleaned, 'REDACTED-CUSTOM REDACTED-CUSTOM')
        self.assertEqual(redactor.clean(cleaned), cleaned)
