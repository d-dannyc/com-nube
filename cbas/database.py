"""
Capa de persistencia de metadatos y control de versiones para CBAS.
Almacena el inventario de archivos de la carpeta monitoreada, el historial de versiones
asociado a los identificadores rev de Dropbox y las instantaneas de texto para calcular
comparaciones de cambios (Diff estilo Git) de forma instantanea.
Incorpora inteligencia de metadatos, clasificación departamental, hitos inmutables y
análisis forense de integridad.
"""

import difflib
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from cbas.config import DATABASE_PATH
from cbas.validation import inferir_departamento

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
DROPBOX_BLOCK_SIZE = 4 * 1024 * 1024  # 4 MB exactos


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


def _asegurar_esquema(conn: sqlite3.Connection) -> None:
    """Garantiza la presencia de columnas avanzadas en bases de datos existentes."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(archivos_monitoreados)")
    cols_archivos = {row["name"] for row in cursor.fetchall()}
    if "departamento" not in cols_archivos:
        cursor.execute("ALTER TABLE archivos_monitoreados ADD COLUMN departamento TEXT NOT NULL DEFAULT 'General'")
    if "protegido" not in cols_archivos:
        cursor.execute("ALTER TABLE archivos_monitoreados ADD COLUMN protegido INTEGER NOT NULL DEFAULT 0")

    cursor.execute("PRAGMA table_info(versiones_archivo)")
    cols_versiones = {row["name"] for row in cursor.fetchall()}
    if "departamento" not in cols_versiones:
        cursor.execute("ALTER TABLE versiones_archivo ADD COLUMN departamento TEXT NOT NULL DEFAULT 'General'")
    if "es_hito" not in cols_versiones:
        cursor.execute("ALTER TABLE versiones_archivo ADD COLUMN es_hito INTEGER NOT NULL DEFAULT 0")
    if "etiqueta_hito" not in cols_versiones:
        cursor.execute("ALTER TABLE versiones_archivo ADD COLUMN etiqueta_hito TEXT")
    if "nivel_riesgo" not in cols_versiones:
        cursor.execute("ALTER TABLE versiones_archivo ADD COLUMN nivel_riesgo TEXT NOT NULL DEFAULT 'NORMAL'")
    if "alerta_metadatos" not in cols_versiones:
        cursor.execute("ALTER TABLE versiones_archivo ADD COLUMN alerta_metadatos TEXT")
    if "bloques_4mb_total" not in cols_versiones:
        cursor.execute("ALTER TABLE versiones_archivo ADD COLUMN bloques_4mb_total INTEGER NOT NULL DEFAULT 1")
    if "bytes_ahorrados_delta" not in cols_versiones:
        cursor.execute("ALTER TABLE versiones_archivo ADD COLUMN bytes_ahorrados_delta INTEGER NOT NULL DEFAULT 0")


def inicializar_base_datos() -> None:
    """Crea las tablas de archivos monitoreados y versiones si no existen y asegura migraciones."""
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS archivos_monitoreados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_archivo TEXT NOT NULL UNIQUE,
                extension TEXT NOT NULL,
                es_texto INTEGER NOT NULL DEFAULT 1,
                departamento TEXT NOT NULL DEFAULT 'General',
                protegido INTEGER NOT NULL DEFAULT 0,
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
                departamento TEXT NOT NULL DEFAULT 'General',
                numero_version INTEGER NOT NULL,
                ruta_dropbox TEXT NOT NULL,
                rev_dropbox TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                tamano_bytes INTEGER NOT NULL,
                es_texto INTEGER NOT NULL DEFAULT 1,
                es_hito INTEGER NOT NULL DEFAULT 0,
                etiqueta_hito TEXT,
                nivel_riesgo TEXT NOT NULL DEFAULT 'NORMAL',
                alerta_metadatos TEXT,
                bloques_4mb_total INTEGER NOT NULL DEFAULT 1,
                bytes_ahorrados_delta INTEGER NOT NULL DEFAULT 0,
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
        _asegurar_esquema(conn)
        conn.commit()


def evaluar_riesgo_y_metadatos(nombre_archivo: str, contenido_texto: str | None,
                               tamano_bytes: int, bytes_previos: int,
                               es_protegido: bool, tipo_operacion: str) -> tuple[str, str | None]:
    """Evalúa anomalías de integridad, firmas maliciosas o violaciones de documentos congelados."""
    if tipo_operacion == "RESTAURADO":
        return "NORMAL", None

    if es_protegido and tipo_operacion not in ("CREADO", "RESTAURADO"):
        return "CRITICO", "ALERTA DE SEGURIDAD: Modificación no autorizada sobre documento congelado/auditado."

    if contenido_texto:
        texto_upper = contenido_texto.upper()
        if "LOCKBIT" in texto_upper or "ENCRYPTED" in texto_upper or "RANSOMWARE" in texto_upper:
            return "CRITICO", "ALERTA FORENSE: Firma o patrón de cifrado Ransomware detectado en el contenido."

    if bytes_previos > 1024 and tamano_bytes < (bytes_previos * 0.25):
        return "ADVERTENCIA", f"ADVERTENCIA DE INTEGRIDAD: Reducción abrupta de más del 75% del contenido ({tamano_bytes} vs {bytes_previos} bytes)."

    return "NORMAL", None


def registrar_nueva_version(datos: dict) -> dict:
    """
    Registra una nueva version de un archivo en la tabla versiones_archivo,
    calcula automaticamente las lineas agregadas/eliminadas, evalua riesgos,
    y actualiza el registro principal en archivos_monitoreados.
    """
    ahora_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    nombre_archivo = datos["nombre_archivo"]
    extension = Path(nombre_archivo).suffix.lower() or "sin_ext"
    departamento = datos.get("departamento") or inferir_departamento(nombre_archivo)
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

        cursor.execute(
            "SELECT id, protegido FROM archivos_monitoreados WHERE nombre_archivo = ?",
            (nombre_archivo,),
        )
        existente = cursor.fetchone()
        archivo_protegido = bool(existente["protegido"]) if existente else False

        if ultima_version_row is None:
            nuevo_num_version = 1
            texto_previo = None
            bytes_previos = 0
        else:
            nuevo_num_version = int(ultima_version_row["numero_version"]) + 1
            texto_previo = ultima_version_row["contenido_texto"]
            bytes_previos = int(ultima_version_row["tamano_bytes"])

        # Evaluación de riesgo y anomalías en metadatos
        nivel_riesgo, alerta_metadatos = evaluar_riesgo_y_metadatos(
            nombre_archivo, contenido_texto, tamano_bytes, bytes_previos,
            archivo_protegido, tipo_operacion
        )

        # Métricas de bloques de 4 MB y ahorro Delta Sync
        bloques_4mb = max(1, (tamano_bytes + DROPBOX_BLOCK_SIZE - 1) // DROPBOX_BLOCK_SIZE)
        if tipo_operacion == "MODIFICADO" and bytes_previos > 0:
            if tamano_bytes > DROPBOX_BLOCK_SIZE:
                ahorro_delta = max(0, tamano_bytes - DROPBOX_BLOCK_SIZE)
            else:
                ahorro_delta = max(0, abs(tamano_bytes - bytes_previos))
        else:
            ahorro_delta = 0

        if contenido_texto is not None and (es_texto_bool or extension == '.docx'):
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
                nombre_archivo, departamento, numero_version, ruta_dropbox, rev_dropbox, content_hash,
                tamano_bytes, es_texto, es_hito, etiqueta_hito, nivel_riesgo, alerta_metadatos,
                bloques_4mb_total, bytes_ahorrados_delta, tipo_operacion, lineas_agregadas, lineas_eliminadas,
                resumen_cambio, usuario_so, direccion_ip, nombre_equipo,
                fecha_servidor_dropbox_utc, fecha_registro_utc, detalle_operacion, contenido_texto
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nombre_archivo,
                departamento,
                nuevo_num_version,
                ruta_dropbox,
                rev_dropbox,
                content_hash,
                tamano_bytes,
                1 if es_texto_bool else 0,
                1 if datos.get("es_hito") else 0,
                datos.get("etiqueta_hito"),
                nivel_riesgo,
                alerta_metadatos,
                bloques_4mb,
                ahorro_delta,
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

        if existente:
            cursor.execute(
                """
                UPDATE archivos_monitoreados
                SET extension = ?,
                    es_texto = ?,
                    departamento = ?,
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
                    departamento,
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
                    nombre_archivo, extension, es_texto, departamento, protegido, ruta_dropbox, dropbox_file_id,
                    version_actual, rev_actual, content_hash_actual, tamano_bytes,
                    estado_archivo, ultimo_usuario_so, ultima_ip, ultimo_equipo,
                    ultima_modificacion_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    nombre_archivo,
                    extension,
                    1 if es_texto_bool else 0,
                    departamento,
                    1 if datos.get("protegido") else 0,
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
        "departamento": departamento,
        "numero_version": nuevo_num_version,
        "rev_dropbox": rev_dropbox,
        "nivel_riesgo": nivel_riesgo,
        "alerta_metadatos": alerta_metadatos,
        "resumen_cambio": resumen_cambio,
        "fecha_registro_utc": ahora_utc,
    }


def marcar_hito_version(nombre_archivo: str, numero_version: int, etiqueta: str | None = None, es_hito: bool = True) -> bool:
    """Fija o desfija una versión clave como Hito inmutable que no puede ser purgado."""
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE versiones_archivo
            SET es_hito = ?, etiqueta_hito = ?
            WHERE nombre_archivo = ? AND numero_version = ?
            """,
            (1 if es_hito else 0, etiqueta, nombre_archivo, int(numero_version))
        )
        conn.commit()
        return cursor.rowcount > 0


def cambiar_proteccion_archivo(nombre_archivo: str, protegido: bool) -> bool:
    """Bloquea o desbloquea un archivo auditado para alertar sobre alteraciones no autorizadas."""
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE archivos_monitoreados SET protegido = ? WHERE nombre_archivo = ?",
            (1 if protegido else 0, nombre_archivo)
        )
        conn.commit()
        return cursor.rowcount > 0


def compactar_versiones_menores(nombre_archivo: str, mantener_recientes: int = 3) -> dict:
    """
    Poda micro-versiones intermedias locales sin valor legal.
    Protege siempre: v1, versión actual, hitos, restauraciones y alertas críticas.
    """
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, numero_version, es_hito, tipo_operacion, nivel_riesgo
            FROM versiones_archivo
            WHERE nombre_archivo = ?
            ORDER BY numero_version DESC
            """,
            (nombre_archivo,)
        )
        filas = cursor.fetchall()
        if not filas:
            return {"versiones_eliminadas": 0, "versiones_restantes": 0}

        max_version = filas[0]["numero_version"]
        recientes_ids = {f["id"] for f in filas[:mantener_recientes]}

        eliminables = []
        for f in filas:
            vid = f["id"]
            num = f["numero_version"]
            # Proteger v1 y la versión actual
            if num == 1 or num == max_version:
                continue
            # Proteger las N versiones más recientes
            if vid in recientes_ids:
                continue
            # Proteger Hitos
            if f["es_hito"] == 1:
                continue
            # Proteger Restauraciones y Alertas Críticas
            if f["tipo_operacion"] == "RESTAURADO" or f["nivel_riesgo"] == "CRITICO":
                continue
            eliminables.append(vid)

        if eliminables:
            placeholders = ",".join("?" * len(eliminables))
            cursor.execute(f"DELETE FROM versiones_archivo WHERE id IN ({placeholders})", eliminables)
            conn.commit()

        restantes = len(filas) - len(eliminables)
        return {"versiones_eliminadas": len(eliminables), "versiones_restantes": restantes}


def listar_archivos_monitoreados(departamento: str | None = None) -> list[dict]:
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        if departamento and departamento != "Todos":
            cursor.execute(
                "SELECT * FROM archivos_monitoreados WHERE departamento = ? ORDER BY nombre_archivo ASC",
                (departamento,)
            )
        else:
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
            SELECT id, nombre_archivo, departamento, numero_version, ruta_dropbox, rev_dropbox,
                   content_hash, tamano_bytes, es_texto, es_hito, etiqueta_hito,
                   nivel_riesgo, alerta_metadatos, bloques_4mb_total, bytes_ahorrados_delta,
                   tipo_operacion, lineas_agregadas, lineas_eliminadas, resumen_cambio,
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


def listar_actividad_reciente(limite: int = 100, nombre_archivo: str | None = None, departamento: str | None = None, nivel_riesgo: str | None = None) -> list[dict]:
    with obtener_conexion() as conn:
        cursor = conn.cursor()
        condiciones = []
        params = []
        if nombre_archivo:
            condiciones.append("nombre_archivo = ?")
            params.append(nombre_archivo)
        if departamento and departamento != "Todos":
            condiciones.append("departamento = ?")
            params.append(departamento)
        if nivel_riesgo and nivel_riesgo != "Todos":
            condiciones.append("nivel_riesgo = ?")
            params.append(nivel_riesgo)

        where_clause = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
        query = f"""
            SELECT id, nombre_archivo, departamento, numero_version, ruta_dropbox, rev_dropbox,
                   content_hash, tamano_bytes, tipo_operacion, resumen_cambio, es_hito, etiqueta_hito,
                   nivel_riesgo, alerta_metadatos, usuario_so, direccion_ip, nombre_equipo,
                   fecha_registro_utc, detalle_operacion
            FROM versiones_archivo
            {where_clause}
            ORDER BY id DESC LIMIT ?
        """
        params.append(limite)
        cursor.execute(query, params)
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

        cursor.execute("SELECT COUNT(*) as total FROM versiones_archivo WHERE es_hito = 1")
        total_hitos = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as total FROM versiones_archivo WHERE nivel_riesgo != 'NORMAL'")
        total_alertas = cursor.fetchone()["total"]

        cursor.execute("SELECT COALESCE(MAX(id), 0) as ultimo_evento_id FROM versiones_archivo")
        ultimo_evento_id = cursor.fetchone()["ultimo_evento_id"]

        cursor.execute("SELECT COALESCE(SUM(tamano_bytes), 0) as bytes_totales FROM archivos_monitoreados")
        bytes_totales = cursor.fetchone()["bytes_totales"]

        cursor.execute("SELECT COALESCE(SUM(bytes_ahorrados_delta), 0) as ahorro_total FROM versiones_archivo")
        ahorro_delta_bytes = cursor.fetchone()["ahorro_total"]

    return {
        "total_archivos": total_archivos,
        "total_versiones": total_versiones,
        "total_restauraciones": total_restauraciones,
        "total_hitos": total_hitos,
        "total_alertas": total_alertas,
        "ultimo_evento_id": ultimo_evento_id,
        "bytes_totales": bytes_totales,
        "ahorro_delta_bytes": ahorro_delta_bytes,
    }


def obtener_analitica_metadatos() -> dict:
    """Calcula estadísticas forenses y métricas de cloud computing basadas en metadatos."""
    with obtener_conexion() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT departamento, COUNT(*) as total_archivos, SUM(tamano_bytes) as total_bytes FROM archivos_monitoreados GROUP BY departamento"
        )
        departamentos = [dict(r) for r in cursor.fetchall()]

        cursor.execute(
            "SELECT nivel_riesgo, COUNT(*) as total FROM versiones_archivo GROUP BY nivel_riesgo"
        )
        riesgos = {r["nivel_riesgo"]: r["total"] for r in cursor.fetchall()}

        cursor.execute(
            "SELECT usuario_so, COUNT(*) as eventos FROM versiones_archivo GROUP BY usuario_so ORDER BY eventos DESC LIMIT 5"
        )
        usuarios = [dict(r) for r in cursor.fetchall()]

        cursor.execute(
            "SELECT direccion_ip, nombre_equipo, COUNT(*) as eventos FROM versiones_archivo GROUP BY direccion_ip, nombre_equipo ORDER BY eventos DESC LIMIT 5"
        )
        equipos = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) as total FROM versiones_archivo WHERE es_hito = 1")
        total_hitos = cursor.fetchone()["total"]

        cursor.execute("SELECT COALESCE(SUM(bytes_ahorrados_delta), 0) as ahorro_total FROM versiones_archivo")
        ahorro_delta_bytes = cursor.fetchone()["ahorro_total"]

        cursor.execute("SELECT COUNT(*) as total FROM archivos_monitoreados WHERE protegido = 1")
        total_protegidos = cursor.fetchone()["total"]

        cursor.execute(
            """
            SELECT nombre_archivo, departamento, numero_version, nivel_riesgo, alerta_metadatos, fecha_registro_utc, usuario_so, direccion_ip
            FROM versiones_archivo
            WHERE nivel_riesgo != 'NORMAL'
            ORDER BY id DESC LIMIT 10
            """
        )
        alertas_recientes = [dict(r) for r in cursor.fetchall()]

        return {
            "departamentos": departamentos,
            "riesgos": {
                "normal": riesgos.get("NORMAL", 0),
                "advertencia": riesgos.get("ADVERTENCIA", 0),
                "critico": riesgos.get("CRITICO", 0),
            },
            "usuarios": usuarios,
            "equipos": equipos,
            "total_hitos": total_hitos,
            "total_protegidos": total_protegidos,
            "ahorro_delta_bytes": ahorro_delta_bytes,
            "alertas_recientes": alertas_recientes,
        }
