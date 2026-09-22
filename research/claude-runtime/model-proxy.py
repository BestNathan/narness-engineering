"""Credential-bearing model gateway, isolated from the coding-agent container."""
import http.client
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

UPSTREAM = urlsplit(os.environ.get('ANTHROPIC_BASE_URL', 'https://api.anthropic.com'))
if UPSTREAM.scheme != 'https' or UPSTREAM.username or UPSTREAM.password or UPSTREAM.query or UPSTREAM.fragment:
    raise RuntimeError('ANTHROPIC_BASE_URL must be a credential-free HTTPS base URL')
KEY = os.environ['ANTHROPIC_API_KEY']
MODEL = os.environ['CLAUDE_MODEL']

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Never log request bodies, authentication, or model responses.

    def do_GET(self):
        self.send_error(405)

    def do_POST(self):
        if self.path not in ('/v1/messages', '/v1/messages?beta=true', '/v1/messages/count_tokens', '/v1/messages/count_tokens?beta=true'):
            self.send_error(403)
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 32 * 1024 * 1024:
                self.send_error(413)
                return
            body = self.rfile.read(size)
            payload = json.loads(body)
            if payload.get('model') != MODEL:
                self.send_error(403, 'Only the frozen model is allowed')
                return
            headers = {'Content-Type': 'application/json', 'x-api-key': KEY,
                       'Authorization': 'Bearer ' + KEY,
                       'anthropic-version': self.headers.get('anthropic-version', '2023-06-01')}
            if self.headers.get('anthropic-beta'):
                headers['anthropic-beta'] = self.headers['anthropic-beta']
            conn = http.client.HTTPSConnection(UPSTREAM.hostname, UPSTREAM.port or 443, timeout=180)
            try:
                conn.request('POST', UPSTREAM.path.rstrip('/') + self.path, body=body, headers=headers)
                res = conn.getresponse()
                self.send_response(res.status)
                self.send_header('Content-Type', res.getheader('Content-Type', 'application/json'))
                self.send_header('Connection', 'close')
                self.end_headers()
                while chunk := res.read1(8192):
                    self.wfile.write(chunk)
                    self.wfile.flush()
            finally:
                conn.close()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            # Deliberately omit exception text: upstream failures can contain secrets.
            self.close_connection = True

ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
