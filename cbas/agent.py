"""
Agente Local de Monitoreo en Tiempo Real para CBAS.
Vigila la carpeta asociada (directorio_pyme/) mediante Python Watchdog:
- Las versiones se generan cuando un archivo se guarda en disco o se agrega a la carpeta.
- Aplica una ventana de estabilizacion (debounce de 1.0 segundo) al guardar.
- Verifica el content_hash por bloques de 4 MB para no crear versiones repetidas si el
  contenido no cambio y para evitar bucles cuando se restaura una version desde el panel.
- Soporta cualquier tipo de archivo (texto plano, CSV, JSON, Markdown, codigo, Excel, PDF, imagenes).
"""

import os
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from cbas.config import MONITORED_DIR, obtener_metadatos_estacion
from cbas.hasher import calcular_content_hash_dropbox
from cbas.dropbox_service import subir_version_archivo
from cbas.database import (
    es_archivo_texto,
    leer_snapshot_texto,
    registrar_nueva_version,
    obtener_archivo_por_nombre,
)

HASHES_SINCRONIZADOS: dict[str, str] = {}
LOCK_HASHES = threading.Lock()


def registrar_hash_sincronizado(nombre_archivo: str, content_hash: str) -> None:
    with LOCK_HASHES:
        HASHES_SINCRONIZADOS[nombre_archivo] = content_hash


def obtener_hash_sincronizado(nombre_archivo: str) -> str | None:
    with LOCK_HASHES:
        return HASHES_SINCRONIZADOS.get(nombre_archivo)


def es_archivo_temporal_o_ignorado(ruta: str | Path) -> bool:
    """Ignora archivos temporales de editores (.swp, .tmp, ~$) y ocultos."""
    nombre = os.path.basename(str(ruta))
    if not nombre:
        return True
    if nombre.startswith((".", "~$", "__")):
        return True
    if nombre.endswith("~"):
        return True
    extensiones_ignoradas = (".tmp", ".swp", ".swo", ".partial", ".crdownload", ".lock", ".pyc")
    return nombre.lower().endswith(extensiones_ignoradas)


def sincronizar_archivo_guardado(
    ruta_archivo: Path,
    tipo_operacion_forzada: str | None = None,
    detalle_personalizado: str | None = None,
) -> dict | None:
    """
    Se ejecuta cuando un archivo es creado o guardado en directorio_pyme:
    1. Calcula su hash de bloques de 4 MB.
    2. Si el contenido cambio respecto a la ultima version, lo sube a Dropbox.
    3. Registra la nueva version y el diff de cambios en la base de datos SQLite.
    """
    if not ruta_archivo.exists() or not ruta_archivo.is_file():
        return None

    nombre_archivo = ruta_archivo.name
    if es_archivo_temporal_o_ignorado(ruta_archivo):
        return None

    hash_local = calcular_content_hash_dropbox(ruta_archivo)
    ultimo_hash = obtener_hash_sincronizado(nombre_archivo)

    if ultimo_hash == hash_local and tipo_operacion_forzada is None:
        return None

    registro_previo = obtener_archivo_por_nombre(nombre_archivo)
    if (
        registro_previo
        and registro_previo.get("content_hash_actual") == hash_local
        and tipo_operacion_forzada is None
    ):
        registrar_hash_sincronizado(nombre_archivo, hash_local)
        return None

    if tipo_operacion_forzada:
        tipo_operacion = tipo_operacion_forzada
    elif registro_previo is None:
        tipo_operacion = "CREADO"
    else:
        tipo_operacion = "MODIFICADO"

    es_texto = es_archivo_texto(ruta_archivo)
    snapshot = leer_snapshot_texto(ruta_archivo) if es_texto else None

    resultado_nube = subir_version_archivo(ruta_archivo, nombre_archivo)
    registrar_hash_sincronizado(nombre_archivo, resultado_nube["content_hash"])

    estacion = obtener_metadatos_estacion()

    datos_version = {
        "nombre_archivo": nombre_archivo,
        "ruta_dropbox": resultado_nube["ruta_dropbox"],
        "dropbox_file_id": resultado_nube["dropbox_file_id"],
        "rev_dropbox": resultado_nube["rev"],
        "content_hash": resultado_nube["content_hash"],
        "tamano_bytes": resultado_nube["tamano_bytes"],
        "es_texto": es_texto,
        "tipo_operacion": tipo_operacion,
        "usuario_so": estacion["usuario_so"],
        "direccion_ip": estacion["direccion_ip"],
        "nombre_equipo": estacion["nombre_equipo"],
        "fecha_servidor_dropbox_utc": resultado_nube["fecha_servidor_utc"],
        "contenido_texto": snapshot,
    }
    if detalle_personalizado:
        datos_version["detalle_operacion"] = detalle_personalizado

    return registrar_nueva_version(datos_version)


class ManejadorCarpetaCBAS(FileSystemEventHandler):
    """
    Escucha eventos del sistema de archivos en directorio_pyme/.
    Agrupa escrituras consecutivas mediante un temporizador de 1.0 segundo
    para que cada guardado genere una unica version limpia.
    """

    def __init__(self, delay_segundos: float = 1.0):
        super().__init__()
        self.delay_segundos = delay_segundos
        self.temporizadores: dict[str, threading.Timer] = {}
        self.lock = threading.Lock()

    def _programar_sincronizacion(self, ruta_str: str) -> None:
        if es_archivo_temporal_o_ignorado(ruta_str):
            return

        with self.lock:
            if ruta_str in self.temporizadores:
                self.temporizadores[ruta_str].cancel()

            timer = threading.Timer(
                self.delay_segundos,
                self._ejecutar_sincronizacion,
                args=(Path(ruta_str),),
            )
            timer.daemon = True
            self.temporizadores[ruta_str] = timer
            timer.start()

    def _ejecutar_sincronizacion(self, ruta_archivo: Path) -> None:
        try:
            res = sincronizar_archivo_guardado(ruta_archivo)
            if res:
                print(
                    f"[Agente CBAS] {res['nombre_archivo']} -> Version v{res['numero_version']} "
                    f"(rev: {res['rev_dropbox']} | {res['resumen_cambio']})"
                )
        except Exception as exc:
            print(f"[Agente CBAS] Error al sincronizar {ruta_archivo.name}: {exc}")

    def on_created(self, event):
        if not event.is_directory:
            self._programar_sincronizacion(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._programar_sincronizacion(event.src_path)

    def on_moved(self, event):
        if not event.is_directory and hasattr(event, "dest_path"):
            self._programar_sincronizacion(event.dest_path)


def iniciar_observador_en_segundo_plano() -> Observer:
    """Inicia el observador Watchdog sobre directorio_pyme/."""
    MONITORED_DIR.mkdir(parents=True, exist_ok=True)
    manejador = ManejadorCarpetaCBAS(delay_segundos=1.0)
    observador = Observer()
    observador.schedule(manejador, str(MONITORED_DIR), recursive=False)
    observador.daemon = True
    observador.start()
    return observador
