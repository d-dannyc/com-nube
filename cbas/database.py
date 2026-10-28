"""
Capa de persistencia de metadatos y control de versiones para CBAS.
Almacena el inventario de archivos de la carpeta monitoreada, el historial de versiones
asociado a los identificadores rev de Dropbox y las instantaneas de texto para calcular
comparaciones de cambios (Diff estilo Git) de forma instantanea.
"""

import difflib
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from cbas.config import DATABASE_PATH

EXTENSIONES_TEXTO = {
    ".txt", ".csv", ".json", ".md", ".py", ".sql", ".xml", ".yaml", ".yml",
    ".html", ".css", ".js", ".ts", ".ini", ".cfg", ".conf", ".log", ".sh",
}
EXTENSIONES_BINARIAS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".zip", ".rar",
    ".7z", ".tar", ".gz", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4",
    ".mp3", ".wav", ".db", ".sqlite", ".sqlite3", ".exe", ".bin",
}
MAX_TEXT_SNAPSHOT_BYTES = 512 * 1024  # 512 KB


@contextmanager
def obtener_conexion():
    conn = sqlite3.connect(str(DATABASE_PATH), timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def es_archivo_texto(ruta_archivo: Path, contenido: bytes | None = None) -> bool:
    """Determina si un archivo es legible como texto plano para habilitar la comparacion de lineas (Diff)."""
    ext = ruta_archivo.suffix.lower()
    if ext in EXTENSIONES_BINARIAS:
        return False
    if ext in EXTENSIONES_TEXTO:
        return True
    try:
        if contenido is None:
            with ruta_archivo.open('rb') as archivo:
                muestra = archivo.read(2048)
        else:
            muestra = contenido[:2048]
        if b"\x00" in muestra:
            return False
        muestra.decode("utf-8")
        return True
    except Exception:
        return False


def leer_snapshot_texto(ruta_archivo: Path) -> str | None:
    """Lee el contenido de texto si el archivo es de texto y no excede el limite de instantanea."""
    try:
        if not ruta_archivo.exists() or not ruta_archivo.is_file():
            return None
        if ruta_archivo.stat().st_size > MAX_TEXT_SNAPSHOT_BYTES:
            return None
        if not es_archivo_texto(ruta_archivo):
            return None
        return ruta_archivo.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def calcular_resumen_y_diff(texto_anterior: str | None, texto_nuevo: str | None) -> dict:
    """
    Calcula las diferencias linea por linea entre dos versiones de un archivo de texto
    al estilo de Git (lineas agregadas, eliminadas y contexto).
    """
    if texto_nuevo is None:
        return {
            "es_texto": False,
            "lineas_agregadas": 0,
            "lineas_eliminadas": 0,
            "resumen": "Archivo binario",
            "lineas_diff": [],
        }

    lineas_nuevas = texto_nuevo.splitlines()
    if texto_anterior is None:
        lineas_diff = [
            {
                "tipo": "agregada",
                "num_ant": None,
                "num_nueva": idx + 1,
                "texto": linea,
            }
            for idx, linea in enumerate(lineas_nuevas)
        ]
        total = len(lineas_nuevas)
        return {
            "es_texto": True,
            "lineas_agregadas": total,
            "lineas_eliminadas": 0,
            "resumen": f"+{total} lineas (version inicial)",
            "lineas_diff": lineas_diff,
        }

    lineas_ant = texto_anterior.splitlines()
    matcher = difflib.SequenceMatcher(None, lineas_ant, lineas_nuevas)
    lineas_diff = []
    agregadas = 0
    eliminadas = 0
    num_a = 1
    num_b = 1

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for linea in lineas_ant[i1:i2]:
                lineas_diff.append(
                    {
                        "tipo": "igual",
                        "num_ant": num_a,
                        "num_nueva": num_b,
                        "texto": linea,
                    }
                )
                num_a += 1
                num_b += 1
        elif tag in ("Delete", "delete", "replace"):
            for linea in lineas_ant[i1:i2]:
                lineas_diff.append(
                    {
                        "tipo": "eliminada",
                        "num_ant": num_a,
                        "num_nueva": None,
                        "texto": linea,
                    }
                )
                eliminadas += 1
                num_a += 1
            if tag == "replace":
                for linea in lineas_nuevas[j1:j2]:
                    lineas_diff.append(
                        {
                            "tipo": "agregada",
                            "num_ant": None,
                            "num_nueva": num_b,
                            "texto": linea,
                        }
                    )
                    agregadas += 1
                    num_b += 1
        elif tag == "insert":
            for linea in lineas_nuevas[j1:j2]:
                lineas_diff.append(
                    {
                        "tipo": "agregada",
                        "num_ant": None,
                        "num_nueva": num_b,
                        "texto": linea,
                    }
                )
                agregadas += 1
                num_b += 1

    partes = []
    if agregadas > 0:
        partes.append(f"+{agregadas} {'linea' if agregadas == 1 else 'lineas'}")
    if eliminadas > 0:
        partes.append(f"-{eliminadas} {'linea' if eliminadas == 1 else 'lineas'}")
    resumen = ", ".join(partes) if partes else "Sin cambios de lineas"

    return {
        "es_texto": True,
        "lineas_agregadas": agregadas,
        "lineas_eliminadas": eliminadas,
        "resumen": resumen,
        "lineas_diff": lineas_diff,
    }


def inicializar_base_datos() -> None:
    """Crea las tablas de archivos monitoreados y versiones si no existen."""
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS archivos_monitoreados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_archivo TEXT NOT NULL UNIQUE,
                extension TEXT NOT NULL,
                es_texto INTEGER NOT NULL DEFAULT 1,
                ruta_dropbox TEXT NOT NULL,
                dropbox_file_id TEXT,
                version_actual INTEGER NOT NULL DEFAULT 1,
                rev_actual TEXT NOT NULL,
                content_hash_actual TEXT NOT NULL,
                tamano_bytes INTEGER NOT NULL,
                estado_archivo TEXT NOT NULL DEFAULT 'ACTIVO',
                ultimo_usuario_so TEXT NOT NULL,
                ultima_ip TEXT NOT NULL,
                ultimo_equipo TEXT NOT NULL,
                ultima_modificacion_utc TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS versiones_archivo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_archivo TEXT NOT NULL,
                numero_version INTEGER NOT NULL,
                ruta_dropbox TEXT NOT NULL,
                rev_dropbox TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                tamano_bytes INTEGER NOT NULL,
                es_texto INTEGER NOT NULL DEFAULT 1,
                tipo_operacion TEXT NOT NULL,
                lineas_agregadas INTEGER NOT NULL DEFAULT 0,
                lineas_eliminadas INTEGER NOT NULL DEFAULT 0,
                resumen_cambio TEXT NOT NULL,
                usuario_so TEXT NOT NULL,
                direccion_ip TEXT NOT NULL,
                nombre_equipo TEXT NOT NULL,
                fecha_servidor_dropbox_utc TEXT,
                fecha_registro_utc TEXT NOT NULL,
                detalle_operacion TEXT NOT NULL,
                contenido_texto TEXT
            )
            """
        )
        conn.commit()


def registrar_nueva_version(datos: dict) -> dict:
    """
    Registra una nueva version de un archivo en la tabla versiones_archivo,
    calcula automaticamente las lineas agregadas/eliminadas respecto a la version anterior
    y actualiza el registro principal en archivos_monitoreados.
    """
    ahora_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    nombre_archivo = datos["nombre_archivo"]
    extension = Path(nombre_archivo).suffix.lower() or "sin_ext"
    ruta_dropbox = datos["ruta_dropbox"]
    dropbox_file_id = datos.get("dropbox_file_id", "")
    rev_dropbox = datos["rev_dropbox"]
    content_hash = datos["content_hash"]
    tamano_bytes = int(datos["tamano_bytes"])
    es_texto_bool = bool(datos.get("es_texto", True))
    tipo_operacion = datos["tipo_operacion"]
    usuario_so = datos["usuario_so"]
    direccion_ip = datos["direccion_ip"]
    nombre_equipo = datos["nombre_equipo"]
    fecha_servidor_utc = datos.get("fecha_servidor_dropbox_utc", ahora_utc)
    contenido_texto = datos.get("contenido_texto")
    estado_archivo = datos.get("estado_archivo", "ACTIVO")

    with obtener_conexion() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT numero_version, contenido_texto, tamano_bytes
            FROM versiones_archivo
            WHERE nombre_archivo = ?
            ORDER BY numero_version DESC LIMIT 1
            """,
            (nombre_archivo,),
        )
        ultima_version_row = cursor.fetchone()

        if ultima_version_row is None:
            nuevo_num_version = 1
            texto_previo = None
            bytes_previos = 0
        else:
            nuevo_num_version = int(ultima_version_row["numero_version"]) + 1
            texto_previo = ultima_version_row["contenido_texto"]
            bytes_previos = int(ultima_version_row["tamano_bytes"])

        if es_texto_bool and contenido_texto is not None:
            info_diff = calcular_resumen_y_diff(texto_previo, contenido_texto)
            agregadas = info_diff["lineas_agregadas"]
            eliminadas = info_diff["lineas_eliminadas"]
            resumen_cambio = datos.get("resumen_cambio") or info_diff["resumen"]
        elif es_texto_bool:
            agregadas = 0
            eliminadas = 0
            diff_bytes = tamano_bytes - bytes_previos
            signo = "+" if diff_bytes >= 0 else ""
            resumen_cambio = datos.get("resumen_cambio") or f"Archivo de texto grande ({signo}{diff_bytes} bytes)"
        else:
            agregadas = 0
            eliminadas = 0
            diff_bytes = tamano_bytes - bytes_previos
            signo = "+" if diff_bytes >= 0 else ""
            resumen_cambio = datos.get("resumen_cambio") or f"Archivo binario ({signo}{diff_bytes} bytes)"

        detalle_operacion = datos.get(
            "detalle_operacion",
            f"Version v{nuevo_num_version} sincronizada con Dropbox ({resumen_cambio}).",
        )

        cursor.execute(
            """
            INSERT INTO versiones_archivo (
                nombre_archivo, numero_version, ruta_dropbox, rev_dropbox, content_hash,
                tamano_bytes, es_texto, tipo_operacion, lineas_agregadas, lineas_eliminadas,
                resumen_cambio, usuario_so, direccion_ip, nombre_equipo,
                fecha_servidor_dropbox_utc, fecha_registro_utc, detalle_operacion, contenido_texto
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nombre_archivo,
                nuevo_num_version,
                ruta_dropbox,
                rev_dropbox,
                content_hash,
                tamano_bytes,
                1 if es_texto_bool else 0,
                tipo_operacion,
                agregadas,
                eliminadas,
                resumen_cambio,
                usuario_so,
                direccion_ip,
                nombre_equipo,
                fecha_servidor_utc,
                ahora_utc,
                detalle_operacion,
                contenido_texto,
            ),
        )
        evento_id = cursor.lastrowid

        cursor.execute(
            "SELECT id FROM archivos_monitoreados WHERE nombre_archivo = ?",
            (nombre_archivo,),
        )
        existente = cursor.fetchone()

        if existente:
            cursor.execute(
                """
                UPDATE archivos_monitoreados
                SET extension = ?,
                    es_texto = ?,
                    ruta_dropbox = ?,
                    dropbox_file_id = COALESCE(NULLIF(?, ''), dropbox_file_id),
                    version_actual = ?,
                    rev_actual = ?,
                    content_hash_actual = ?,
                    tamano_bytes = ?,
                    estado_archivo = ?,
                    ultimo_usuario_so = ?,
                    ultima_ip = ?,
                    ultimo_equipo = ?,
                    ultima_modificacion_utc = ?
                WHERE nombre_archivo = ?
                """,
                (
                    extension,
                    1 if es_texto_bool else 0,
                    ruta_dropbox,
                    dropbox_file_id,
                    nuevo_num_version,
                    rev_dropbox,
                    content_hash,
                    tamano_bytes,
                    estado_archivo,
                    usuario_so,
                    direccion_ip,
                    nombre_equipo,
                    ahora_utc,
                    nombre_archivo,
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO archivos_monitoreados (
                    nombre_archivo, extension, es_texto, ruta_dropbox, dropbox_file_id,
                    version_actual, rev_actual, content_hash_actual, tamano_bytes,
                    estado_archivo, ultimo_usuario_so, ultima_ip, ultimo_equipo,
                    ultima_modificacion_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    nombre_archivo,
                    extension,
                    1 if es_texto_bool else 0,
                    ruta_dropbox,
                    dropbox_file_id,
                    nuevo_num_version,
                    rev_dropbox,
                    content_hash,
                    tamano_bytes,
                    estado_archivo,
                    usuario_so,
                    direccion_ip,
                    nombre_equipo,
                    ahora_utc,
                ),
            )

        conn.commit()

    return {
        "id": evento_id,
        "nombre_archivo": nombre_archivo,
        "numero_version": nuevo_num_version,
        "rev_dropbox": rev_dropbox,
        "resumen_cambio": resumen_cambio,
        "fecha_registro_utc": ahora_utc,
    }


def listar_archivos_monitoreados() -> list[dict]:
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM archivos_monitoreados ORDER BY nombre_archivo ASC"
        )
        return [dict(row) for row in cursor.fetchall()]


def obtener_archivo_por_nombre(nombre_archivo: str) -> dict | None:
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM archivos_monitoreados WHERE nombre_archivo = ?",
            (nombre_archivo,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def listar_versiones_de_archivo(nombre_archivo: str) -> list[dict]:
    """Devuelve todas las versiones de un archivo ordenadas de la mas reciente a la mas antigua."""
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, nombre_archivo, numero_version, ruta_dropbox, rev_dropbox,
                   content_hash, tamano_bytes, es_texto, tipo_operacion,
                   lineas_agregadas, lineas_eliminadas, resumen_cambio,
                   usuario_so, direccion_ip, nombre_equipo,
                   fecha_servidor_dropbox_utc, fecha_registro_utc, detalle_operacion
            FROM versiones_archivo
            WHERE nombre_archivo = ?
            ORDER BY numero_version DESC
            """,
            (nombre_archivo,),
        )
        return [dict(row) for row in cursor.fetchall()]


def obtener_version_especifica(nombre_archivo: str, numero_version: int | None = None, rev_dropbox: str | None = None) -> dict | None:
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        if numero_version is not None:
            cursor.execute(
                "SELECT * FROM versiones_archivo WHERE nombre_archivo = ? AND numero_version = ?",
                (nombre_archivo, int(numero_version)),
            )
        else:
            cursor.execute(
                "SELECT * FROM versiones_archivo WHERE nombre_archivo = ? AND rev_dropbox = ? ORDER BY numero_version DESC LIMIT 1",
                (nombre_archivo, rev_dropbox),
            )
        row = cursor.fetchone()
        return dict(row) if row else None


def guardar_snapshot_texto_en_version(version_id: int, contenido_texto: str) -> None:
    with obtener_conexion() as conn:
        conn.execute(
            "UPDATE versiones_archivo SET contenido_texto = ? WHERE id = ?",
            (contenido_texto, version_id),
        )
        conn.commit()


def listar_actividad_reciente(limite: int = 100, nombre_archivo: str | None = None) -> list[dict]:
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        if nombre_archivo:
            cursor.execute(
                """
                SELECT id, nombre_archivo, numero_version, ruta_dropbox, rev_dropbox,
                       content_hash, tamano_bytes, tipo_operacion, resumen_cambio,
                       usuario_so, direccion_ip, nombre_equipo, fecha_registro_utc, detalle_operacion
                FROM versiones_archivo
                WHERE nombre_archivo = ?
                ORDER BY id DESC LIMIT ?
                """,
                (nombre_archivo, limite),
            )
        else:
            cursor.execute(
                """
                SELECT id, nombre_archivo, numero_version, ruta_dropbox, rev_dropbox,
                       content_hash, tamano_bytes, tipo_operacion, resumen_cambio,
                       usuario_so, direccion_ip, nombre_equipo, fecha_registro_utc, detalle_operacion
                FROM versiones_archivo
                ORDER BY id DESC LIMIT ?
                """,
                (limite,),
            )
        return [dict(row) for row in cursor.fetchall()]


def obtener_resumen_sistema() -> dict:
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM archivos_monitoreados")
        total_archivos = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as total FROM versiones_archivo")
        total_versiones = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT COUNT(*) as total FROM versiones_archivo WHERE tipo_operacion = 'RESTAURADO'"
        )
        total_restauraciones = cursor.fetchone()["total"]

        cursor.execute("SELECT COALESCE(MAX(id), 0) as ultimo_evento_id FROM versiones_archivo")
        ultimo_evento_id = cursor.fetchone()["ultimo_evento_id"]

        cursor.execute("SELECT COALESCE(SUM(tamano_bytes), 0) as bytes_totales FROM archivos_monitoreados")
        bytes_totales = cursor.fetchone()["bytes_totales"]

    return {
        "total_archivos": total_archivos,
        "total_versiones": total_versiones,
        "total_restauraciones": total_restauraciones,
        "ultimo_evento_id": ultimo_evento_id,
        "bytes_totales": bytes_totales,
    }
