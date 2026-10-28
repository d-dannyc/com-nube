"""
Asistente interactivo de vinculacion OAuth 2.0 (Offline Access / Refresh Token) para CBAS.
Genera y almacena automaticamente el Refresh Token de larga duracion en el archivo .env
de la raiz del proyecto sin presuponer experiencia previa del administrador.
"""

from pathlib import Path
from getpass import getpass
from dotenv import set_key
from dropbox import DropboxOAuth2FlowNoRedirect

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


def configurar_oauth_interactivo():
    print("=" * 72)
    print("ASISTENTE DE VINCULACION OAUTH 2.0 - CLOUD BACKUP AND AUDIT SYSTEM (CBAS)")
    print("=" * 72)
    print("Este asistente conectara su aplicacion de Dropbox Developers con CBAS.\n")

    app_key = input("1. Ingrese su App key de Dropbox: ").strip()
    app_secret = getpass("2. Ingrese su App secret de Dropbox (oculto): ").strip()

    if not app_key or not app_secret:
        print("[ERROR] Debe proporcionar tanto el App key como el App secret.")
        return

    auth_flow = DropboxOAuth2FlowNoRedirect(
        consumer_key=app_key,
        consumer_secret=app_secret,
        token_access_type="offline",
        scope=[
            "account_info.read",
            "files.metadata.read",
            "files.content.read",
            "files.content.write",
        ],
    )

    authorize_url = auth_flow.start()
    print("\n3. Abra el siguiente enlace en su navegador web y presione Permitir (Allow):")
    print(f"\n   {authorize_url}\n")
    auth_code = input("4. Pegue aqui el codigo de autorizacion entregado por Dropbox: ").strip()

    try:
        oauth_result = auth_flow.finish(auth_code)
    except Exception as exc:
        print(f"\n[ERROR] No se pudo canjear el codigo de autorizacion: {exc}")
        return

    for clave, valor in {'DROPBOX_APP_KEY': app_key, 'DROPBOX_APP_SECRET': app_secret,
                         'DROPBOX_REFRESH_TOKEN': oauth_result.refresh_token}.items():
        set_key(str(ENV_FILE), clave, valor)
    print("\n[OK] Vinculacion OAuth 2.0 completada con exito.")
    print(f"[OK] Credenciales guardadas en: {ENV_FILE}")


if __name__ == "__main__":
    configurar_oauth_interactivo()
