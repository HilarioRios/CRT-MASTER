"""Servidor HTTP local minimo para recibir el callback de OAuth en
http://127.0.0.1:8765/oauth2/callback, expuesto a internet via Cloudflare
Quick Tunnel para que Gustavo pueda autorizar desde su propio dispositivo.

Por ahora solo responde con una pagina de confirmacion -- NO intercambia el
`code` por un token todavia (eso se hace en un paso posterior, explicito).
No imprime ni guarda ningun parametro recibido en la query string.

Uso:
    .venv/bin/python scripts/oauth_callback_server.py
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "127.0.0.1"
PORT = 8765


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] != "/oauth2/callback":
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Recibido</h1>"
            b"<p>Puedes cerrar esta pestana. Avisa a quien configuro este "
            b"servidor que el callback llego.</p></body></html>"
        )

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
        print(f"[callback] {self.address_string()} - {format % args}", flush=True)


def main() -> None:
    server = HTTPServer((HOST, PORT), CallbackHandler)
    print(f"Escuchando en http://{HOST}:{PORT}/oauth2/callback ...", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
