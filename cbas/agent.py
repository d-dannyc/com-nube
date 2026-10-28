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
import time
from pathlib import Path
from datetime import datetime, timezone
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from cbas.config import MONITORED_DIR, obtener_metadatos_estacion
from cbas.hasher import calcular_hash_bytes
from cbas.validation import validar_nombre
from cbas.dropbox_service import subir_version_archivo
from cbas.database import (
    es_archivo_texto,
    registrar_nueva_version,
    obtener_archivo_por_nombre,
    MAX_TEXT_SNAPSHOT_BYTES,
)

HASHES_SINCRONIZADOS: dict[str, str] = {}
LOCK_HASHES = threading.Lock()
LOCKS_ARCHIVO = {}
PENDIENTES_AUDITORIA = {}
ESTADO = {'agente_activo': False, 'ultima_comprobacion_utc': None,
          'pendientes': 0, 'fallidos': 0, 'errores': {}}


def bloqueo_archivo(nombre):
    with LOCK_HASHES:
        return LOCKS_ARCHIVO.setdefault(nombre, threading.RLock())


def obtener_estado_sincronizacion():
    with LOCK_HASHES:
        return {**ESTADO, 'errores': dict(ESTADO['errores'])}


def confirmar_auditoria_pendiente(nombre):
    datos = PENDIENTES_AUDITORIA.get(nombre)
    if datos is None:
        return None
    resultado = registrar_nueva_version(datos)
    registrar_hash_sincronizado(nombre, datos['content_hash'])
    del PENDIENTES_AUDITORIA[nombre]
    return resultado


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


def sincronizar_archivo_guardado(ruta_archivo, tipo_operacion_forzada=None, detalle_personalizado=None):
    ruta_archivo = Path(ruta_archivo)
    validar_nombre(ruta_archivo.name, MONITORED_DIR)
    with bloqueo_archivo(ruta_archivo.name):
        recuperado = confirmar_auditoria_pendiente(ruta_archivo.name)
        return _sincronizar_archivo(ruta_archivo, tipo_operacion_forzada, detalle_personalizado) or recuperado


def _sincronizar_archivo(
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

    antes = ruta_archivo.stat()
    if antes.st_size > 150 * 1024 * 1024:
        raise ValueError('Máximo admitido: 150 MiB por archivo.')
    contenido = ruta_archivo.read_bytes()
    despues = ruta_archivo.stat()
    if (antes.st_mtime_ns, antes.st_size) != (despues.st_mtime_ns, despues.st_size):
        raise RuntimeError('El archivo sigue cambiando; se reintentará.')
    hash_local = calcular_hash_bytes(contenido)
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

    es_texto = es_archivo_texto(ruta_archivo, contenido)
    snapshot = (contenido.decode('utf-8', errors='replace')
                if es_texto and len(contenido) <= MAX_TEXT_SNAPSHOT_BYTES else None)

    resultado_nube = subir_version_archivo(ruta_archivo, nombre_archivo, contenido=contenido)

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

    PENDIENTES_AUDITORIA[nombre_archivo] = datos_version
    return confirmar_auditoria_pendiente(nombre_archivo)


class ManejadorCarpetaCBAS(FileSystemEventHandler):
    """
    Escucha eventos del sistema de archivos en directorio_pyme/.
    Agrupa escrituras consecutivas mediante un temporizador de 1.0 segundo
    para que cada guardado genere una unica version limpia.
    """

    def __init__(self, despertar):
        super().__init__()
        self.despertar = despertar

    def _programar_sincronizacion(self, ruta_str: str) -> None:
        if es_archivo_temporal_o_ignorado(ruta_str):
            return

        self.despertar.set()

    def on_created(self, event):
        if not event.is_directory:
            self._programar_sincronizacion(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._programar_sincronizacion(event.src_path)

    def on_moved(self, event):
        if not event.is_directory and hasattr(event, "dest_path"):
            self._programar_sincronizacion(event.dest_path)


def reconciliar_carpeta():
    resultados, errores = [], {}
    rutas = {p.name: p for p in MONITORED_DIR.iterdir()
             if p.is_file() and not es_archivo_temporal_o_ignorado(p)}
    for nombre in list(PENDIENTES_AUDITORIA):
        rutas.setdefault(nombre, MONITORED_DIR / nombre)
    with LOCK_HASHES:
        ESTADO['pendientes'] = len(rutas)
    for nombre, ruta in sorted(rutas.items()):
        try:
            resultado = sincronizar_archivo_guardado(ruta)
            if resultado:
                resultados.append(resultado)
        except Exception:
            errores[nombre] = 'Respaldo pendiente. Comprueba conexión, permisos y tamaño; se reintentará.'
        finally:
            with LOCK_HASHES:
                ESTADO['pendientes'] -= 1
    with LOCK_HASHES:
        ESTADO.update(ultima_comprobacion_utc=datetime.now(timezone.utc).isoformat(),
                      fallidos=len(errores), errores=errores)
    return resultados


class AgenteCBAS:
    def __init__(self):
        self.fin = threading.Event()
        self.despertar = threading.Event()
        self.observador = Observer()
        self.observador.schedule(ManejadorCarpetaCBAS(self.despertar), str(MONITORED_DIR), recursive=False)
        self.hilo = threading.Thread(target=self._ejecutar, daemon=True)

    def start(self):
        self.observador.start()
        with LOCK_HASHES:
            ESTADO['agente_activo'] = True
        self.hilo.start()

    def _ejecutar(self):
        try:
            while not self.fin.is_set():
                self.despertar.clear()
                try:
                    MONITORED_DIR.mkdir(parents=True, exist_ok=True)
                    reconciliar_carpeta()
                except OSError:
                    with LOCK_HASHES:
                        ESTADO.update(fallidos=1, pendientes=0, errores={
                            'carpeta': 'No se pudo leer la carpeta monitoreada. Comprueba su ubicación y permisos.'})
                if self.despertar.wait(15):
                    # ponytail: debounce de carpeta limitado a 15s; evita que un log
                    # continuo bloquee los demás archivos. Estabilidad por archivo si crece la carga.
                    limite = time.monotonic() + 15
                    while not self.fin.is_set():
                        restante = limite - time.monotonic()
                        if restante <= 0:
                            break
                        self.despertar.clear()
                        if not self.despertar.wait(min(1, restante)):
                            break
        finally:
            with LOCK_HASHES:
                ESTADO['agente_activo'] = False

    def stop(self):
        self.fin.set()
        self.despertar.set()
        self.observador.stop()

    def join(self):
        self.observador.join()
        self.hilo.join(timeout=20)


def iniciar_observador_en_segundo_plano():
    """Inicia el observador Watchdog sobre directorio_pyme/."""
    MONITORED_DIR.mkdir(parents=True, exist_ok=True)
    agente = AgenteCBAS()
    agente.start()
    return agente
