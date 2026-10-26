"""
Servicio de comunicacion con Dropbox Cloud API v2 para CBAS.
Provee funciones para:
- Subir archivos generando nuevas revisiones (WriteMode.overwrite).
- Descargar los bytes de cualquier version especifica (rev) sin alterar el archivo local.
- Restaurar un archivo en la nube y en la carpeta local hacia una revision elegida.
- Consultar las revisiones registradas en Dropbox.
"""

from datetime import timezone
from pathlib import Path
import dropbox
from dropbox.files import WriteMode, ListRevisionsMode

from cbas.config import (
    DROPBOX_APP_KEY,
    DROPBOX_APP_SECRET,
    DROPBOX_REFRESH_TOKEN,
    DROPBOX_ACCESS_TOKEN,
    DROPBOX_VAULT_FOLDER,
    MONITORED_DIR,
)


def obtener_cliente_dropbox() -> dropbox.Dropbox:
    """Inicializa el cliente oficial de Dropbox API v2 usando Refresh Token OAuth 2.0."""
    if DROPBOX_REFRESH_TOKEN and DROPBOX_APP_KEY and DROPBOX_APP_SECRET:
        return dropbox.Dropbox(
            oauth2_refresh_token=DROPBOX_REFRESH_TOKEN,
            app_key=DROPBOX_APP_KEY,
            app_secret=DROPBOX_APP_SECRET,
        )
    if DROPBOX_ACCESS_TOKEN:
        return dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
    raise RuntimeError(
        "No se encontraron credenciales OAuth 2.0 validas en el archivo .env."
    )


def verificar_cuenta_dropbox() -> dict:
    """Verifica la sesion activa en Dropbox API v2 y retorna los datos reales de la cuenta."""
    dbx = obtener_cliente_dropbox()
    cuenta = dbx.users_get_current_account()
    espacio = dbx.users_get_space_usage()
    usado_mb = round(espacio.used / (1024 * 1024), 2)
    return {
        "conectado": True,
        "account_id": cuenta.account_id,
        "nombre_mostrar": cuenta.name.display_name,
        "email": cuenta.email,
        "pais": cuenta.country,
        "espacio_usado_mb": usado_mb,
        "carpeta_boveda": DROPBOX_VAULT_FOLDER,
    }


def construir_ruta_dropbox(nombre_archivo: str) -> str:
    limpio = nombre_archivo.lstrip("/")
    return f"{DROPBOX_VAULT_FOLDER}/{limpio}"


def subir_version_archivo(ruta_local: str | Path, nombre_archivo: str | None = None) -> dict:
    """
    Sube un archivo local a Dropbox en modo WriteMode.overwrite para generar
    un nuevo identificador de revision (rev) conservando las versiones anteriores.
    """
    ruta_path = Path(ruta_local)
    if not nombre_archivo:
        nombre_archivo = ruta_path.name

    ruta_nube = construir_ruta_dropbox(nombre_archivo)
    dbx = obtener_cliente_dropbox()

    with open(ruta_path, "rb") as f:
        contenido = f.read()

    metadata = dbx.files_upload(
        contenido,
        ruta_nube,
        mode=WriteMode.overwrite,
        mute=True,
    )

    fecha_utc = metadata.server_modified.replace(tzinfo=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )

    return {
        "dropbox_file_id": metadata.id,
        "nombre_archivo": metadata.name,
        "ruta_dropbox": metadata.path_display or ruta_nube,
        "rev": metadata.rev,
        "tamano_bytes": metadata.size,
        "content_hash": metadata.content_hash,
        "fecha_servidor_utc": fecha_utc,
    }


def descargar_bytes_version(nombre_archivo: str, rev: str | None = None) -> tuple[bytes, dict]:
    """
    Descarga desde Dropbox el contenido binario exacto de una version especifica (rev)
    sin modificar ni sobrescribir el archivo local en directorio_pyme.
    """
    ruta_nube = construir_ruta_dropbox(nombre_archivo)
    dbx = obtener_cliente_dropbox()
    metadata, response = dbx.files_download(ruta_nube, rev=rev)
    contenido_bytes = response.content
    fecha_utc = metadata.server_modified.replace(tzinfo=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )
    info = {
        "nombre_archivo": metadata.name,
        "rev": metadata.rev,
        "tamano_bytes": metadata.size,
        "content_hash": metadata.content_hash,
        "fecha_servidor_utc": fecha_utc,
    }
    return contenido_bytes, info


def listar_revisiones_dropbox(nombre_archivo: str, limite: int = 30) -> list[dict]:
    """Consulta el endpoint files_list_revisions de Dropbox para un archivo."""
    ruta_nube = construir_ruta_dropbox(nombre_archivo)
    dbx = obtener_cliente_dropbox()
    resultado = dbx.files_list_revisions(
        ruta_nube, mode=ListRevisionsMode.path, limit=limite
    )

    revisiones = []
    for idx, entrada in enumerate(resultado.entries):
        fecha_utc = entrada.server_modified.replace(tzinfo=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
        revisiones.append(
            {
                "orden": idx,
                "rev": entrada.rev,
                "tamano_bytes": entrada.size,
                "content_hash": entrada.content_hash,
                "fecha_servidor_utc": fecha_utc,
                "ruta_dropbox": entrada.path_display or ruta_nube,
                "dropbox_file_id": entrada.id,
            }
        )
    return revisiones


def restaurar_version_en_carpeta(nombre_archivo: str, rev_objetivo: str) -> dict:
    """
    Restaura el archivo en Dropbox al identificador rev elegido mediante files_restore
    y descarga el contenido restaurado directamente en directorio_pyme.
    """
    ruta_nube = construir_ruta_dropbox(nombre_archivo)
    ruta_local_destino = MONITORED_DIR / nombre_archivo
    dbx = obtener_cliente_dropbox()

    restaurado_meta = dbx.files_restore(ruta_nube, rev_objetivo)
    MONITORED_DIR.mkdir(parents=True, exist_ok=True)
    dbx.files_download_to_file(str(ruta_local_destino), ruta_nube)

    fecha_utc = restaurado_meta.server_modified.replace(tzinfo=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )

    return {
        "nombre_archivo": nombre_archivo,
        "ruta_dropbox": restaurado_meta.path_display or ruta_nube,
        "ruta_local": str(ruta_local_destino),
        "rev_solicitada": rev_objetivo,
        "nueva_rev_activa": restaurado_meta.rev,
        "content_hash": restaurado_meta.content_hash,
        "tamano_bytes": restaurado_meta.size,
        "fecha_servidor_utc": fecha_utc,
        "dropbox_file_id": restaurado_meta.id,
    }
