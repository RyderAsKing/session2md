"""Exercise the shipped HTTP interface using only temporary sample data."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class LocalInterface(unittest.TestCase):
    def test_local_ui_and_export_requests(self):
        process = subprocess.Popen([sys.executable, '-m', 'session2md', 'serve', '--port', '0', '--no-browser'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        def stop():
            process.terminate()
            process.communicate(timeout=10)
        self.addCleanup(stop)
        line = process.stdout.readline()
        self.assertIn('http://127.0.0.1:', line)
        base = line.strip().split()[-1]
        with urlopen(base, timeout=5) as response:
            self.assertIn('Good conversations.', response.read().decode())
            self.assertIn("frame-ancestors 'none'", response.headers['Content-Security-Policy'])
        with urlopen(base + '/api/config', timeout=5) as response:
            token = json.load(response)['token']
        with self.assertRaises(HTTPError) as denied:
            urlopen(Request(base + '/api/config', headers={'Origin': 'https://unrelated.example'}), timeout=5)
        self.assertEqual(denied.exception.code, 403)
        with tempfile.TemporaryDirectory() as output:
            body = json.dumps({'output': output, 'sources': {}, 'demo': True}).encode()
            with self.assertRaises(HTTPError) as denied:
                urlopen(Request(base + '/api/export', data=body), timeout=5)
            self.assertEqual(denied.exception.code, 403)
            request = Request(base + '/api/export', data=body, headers={'Content-Type': 'application/json', 'X-Session2md-Token': token, 'Origin': base})
            with urlopen(request, timeout=5) as response:
                result = json.load(response)
            self.assertEqual(result['imported'], 3)
            self.assertEqual(result['warnings'], [])
            with urlopen(request, timeout=5) as response:
                self.assertEqual(json.load(response)['written'], 0)

            # Exercise folder selection and no-write previews through the actual HTTP API.
            source = Path(output) / 'rollout.jsonl'
            rows = [
                {'type': 'session_meta', 'payload': {'id': 'scope-test', 'cwd': '/project/one'}},
                {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'password="fake-http-sensitive-value"'}]}},
            ]
            source.write_text('\n'.join(json.dumps(row) for row in rows))
            destination = Path(output) / 'scoped-vault'
            payload = {'sources': {'codex': str(source)}, 'output': str(destination)}
            headers = {'Content-Type': 'application/json', 'X-Session2md-Token': token, 'Origin': base}
            with self.assertRaises(HTTPError) as denied:
                urlopen(Request(base + '/api/export', data=json.dumps(payload).encode(), headers=headers), timeout=5)
            self.assertEqual(denied.exception.code, 400)
            payload.update(folder='/project/one', dry_run=True)
            with urlopen(Request(base + '/api/export', data=json.dumps(payload).encode(), headers=headers), timeout=5) as response:
                result = json.load(response)
            self.assertEqual(result['imported'], 1)
            self.assertGreater(result['redactions']['SECRET_VALUE'], 0)
            self.assertFalse(destination.exists())
            payload['dry_run'] = False
            with urlopen(Request(base + '/api/export', data=json.dumps(payload).encode(), headers=headers), timeout=5) as response:
                result = json.load(response)
            self.assertEqual(result['imported'], 1)
            for note in destination.rglob('*.md'):
                self.assertNotIn('fake-http-sensitive-value', note.read_text())
