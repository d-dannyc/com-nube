"""
Configuracion centralizada del sistema CBAS.
Carga variables de entorno desde el archivo .env en la raiz del proyecto
y define las rutas de monitoreo local, base de datos de auditoria y contenedor en Dropbox.
"""

import os
import socket
import getpass
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

DROPBOX_APP_KEY = os.getenv("DROPBOX_APP_KEY", "").strip()
DROPBOX_APP_SECRET = os.getenv("DROPBOX_APP_SECRET", "").strip()
DROPBOX_REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN", "").strip()
DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN", "").strip()

CBAS_BACKEND_HOST = os.getenv("CBAS_BACKEND_HOST", "127.0.0.1").strip()
CBAS_BACKEND_PORT = int(os.getenv("CBAS_BACKEND_PORT", "5050"))
CBAS_BACKEND_URL = f"http://{CBAS_BACKEND_HOST}:{CBAS_BACKEND_PORT}"

MONITORED_DIR = BASE_DIR / "directorio_pyme"
DATABASE_PATH = BASE_DIR / "cbas_audit.db"
REPORTS_DIR = BASE_DIR / "docs"
DROPBOX_VAULT_FOLDER = os.getenv("CBAS_DROPBOX_FOLDER", "/CBAS_Pyme_Vault").strip()


def obtener_metadatos_estacion() -> dict:
    """Obtiene el usuario del sistema operativo, nombre de red e IP local de la estacion PYME."""
    try:
        usuario_so = getpass.getuser()
    except Exception:
        usuario_so = "operador_pyme"

    try:
        nombre_equipo = socket.gethostname()
    except Exception:
        nombre_equipo = "estacion-pyme-01"

    direccion_ip = "127.0.0.1"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            direccion_ip = s.getsockname()[0]
    except Exception:
        try:
            direccion_ip = socket.gethostbyname(nombre_equipo)
        except Exception:
            direccion_ip = "192.168.1.10"

    return {
        "usuario_so": usuario_so,
        "nombre_equipo": nombre_equipo,
        "direccion_ip": direccion_ip,
    }
