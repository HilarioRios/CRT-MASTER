"""Autoriza por OAuth (Desktop app, local) el acceso de Drive que usara
scripts/sync_drive.py. Credenciales COMPLETAMENTE separadas de YouTube:
usa su propio OAuth client (GOOGLE_DRIVE_OAUTH_CLIENT_FILE, tipo "Desktop
app" en Google Cloud Console, distinto del "Web application" de YouTube) y
guarda su propio token (GOOGLE_DRIVE_OAUTH_TOKEN_FILE) -- nunca lee, toca
ni sobreescribe tokens/youtube_gustavo*.json.

Scope: https://www.googleapis.com/auth/drive (acceso completo), NO
drive.file. Se evaluo drive.file (least-privilege) primero, pero se
descarto: drive.file solo garantiza visibilidad de archivos que la propia
app creo o que el usuario abrio via file-picker -- sync_drive.py escribe
dentro de una carpeta preexistente (no creada por esta app) referenciada
por un folder_id estatico leido de config/drive_structure.json, nunca
descubierto via listado. Ese patron es exactamente el caso donde drive.file
puede fallar de forma impredecible (404 al crear un hijo de un folder_id
que la app nunca "vio"). La cuenta autorizada ya tiene permiso de escritura
real sobre esa carpeta especifica (verificado con
get_file_permissions/capabilities antes de llegar a este diseño) -- el
scope mas amplio no le da mas poder ahi, solo evita la restriccion de
visibilidad de la API. Trade-off real: el token puede, en teoria, acceder
a cualquier archivo del Drive de la cuenta autorizada, no solo a esta
carpeta -- aceptado a cambio de fiabilidad, ya que es exactamente lo que
se pidio para este script.

Verifica al final (READ-ONLY) que puede ver la carpeta destino del Segundo
Cerebro y que tiene permiso de escritura ahi.

Uso:
    .venv/bin/python scripts/authorize_drive.py
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

SCOPES = ["https://www.googleapis.com/auth/drive"]

CLIENT_FILE = ROOT / os.environ["GOOGLE_DRIVE_OAUTH_CLIENT_FILE"]
TOKEN_FILE = ROOT / os.environ["GOOGLE_DRIVE_OAUTH_TOKEN_FILE"]
DEST_ROOT_FOLDER_ID = os.environ["GOOGLE_DRIVE_SECOND_BRAIN_FOLDER_ID"]


def get_credentials() -> Credentials:
    creds: Credentials | None = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except (ValueError, OSError):
            creds = None

    if creds and not creds.valid and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if not CLIENT_FILE.exists():
            raise FileNotFoundError(
                f"No se encontro el archivo de credenciales OAuth: {CLIENT_FILE}"
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
        creds = flow.run_local_server(port=0)

    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json())
    TOKEN_FILE.chmod(0o600)

    return creds


def check_destination_access(creds: Credentials) -> dict:
    """READ-ONLY: confirma que la cuenta autenticada puede ver y escribir en
    la carpeta destino del Segundo Cerebro."""
    drive = build("drive", "v3", credentials=creds)
    return drive.files().get(
        fileId=DEST_ROOT_FOLDER_ID, fields="id,name,capabilities(canAddChildren,canEdit)"
    ).execute()


def main() -> None:
    creds = get_credentials()
    print(f"OK: token guardado en {TOKEN_FILE}")

    info = check_destination_access(creds)
    caps = info.get("capabilities", {})
    print(f"\nCarpeta destino: {info.get('name')} ({info.get('id')})")
    print(f"  canAddChildren={caps.get('canAddChildren')} canEdit={caps.get('canEdit')}")
    if not caps.get("canAddChildren"):
        print("  ADVERTENCIA: esta cuenta no puede crear archivos en esa carpeta.")


if __name__ == "__main__":
    main()
