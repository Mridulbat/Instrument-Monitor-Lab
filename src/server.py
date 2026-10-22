"""Loopback-only dashboard server; no installation or external services required."""
import argparse
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from engine import RUN
from live import LiveMonitor
from study import run as run_study
LIVE = LiveMonitor()

ROOT = Path(__file__).resolve().parent


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, body, content_type):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self.reply(200, (ROOT/'index.html').read_bytes(), 'text/html; charset=utf-8')
        elif self.path == '/study.html':
            self.reply(200, (ROOT/'study.html').read_bytes(), 'text/html; charset=utf-8')
        else:
            self.reply(404, b'Not found', 'text/plain')

    def do_POST(self):
        if self.path not in ('/api/run', '/api/study'):
            self.reply(404, b'Not found', 'text/plain'); return
        origin = self.headers.get('Origin')
        expected = f'http://127.0.0.1:{self.server.server_port}'
        if origin and origin != expected:
            self.reply(403, b'Origin rejected', 'text/plain'); return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 1000000: raise ValueError('Request size must be 1 byte to 1 MB.')
            params = json.loads(self.rfile.read(length))
            if not isinstance(params, dict): raise ValueError('Expected a JSON object.')
            if self.path == '/api/study':
                result = run_study(**params)
            else:
                result = LIVE.poll() if params.pop('live', False) else RUN(params)
            self.reply(200, json.dumps(result, allow_nan=False).encode(), 'application/json')
        except (ValueError, TypeError, KeyError) as error:
            self.reply(400, json.dumps({'error': str(error)}).encode(), 'application/json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    try:
        with HTTPServer(('127.0.0.1', args.port), Handler) as server:
            url = f'http://127.0.0.1:{server.server_port}'
            print(f'Open {url} | Ctrl+C to stop', flush=True)
            if not args.no_browser: webbrowser.open(url)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    except OSError as error:
        parser.exit(1, f'Cannot start server: {error}. Try --port with another port.\n')
