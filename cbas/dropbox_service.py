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
import os
import stat
import tempfile
from contextlib import contextmanager
import dropbox
from dropbox.files import WriteMode, ListRevisionsMode
from cbas.validation import validar_nombre, validar_revision
from cbas.hasher import calcular_hash_bytes

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
            timeout=15,
            max_retries_on_error=1,
        )
    if DROPBOX_ACCESS_TOKEN:
        return dropbox.Dropbox(DROPBOX_ACCESS_TOKEN, timeout=15, max_retries_on_error=1)
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
    limpio = validar_nombre(nombre_archivo)
    return f"{DROPBOX_VAULT_FOLDER}/{limpio}"


def subir_version_archivo(ruta_local: str | Path, nombre_archivo: str | None = None,
                          contenido: bytes | None = None) -> dict:
    """
    Sube un archivo local a Dropbox en modo WriteMode.overwrite para generar
    un nuevo identificador de revision (rev) conservando las versiones anteriores.
    """
    ruta_path = Path(ruta_local)
    if not nombre_archivo:
        nombre_archivo = ruta_path.name

    ruta_nube = construir_ruta_dropbox(nombre_archivo)
    dbx = obtener_cliente_dropbox()

    if contenido is None:
        contenido = ruta_path.read_bytes()
    if len(contenido) > 150 * 1024 * 1024:
        raise ValueError('El archivo excede 150 MiB; esta versión no implementa subida por sesiones.')

    metadata = dbx.files_upload(
        contenido,
        ruta_nube,
        mode=WriteMode.overwrite,
        mute=True,
    )
    if metadata.content_hash != calcular_hash_bytes(contenido):
        raise RuntimeError('Dropbox devolvió un hash distinto al contenido enviado.')

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
    if rev is not None:
        validar_revision(rev)
    ruta_nube = construir_ruta_dropbox(nombre_archivo)
    dbx = obtener_cliente_dropbox()
    metadata, response = dbx.files_download(ruta_nube, rev=rev)
    try:
        contenido_bytes = response.content
    finally:
        response.close()
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


@contextmanager
def destino_restaurable(ruta: Path):
    """Comprueba y mantiene el permiso de reemplazo antes de cambiar Dropbox."""
    handle = None
    kernel = None
    if os.name == 'nt' and ruta.exists():
        if ruta.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY:
            raise PermissionError('El archivo está marcado como solo lectura.')
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        # DELETE access; compartir lectura, escritura y borrado. No elimina el archivo.
        handle = kernel.CreateFileW(str(ruta.resolve()), 0x10000, 7, None, 3, 0, None)
        if handle == wintypes.HANDLE(-1).value:
            raise PermissionError('El archivo está abierto o no permite reemplazo.')
    def liberar():
        nonlocal handle
        if handle is not None and kernel is not None:
            kernel.CloseHandle(handle)
            handle = None
    try:
        yield liberar
    finally:
        liberar()


def restaurar_version_en_carpeta(nombre_archivo: str, rev_objetivo: str) -> dict:
    """
    Restaura el archivo en Dropbox al identificador rev elegido mediante files_restore
    y descarga el contenido restaurado directamente en directorio_pyme.
    """
    validar_nombre(nombre_archivo, MONITORED_DIR)
    validar_revision(rev_objetivo)
    ruta_nube = construir_ruta_dropbox(nombre_archivo)
    ruta_local_destino = MONITORED_DIR / nombre_archivo
    with destino_restaurable(ruta_local_destino) as liberar:
        return _restaurar_en_destino(nombre_archivo, rev_objetivo, ruta_nube, ruta_local_destino, liberar)


def _restaurar_en_destino(nombre_archivo, rev_objetivo, ruta_nube, ruta_local_destino, liberar):
    dbx = obtener_cliente_dropbox()

    MONITORED_DIR.mkdir(parents=True, exist_ok=True)
    # Descargar y verificar ANTES de cambiar la versión activa o el archivo local.
    fd, temporal = tempfile.mkstemp(prefix='.cbas-restore-', dir=MONITORED_DIR)
    os.close(fd)
    try:
        dbx.files_download_to_file(temporal, ruta_nube, rev=rev_objetivo)
        contenido = Path(temporal).read_bytes()
        restaurado_meta = dbx.files_restore(ruta_nube, rev_objetivo)
        if calcular_hash_bytes(contenido) != restaurado_meta.content_hash:
            raise RuntimeError('La revisión descargada no coincide con el hash restaurado.')
        # Windows no permite MoveFileEx sobre un destino con handles abiertos.
        liberar()
        os.replace(temporal, ruta_local_destino)
    finally:
        Path(temporal).unlink(missing_ok=True)

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
        "_contenido": contenido,
    }
