"""Autorizacion OAuth remota de YouTube: genera un link de autorizacion para
que Gustavo lo abra desde SU PROPIO dispositivo, recibe el callback a traves
del Cloudflare Quick Tunnel ya activo (no lo reinicia), guarda el token, y
verifica con una operacion READ-ONLY que canal(es) administra la cuenta.

Nunca abre un navegador local ni imprime client_secret, access_token o
refresh_token.

Uso:
    .venv/bin/python scripts/authorize_youtube_remote.py
"""
from __future__ import annotations

import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow

sys.path.insert(0, str(Path(__file__).resolve().parent))
from authorize_youtube import list_my_channels  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

CLIENT_FILE = ROOT / os.environ["YOUTUBE_OAUTH_WEB_CLIENT_FILE"]
TOKEN_FILE = ROOT / os.environ["YOUTUBE_OAUTH_TOKEN_FILE"]
REDIRECT_URI = os.environ["YOUTUBE_OAUTH_REDIRECT_URI"]

_parsed_redirect = urlparse(REDIRECT_URI)
CALLBACK_PATH = _parsed_redirect.path or "/oauth2/callback"
LOCAL_HOST, LOCAL_PORT = "127.0.0.1", 8765


def build_flow() -> Flow:
    if not CLIENT_FILE.exists():
        raise FileNotFoundError(
            f"No se encontro el archivo de credenciales OAuth web: {CLIENT_FILE}"
        )
    return Flow.from_client_secrets_file(
        str(CLIENT_FILE), scopes=SCOPES, redirect_uri=REDIRECT_URI
    )


def get_authorization_url(flow: Flow) -> tuple[str, str]:
    """access_type=offline + prompt=consent para asegurar que llegue un
    refresh_token (si no, el token expira y nadie puede re-autorizar por su
    cuenta sin repetir todo este proceso remoto)."""
    return flow.authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="true"
    )


def match_callback(path: str) -> dict | None:
    """Parsea un path de request contra CALLBACK_PATH. Devuelve
    {'code', 'state', 'error'} si coincide, o None si no es el callback."""
    parsed = urlparse(path)
    if parsed.path != CALLBACK_PATH:
        return None
    params = parse_qs(parsed.query)
    return {
        "code": params.get("code", [None])[0],
        "state": params.get("state", [None])[0],
        "error": params.get("error", [None])[0],
    }


def accept_callback(result: dict, expected_state: str) -> bool:
    """Proteccion CSRF: solo se acepta un callback cuyo 'state' coincide
    exactamente con el emitido al generar la URL de autorizacion."""
    return result.get("state") == expected_state


def _make_handler(on_callback):
    class _CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            result = match_callback(self.path)
            if result is None:
                self.send_response(404)
                self.end_headers()
                return

            on_callback(result)

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if result["error"]:
                body = "<h1>Autorizacion rechazada</h1><p>Puedes cerrar esta pestana.</p>"
            else:
                body = "<h1>Autorizacion recibida</h1><p>Gracias. Ya puedes cerrar esta pestana.</p>"
            self.wfile.write(body.encode("utf-8"))

        def log_message(self, format: str, *args) -> None:  # noqa: A002
            print(f"[callback] {self.address_string()} - {format % args}", flush=True)

    return _CallbackHandler


def wait_for_callback(expected_state: str) -> str:
    """Bloquea hasta recibir un callback con 'code' y el 'state' esperado
    (proteccion CSRF: un callback con state distinto o ausente se ignora y
    se sigue esperando)."""
    received: dict = {}

    def on_callback(result: dict) -> None:
        if not accept_callback(result, expected_state):
            print("[callback] state inesperado, ignorado", flush=True)
            return
        received.update(result)

    server = HTTPServer((LOCAL_HOST, LOCAL_PORT), _make_handler(on_callback))
    print(
        f"Esperando el callback de Gustavo en http://{LOCAL_HOST}:{LOCAL_PORT}{CALLBACK_PATH} "
        "(publico a traves del tunel ya activo) ...",
        flush=True,
    )
    while "code" not in received and "error" not in received:
        server.handle_request()
    server.server_close()

    if received.get("error"):
        raise RuntimeError(f"Gustavo rechazo la autorizacion: {received['error']}")
    return received["code"]


def main(token_file: Path | None = None) -> None:
    """token_file permite autorizar una cuenta de Google adicional (otro
    canal administrado por otra cuenta) sin pisar el token por defecto
    (YOUTUBE_OAUTH_TOKEN_FILE). Por defecto usa ese token por defecto."""
    token_file = token_file or TOKEN_FILE

    flow = build_flow()
    auth_url, state = get_authorization_url(flow)

    print("\n=== Envia este link a Gustavo para que autorice desde su propio dispositivo ===\n")
    print(auth_url)
    print()

    code = wait_for_callback(expected_state=state)
    flow.fetch_token(code=code)
    creds = flow.credentials

    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(creds.to_json())
    token_file.chmod(0o600)
    print(f"OK: token guardado en {token_file}")

    channels = list_my_channels(creds)
    if not channels:
        print("La cuenta autenticada no administra ningun canal de YouTube.")
        return

    print(f"\nCanal(es) administrados por la cuenta autenticada ({len(channels)}):")
    for ch in channels:
        snippet = ch.get("snippet", {})
        stats = ch.get("statistics", {})
        print(
            f"  - {snippet.get('title')} "
            f"(channelId={ch.get('id')}, "
            f"suscriptores={stats.get('subscriberCount', 'oculto')}, "
            f"videos={stats.get('videoCount', '?')})"
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--token-file",
        type=str,
        default=None,
        help="Ruta de salida del token, relativa a la raiz del proyecto "
             "(por defecto: YOUTUBE_OAUTH_TOKEN_FILE del .env). Usar para "
             "autorizar una cuenta de Google adicional sin pisar el token existente.",
    )
    args = parser.parse_args()
    main(token_file=(ROOT / args.token_file) if args.token_file else None)
