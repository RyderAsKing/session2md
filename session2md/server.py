"""Loopback-only UI. No external services or Python dependencies."""
import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from .exporter import export_vault
from .readers import discover
from .privacy import Redactor

STATIC = Path(__file__).parent / 'static'


def serve(port=8765, browser=True):
    token = secrets.token_urlsafe(32)
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, status, body, mime='application/json'):
            data = body.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', mime + '; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(data)

        def trusted(self):
            host = f'127.0.0.1:{self.server.server_port}'
            return self.headers.get('Host') == host and self.headers.get('Origin', 'http://' + host) == 'http://' + host

        def do_GET(self):
            if not self.trusted():
                return self.respond(403, '{"error":"Untrusted origin"}')
            path = urlsplit(self.path).path
            if path == '/api/config':
                return self.respond(200, json.dumps({'token': token, 'sources': discover(), 'output': str(Path.home() / 'session2md')}))
            files = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
            if path not in files:
                return self.respond(404, '{"error":"Not found"}')
            name, mime = files[path]
            self.respond(200, (STATIC / name).read_text(encoding='utf-8'), mime)

        def do_POST(self):
            if not self.trusted() or not secrets.compare_digest(self.headers.get('X-Session2md-Token', ''), token):
                return self.respond(403, '{"error":"Untrusted request"}')
            if self.path != '/api/export':
                return self.respond(404, '{"error":"Not found"}')
            if not lock.acquire(blocking=False):
                return self.respond(409, '{"error":"An export is already running"}')
            redactor = Redactor()
            try:
                size = int(self.headers.get('Content-Length', 0))
                if not 0 < size <= 65536:
                    raise ValueError('Invalid request size')
                data = json.loads(self.rfile.read(size))
                output = data.get('output', '').strip()
                if not output:
                    raise ValueError('Choose an output folder')
                sources = data.get('sources', {})
                if not isinstance(sources, dict) or any(not isinstance(v, str) for v in sources.values()):
                    raise ValueError('Source paths must be strings')
                if not any(sources.values()) and not data.get('demo'):
                    raise ValueError('Choose at least one source, or try the demo')
                folder = data.get('folder')
                if folder is not None and not isinstance(folder, str):
                    raise ValueError('Project folder must be a path string')
                literals = data.get('literals', [])
                redactor = Redactor(literals)
                for flag in ('all_chats', 'exact_folder', 'dry_run', 'demo', 'style', 'reasoning'):
                    if flag in data and not isinstance(data[flag], bool):
                        raise ValueError('Scope flags must be booleans')
                result = export_vault(sources, output, reasoning=bool(data.get('reasoning')), style=bool(data.get('style', True)), demo=bool(data.get('demo')),
                                      folder=folder, exact_folder=data.get('exact_folder', False),
                                      all_chats=data.get('all_chats', False), literals=literals, dry_run=data.get('dry_run', False))
                self.respond(200, json.dumps(result))
            except (ValueError, OSError, TypeError) as exc:
                self.respond(400, json.dumps({'error': redactor.clean(str(exc))}))
            except Exception as exc:
                self.respond(500, json.dumps({'error': redactor.clean(f'Export failed: {exc}')}))
            finally:
                lock.release()

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'session2md is running at {url}\nPress Ctrl+C to stop.', flush=True)
    if browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
