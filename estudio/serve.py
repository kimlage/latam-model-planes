#!/usr/bin/env python3
"""Serve the repository locally, with fresh editor code and loopback-only access."""
import argparse
import json
import shutil
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from video import converter, MAX_BYTES

encoding = threading.Lock()


class StudioHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if urlparse(self.path).path == '/api/video':
            self.send_json(200, {'mp4':bool(shutil.which('ffmpeg')), 'maxBytes':MAX_BYTES})
        else:
            super().do_GET()

    def send_json(self, status, value):
        data=json.dumps(value,ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if urlparse(self.path).path != '/api/video':
            return self.send_json(404, {'error':'Endpoint desconhecido.'})
        port=self.server.server_address[1]
        hosts={f'127.0.0.1:{port}',f'localhost:{port}'}
        # Only the local editor can request encoding, not a remote webpage.
        if self.headers.get('Host') not in hosts or self.headers.get('Origin') not in {'http://'+h for h in hosts} or self.headers.get('X-Latam-Studio') != '1':
            return self.send_json(403,{'error':'Use o editor na origem local do servidor.'})
        if not encoding.acquire(blocking=False):
            return self.send_json(409,{'error':'Já existe uma conversão em andamento.'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<=0 or length>MAX_BYTES:
                return self.send_json(413,{'error':'Sequência excede 512 MB ou está vazia.'})
            self.connection.settimeout(180)
            body=self.rfile.read(length)
            if len(body)!=length:
                raise ValueError('Transferência incompleta.')
            fps=float(parse_qs(urlparse(self.path).query).get('fps',['25'])[0])
            data=converter(body,fps)
            self.send_response(200)
            self.send_header('Content-Type','video/mp4')
            self.send_header('Content-Length',str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_json(400,{'error':str(e)})
        finally:
            encoding.release()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8137)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    handler = partial(StudioHandler, directory=str(root))
    with ThreadingHTTPServer(('127.0.0.1', args.port), handler) as server:
        print(f'Scene Studio: http://127.0.0.1:{args.port}/estudio/', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
