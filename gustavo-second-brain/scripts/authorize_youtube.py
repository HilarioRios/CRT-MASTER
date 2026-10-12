"""Autoriza por OAuth la cuenta de YouTube de Gustavo y verifica que canal(es)
administra. Pide unicamente el scope https://www.googleapis.com/auth/youtube.force-ssl
y, tras autorizar, solo hace una llamada READ-ONLY (channels().list(mine=True)).
Este script NUNCA escribe, edita, sube ni borra nada en YouTube.

Uso:
    .venv/bin/python scripts/authorize_youtube.py
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

CLIENT_FILE = ROOT / os.environ["YOUTUBE_OAUTH_CLIENT_FILE"]
TOKEN_FILE = ROOT / os.environ["YOUTUBE_OAUTH_TOKEN_FILE"]


def get_credentials() -> Credentials:
    creds: Credentials | None = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except (ValueError, OSError):
            creds = None  # token file corrupto/ilegible -> tratar como si no existiera

    if creds and not creds.valid and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None  # refresh token revocado/invalido -> forzar flujo OAuth nuevo

    if not creds or not creds.valid:
        if not CLIENT_FILE.exists():
            raise FileNotFoundError(
                f"No se encontro el archivo de credenciales OAuth: {CLIENT_FILE}"
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
        creds = flow.run_local_server(port=0)

    # Persistir siempre el estado mas reciente (token nuevo o refrescado) para
    # que la proxima corrida no tenga que volver a pedir un refresh/autorizacion.
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json())
    TOKEN_FILE.chmod(0o600)

    return creds


def list_my_channels(creds: Credentials) -> list[dict]:
    """READ-ONLY: lista los canales administrados por la cuenta autenticada.
    No crea, modifica ni elimina nada."""
    youtube = build("youtube", "v3", credentials=creds)
    response = youtube.channels().list(
        part="snippet,contentDetails,statistics", mine=True
    ).execute()
    return response.get("items", [])


def main() -> None:
    creds = get_credentials()
    print(f"OK: token guardado en {TOKEN_FILE}")

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
    main()
