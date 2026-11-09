"""
Servidor Backend y API REST de Control de Versiones y Auditoria para CBAS.
Sirve la interfaz web y expone endpoints rapidos para:
- Listar archivos monitoreados por departamentos en directorio_pyme/.
- Consultar el historial de versiones de cualquier archivo al instante.
- Comparar los cambios linea por linea (Diff estilo Git) entre cualquier version y su version previa o actual.
- Descargar cualquier version historica (rev) directamente al navegador sin sobrescribir el archivo local.
- Restaurar una version elegida hacia directorio_pyme/ cuando el usuario lo solicite.
- Gestionar hitos inmutables, protección de documentos auditados y compactación de micro-versiones.
- Proveer analítica de metadatos, autoguardado/edición en vivo y simulador de incidentes de resiliencia.
"""

import io
import json
from pathlib import Path
from flask import Flask, jsonify, request, render_template, send_file
from werkzeug.exceptions import HTTPException
from cbas.validation import validar_nombre, validar_revision, inferir_departamento, DEPARTAMENTOS_VALIDOS
from cbas.documents import texto_docx, MAX_DOCX_BYTES

from cbas.config import (
    MONITORED_DIR,
    obtener_metadatos_estacion,
)
from cbas.database import (
    inicializar_base_datos,
    es_archivo_texto,
    calcular_resumen_y_diff,
    registrar_nueva_version,
    listar_archivos_monitoreados,
    obtener_archivo_por_nombre,
    listar_versiones_de_archivo,
    obtener_version_especifica,
    guardar_snapshot_texto_en_version,
    listar_actividad_reciente,
    obtener_resumen_sistema,
    marcar_hito_version,
    cambiar_proteccion_archivo,
    compactar_versiones_menores,
    obtener_analitica_metadatos,
    MAX_TEXT_SNAPSHOT_BYTES,
    leer_snapshot_texto,
)
from cbas.dropbox_service import (
    verificar_cuenta_dropbox,
    descargar_bytes_version,
    restaurar_version_en_carpeta,
)
from cbas.hasher import calcular_content_hash_dropbox
from cbas.agent import (
    sincronizar_archivo_guardado,
    registrar_hash_sincronizado,
    es_archivo_temporal_o_ignorado,
    obtener_estado_sincronizacion,
    bloqueo_archivo,
    confirmar_auditoria_pendiente,
    PENDIENTES_AUDITORIA,
    obtener_nombre_relativo,
)

app = Flask(__name__, template_folder="templates")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024


@app.before_request
def validar_rutas_api():
    argumentos = request.view_args or {}
    if 'nombre_archivo' in argumentos:
        validar_nombre(argumentos['nombre_archivo'], MONITORED_DIR)
    if 'rev' in argumentos:
        validar_revision(argumentos['rev'])


@app.errorhandler(ValueError)
def error_validacion(exc):
    return jsonify(error=str(exc)), 400


@app.errorhandler(PermissionError)
def error_archivo_bloqueado(exc):
    return jsonify(error='No se puede reemplazar el archivo local. Cierra el documento en Word u otra aplicación y vuelve a restaurarlo. Si persiste, revisa los permisos de la carpeta.'), 409


@app.errorhandler(HTTPException)
def error_http(exc):
    return jsonify(error={400: 'Solicitud o JSON no válido.', 404: 'Recurso no encontrado.',
                          413: 'La solicitud excede el tamaño permitido.'}.get(exc.code, exc.name)), exc.code


@app.errorhandler(Exception)
def error_inesperado(exc):
    app.logger.error('Operación fallida: %s', type(exc).__name__)
    return jsonify(error='No se pudo completar la operación. Comprueba Dropbox y vuelve a intentar.'), 503


def entero_positivo(valor, nombre, maximo=None):
    try:
        numero = int(valor)
    except (ValueError, TypeError):
        raise ValueError(f'{nombre} debe ser un entero positivo.') from None
    if numero < 1 or (maximo and numero > maximo):
        raise ValueError(f'{nombre} está fuera del rango permitido.')
    return numero


ARCHIVOS_INICIALES_CARPETA = {
    "Contabilidad/Balance_Contable_2026.csv": (
        "fecha,codigo_cuenta,concepto,area_responsable,debe_bs,haber_bs,saldo_bs\n"
        "2026-10-01,1101-01,Apertura Caja General Octubre,Contabilidad,185000.00,0.00,185000.00\n"
        "2026-10-08,4102-04,Cobro Factura 4082 Cliente Corporativo,Ventas,64500.00,0.00,249500.00\n"
        "2026-10-15,5201-09,Pago Proveedores Materia Prima,Adquisiciones,0.00,42300.00,207200.00\n"
        "2026-10-20,5104-02,Provision Planilla Octubre 2026,Recursos Humanos,0.00,58900.00,148300.00\n"
    ),
    "Recursos_Humanos/Planilla_Sueldos_RRHH.csv": (
        "id_empleado,nombre_completo,cargo,departamento,haber_basico_bs,liquido_pagable_bs\n"
        "EMP-101,Saul Mijael Choquehuanca Huanca,Responsable de Operaciones TI,Sistemas,9800.00,9126.00\n"
        "EMP-102,Carlos Daniel Quispe Chambi,Administrador de Infraestructura,Sistemas,9500.00,8845.00\n"
        "EMP-103,Victor Bernardo Quispe Rojas,Contador General,Contabilidad,8900.00,8275.00\n"
        "EMP-104,Gabriel Yujra Machaca,Analista Administrativo,Administracion,8600.00,7980.00\n"
    ),
    "Sistemas_TI/Configuracion_ERP_Pyme.json": json.dumps(
        {
            "empresa": "Comercial Andina S.R.L.",
            "nit": "3849201015",
            "ciudad": "La Paz",
            "moneda_base": "BOB",
            "impuesto_iva_porcentaje": 13,
            "respaldo_nube_activo": True,
            "carpeta_dropbox": "/CBAS_Pyme_Vault",
        },
        indent=4,
        ensure_ascii=False,
    )
    + "\n",
    "Legal/Contratos_Proveedores_2026.md": (
        "# Registro de Contratos y Proveedores - Gestion 2026\n\n"
        "## 1. Proveedores Activos\n"
        "- Distribuidora Industrial del Sur S.A. - Vigencia: Diciembre 2026\n"
        "- Servicios Logisticos Altiplano S.R.L. - Vigencia: Noviembre 2026\n\n"
        "## 2. Condiciones de Almacenamiento Documental\n"
        "Todo cambio guardado sobre los archivos de esta carpeta se respalda en Dropbox Cloud API\n"
        "conservando el historial de versiones y permitiendo comparar o descargar versiones previas.\n"
    ),
}


def inicializar_carpeta_y_sincronizar() -> list[dict]:
    """
    Inicializa la base de datos y sincroniza todos los archivos reales presentes
    en directorio_pyme/ (incluyendo subcarpetas departamentales) hacia Dropbox.
    """
    inicializar_base_datos()
    MONITORED_DIR.mkdir(parents=True, exist_ok=True)

    archivos_existentes = [
        p for p in MONITORED_DIR.rglob("*")
        if p.is_file() and not es_archivo_temporal_o_ignorado(p)
    ]
    if not archivos_existentes:
        for rel_nombre, contenido in ARCHIVOS_INICIALES_CARPETA.items():
            ruta = MONITORED_DIR / rel_nombre
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(contenido, encoding="utf-8")

    resultados = []
    for ruta in sorted(MONITORED_DIR.rglob("*")):
        if ruta.is_file() and not es_archivo_temporal_o_ignorado(ruta):
            res = sincronizar_archivo_guardado(ruta)
            if res:
                resultados.append(res)

    return resultados


def obtener_texto_de_version(version_dict: dict) -> str | None:
    """
    Obtiene el texto de una version desde la base de datos local;
    si no estuviera en cache y el archivo es de texto, lo descarga de Dropbox por su rev y lo guarda.
    """
    es_docx = Path(version_dict['nombre_archivo']).suffix.lower() == '.docx'
    if (not version_dict.get('es_texto') and not es_docx
            or version_dict['tamano_bytes'] > (MAX_DOCX_BYTES if es_docx else MAX_TEXT_SNAPSHOT_BYTES)):
        return None
    if version_dict.get("contenido_texto") is not None:
        return version_dict["contenido_texto"]

    try:
        raw_bytes, _ = descargar_bytes_version(
            version_dict["nombre_archivo"], rev=version_dict["rev_dropbox"]
        )
        texto = texto_docx(version_dict['nombre_archivo'], raw_bytes) if es_docx else raw_bytes.decode('utf-8', errors='replace')
        if texto is not None:
            guardar_snapshot_texto_en_version(version_dict["id"], texto)
        return texto
    except Exception:
        raise RuntimeError('No se pudo recuperar el contenido de esta revisión.') from None


def analizar_metadatos_empresariales(nombre_archivo: str, texto: str | None, tamano_bytes: int) -> dict:
    """Extrae metadatos analíticos y de negocio específicos según la estructura del documento."""
    ext = Path(nombre_archivo).suffix.lower()
    metricas = {
        "tipo_archivo": ext or "sin_extension",
        "tamano_formateado": f"{tamano_bytes} bytes",
        "resumen_estructural": f"Binario ({tamano_bytes} bytes)",
    }
    if not texto:
        return metricas

    lineas = texto.splitlines()
    palabras = len(texto.split())
    metricas["total_lineas"] = len(lineas)
    metricas["total_palabras"] = palabras

    if ext == ".csv":
        try:
            import csv
            lector = list(csv.reader(lineas))
            if lector:
                columnas = len(lector[0])
                encabezados = [c.strip() for c in lector[0][:6] if c.strip()]
                filas_datos = max(0, len(lector) - 1)
                metricas["filas_datos"] = filas_datos
                metricas["columnas"] = columnas
                metricas["resumen_estructural"] = f"CSV: {filas_datos} filas x {columnas} cols ({', '.join(encabezados)})"
        except Exception:
            metricas["resumen_estructural"] = f"CSV: {len(lineas)} líneas"
    elif ext == ".json":
        try:
            parsed = json.loads(texto)
            if isinstance(parsed, dict):
                claves = list(parsed.keys())
                metricas["campos_json"] = len(claves)
                metricas["resumen_estructural"] = f"JSON válido ({len(claves)} claves: {', '.join(claves[:5])}...)"
            elif isinstance(parsed, list):
                metricas["elementos_json"] = len(parsed)
                metricas["resumen_estructural"] = f"JSON válido: arreglo de {len(parsed)} elementos"
        except Exception:
            metricas["resumen_estructural"] = "JSON (sintaxis no estándar)"
    elif ext == ".docx":
        metricas["resumen_estructural"] = f"Word: ~{palabras} palabras, {len(lineas)} párrafos"
    elif ext == ".md":
        secciones = len([l for l in lineas if l.strip().startswith('#')])
        metricas["resumen_estructural"] = f"Markdown: {secciones} secciones, ~{palabras} palabras"
    else:
        metricas["resumen_estructural"] = f"Texto: {len(lineas)} líneas, ~{palabras} palabras"

    return metricas


@app.route("/")
def vista_principal():
    return render_template("dashboard.html")


@app.route("/api/status", methods=["GET"])
def api_estado_sistema():
    resumen = obtener_resumen_sistema()
    estacion = obtener_metadatos_estacion()
    try:
        cuenta_dropbox = verificar_cuenta_dropbox()
    except Exception as exc:
        cuenta_dropbox = {
            "conectado": False,
            "error": "Comprueba las credenciales, los permisos de la aplicación y la conexión.",
            "nombre_mostrar": "Sin conexion",
            "email": "-",
        }

    return jsonify(
        {
            "resumen": resumen,
            "estacion_local": estacion,
            "dropbox": cuenta_dropbox,
            "directorio_monitoreado": str(MONITORED_DIR),
            "departamentos": DEPARTAMENTOS_VALIDOS,
            "sincronizacion": obtener_estado_sincronizacion(),
        }
    )


@app.route("/api/files", methods=["GET"])
def api_listar_archivos():
    departamento = request.args.get("departamento")
    archivos = listar_archivos_monitoreados(departamento=departamento)
    return jsonify({"archivos": archivos})


@app.route("/api/files/<path:nombre_archivo>/versions", methods=["GET"])
def api_listar_versiones_archivo(nombre_archivo: str):
    """
    Devuelve de inmediato el listado de versiones del archivo (v1, v2, v3...)
    para que la interfaz responda al instante y permita elegir cualquier version.
    """
    archivo = obtener_archivo_por_nombre(nombre_archivo)
    if not archivo:
        return jsonify({"error": "Archivo no encontrado."}), 404

    versiones = listar_versiones_de_archivo(nombre_archivo)
    return jsonify(
        {
            "nombre_archivo": nombre_archivo,
            "archivo": archivo,
            "versiones": versiones,
        }
    )


@app.route("/api/files/<path:nombre_archivo>/diff", methods=["GET"])
def api_comparar_version_archivo(nombre_archivo: str):
    """
    Devuelve el contenido y la comparacion de cambios (Diff estilo Git) de una version elegida.
    """
    versiones = listar_versiones_de_archivo(nombre_archivo)
    if not versiones:
        return jsonify({"error": "No existen versiones registradas para este archivo."}), 404

    num_solicitado = request.args.get("version")
    modo_comparacion = request.args.get("compare_to", "prev")

    if num_solicitado:
        ver_objetivo = obtener_version_especifica(nombre_archivo, numero_version=entero_positivo(num_solicitado, 'version'))
    else:
        ver_objetivo = obtener_version_especifica(
            nombre_archivo, numero_version=versiones[0]["numero_version"]
        )

    if not ver_objetivo:
        return jsonify({"error": "No se encontro la version solicitada."}), 404

    num_obj = int(ver_objetivo["numero_version"])

    ver_base = None
    if modo_comparacion == "prev":
        if num_obj > 1:
            ver_base = obtener_version_especifica(nombre_archivo, numero_version=num_obj - 1)
    elif modo_comparacion == "current":
        num_actual = int(versiones[0]["numero_version"])
        ver_base = obtener_version_especifica(nombre_archivo, numero_version=num_actual)
    else:
        ver_base = obtener_version_especifica(nombre_archivo, numero_version=entero_positivo(modo_comparacion, 'compare_to'))
        if ver_base is None:
            return jsonify(error='La versión de comparación no existe.'), 404

    es_texto = bool(ver_objetivo["es_texto"])
    es_docx = Path(nombre_archivo).suffix.lower() == '.docx'
    tiene_preview = es_texto or es_docx
    texto_objetivo = obtener_texto_de_version(ver_objetivo) if tiene_preview else None
    texto_base = obtener_texto_de_version(ver_base) if (ver_base and tiene_preview) else None

    resultado_diff = calcular_resumen_y_diff(texto_base, texto_objetivo)
    if tiene_preview and (texto_objetivo is None or (ver_base and texto_base is None)):
        resultado_diff = dict(es_texto=True, lineas_diff=[], lineas_agregadas=0,
                              lineas_eliminadas=0, resumen='Comparación no disponible: no se pudo extraer el texto completo o supera el límite.')

    return jsonify(
        {
            "nombre_archivo": nombre_archivo,
            "version_seleccionada": {
                "numero_version": ver_objetivo["numero_version"],
                "rev_dropbox": ver_objetivo["rev_dropbox"],
                "content_hash": ver_objetivo["content_hash"],
                "tamano_bytes": ver_objetivo["tamano_bytes"],
                "es_texto": es_texto,
                "es_hito": ver_objetivo.get("es_hito", 0),
                "etiqueta_hito": ver_objetivo.get("etiqueta_hito"),
                "nivel_riesgo": ver_objetivo.get("nivel_riesgo", "NORMAL"),
                "alerta_metadatos": ver_objetivo.get("alerta_metadatos"),
                "bloques_4mb_total": ver_objetivo.get("bloques_4mb_total", 1),
                "bytes_ahorrados_delta": ver_objetivo.get("bytes_ahorrados_delta", 0),
                "tipo_operacion": ver_objetivo["tipo_operacion"],
                "resumen_cambio": ver_objetivo["resumen_cambio"],
                "usuario_so": ver_objetivo["usuario_so"],
                "direccion_ip": ver_objetivo["direccion_ip"],
                "nombre_equipo": ver_objetivo["nombre_equipo"],
                "fecha_registro_utc": ver_objetivo["fecha_registro_utc"],
                "detalle_operacion": ver_objetivo["detalle_operacion"],
            },
            "version_comparada": (
                {
                    "numero_version": ver_base["numero_version"],
                    "rev_dropbox": ver_base["rev_dropbox"],
                    "fecha_registro_utc": ver_base["fecha_registro_utc"],
                }
                if ver_base
                else None
            ),
            "contenido_texto": texto_objetivo,
            "tipo_vista_previa": 'docx' if es_docx else 'texto' if es_texto else None,
            "metadatos_analiticos": analizar_metadatos_empresariales(nombre_archivo, texto_objetivo, ver_objetivo["tamano_bytes"]),
            "diff": resultado_diff,
        }
    )


@app.route("/api/files/<path:nombre_archivo>/versions/<rev>/download", methods=["GET"])
def api_descargar_version_especifica(nombre_archivo: str, rev: str):
    """
    Descarga directamente al navegador la version elegida sin sobrescribir el archivo local.
    """
    ver_local = obtener_version_especifica(nombre_archivo, rev_dropbox=rev)
    if not ver_local:
        return jsonify(error='La revisión no está registrada para este archivo.'), 404
    num_v = ver_local["numero_version"] if ver_local else "hist"

    ruta_p = Path(nombre_archivo)
    nombre_descarga = f"{ruta_p.stem}_v{num_v}_{rev[:8]}{ruta_p.suffix}"

    try:
        contenido_bytes, _ = descargar_bytes_version(nombre_archivo, rev=rev)
    except Exception as exc:
        raise RuntimeError('No se pudo descargar la versión exacta desde Dropbox.') from None

    buffer = io.BytesIO(contenido_bytes)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=nombre_descarga,
        mimetype="application/octet-stream",
    )


@app.route("/api/restore", methods=["POST"])
def api_restaurar_version():
    """
    Restaura una version seleccionada en la carpeta local directorio_pyme/ y en Dropbox.
    """
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify(error='Envía un objeto JSON válido.'), 400
    nombre_archivo = datos.get("nombre_archivo")
    rev_objetivo = datos.get("rev")
    validar_nombre(nombre_archivo, MONITORED_DIR)
    validar_revision(rev_objetivo)
    origen = obtener_version_especifica(nombre_archivo, rev_dropbox=rev_objetivo)
    if not origen:
        return jsonify(error='La revisión no está registrada para este archivo.'), 404
    if datos.get('numero_version') is not None:
        if entero_positivo(datos['numero_version'], 'numero_version') != origen['numero_version']:
            return jsonify(error='La revisión no corresponde al número de versión.'), 400
    with bloqueo_archivo(nombre_archivo):
        confirmar_auditoria_pendiente(nombre_archivo)
        return _restaurar_version(nombre_archivo, rev_objetivo, origen['numero_version'], bool(origen['es_texto']))


def _restaurar_version(nombre_archivo, rev_objetivo, num_version_origen, es_txt):
    try:
        restaurado = restaurar_version_en_carpeta(nombre_archivo, rev_objetivo)
    except PermissionError:
        raise
    except Exception as exc:
        raise RuntimeError('No se pudo restaurar desde Dropbox.') from None

    contenido = restaurado.pop('_contenido')
    texto_recuperado = (contenido.decode('utf-8', errors='replace')
                        if es_txt and len(contenido) <= MAX_TEXT_SNAPSHOT_BYTES else None)
    if Path(nombre_archivo).suffix.lower() == '.docx':
        texto_recuperado = texto_docx(nombre_archivo, contenido)

    estacion = obtener_metadatos_estacion()
    etiqueta_origen = f"v{num_version_origen} ({rev_objetivo[:10]})" if num_version_origen else rev_objetivo

    PENDIENTES_AUDITORIA[nombre_archivo] = {
        "nombre_archivo": nombre_archivo,
        "ruta_dropbox": restaurado["ruta_dropbox"],
        "dropbox_file_id": restaurado["dropbox_file_id"],
        "rev_dropbox": restaurado["nueva_rev_activa"],
        "content_hash": restaurado["content_hash"],
        "tamano_bytes": restaurado["tamano_bytes"],
        "es_texto": es_txt,
        "tipo_operacion": "RESTAURADO",
        "usuario_so": estacion["usuario_so"],
        "direccion_ip": estacion["direccion_ip"],
        "nombre_equipo": estacion["nombre_equipo"],
        "fecha_servidor_dropbox_utc": restaurado["fecha_servidor_utc"],
        "contenido_texto": texto_recuperado,
        "detalle_operacion": f"Restaurado al contenido de la version {etiqueta_origen}.",
    }
    nueva_ver = confirmar_auditoria_pendiente(nombre_archivo)

    return jsonify(
        {
            "ok": True,
            "restauracion": restaurado,
            "nueva_version": nueva_ver,
        }
    )


@app.route("/api/files/<path:nombre_archivo>/protect", methods=["POST"])
def api_proteger_archivo(nombre_archivo: str):
    """Congela o descongela un archivo para alertar sobre cualquier modificación posterior."""
    validar_nombre(nombre_archivo, MONITORED_DIR)
    datos = request.get_json(silent=True) or {}
    protegido = bool(datos.get("protegido", True))
    cambiar_proteccion_archivo(nombre_archivo, protegido)
    return jsonify({"ok": True, "nombre_archivo": nombre_archivo, "protegido": protegido})


@app.route("/api/files/<path:nombre_archivo>/versions/<int:numero_version>/milestone", methods=["POST"])
def api_fijar_hito(nombre_archivo: str, numero_version: int):
    """Marca una versión como hito auditado inmutable."""
    validar_nombre(nombre_archivo, MONITORED_DIR)
    datos = request.get_json(silent=True) or {}
    es_hito = bool(datos.get("es_hito", True))
    etiqueta = datos.get("etiqueta_hito", "Hito de Auditoría")
    marcar_hito_version(nombre_archivo, numero_version, etiqueta, es_hito)
    return jsonify({
        "ok": True,
        "nombre_archivo": nombre_archivo,
        "numero_version": numero_version,
        "es_hito": es_hito,
        "etiqueta_hito": etiqueta,
    })


@app.route("/api/files/<path:nombre_archivo>/compact", methods=["POST"])
def api_compactar_versiones(nombre_archivo: str):
    """Poda micro-guardados intermedios conservando hitos, v1, actual y restauraciones."""
    validar_nombre(nombre_archivo, MONITORED_DIR)
    datos = request.get_json(silent=True) or {}
    mantener = entero_positivo(datos.get("mantener_recientes", 3), "mantener_recientes", 50)
    resultado = compactar_versiones_menores(nombre_archivo, mantener_recientes=mantener)
    return jsonify({"ok": True, "nombre_archivo": nombre_archivo, **resultado})


@app.route("/api/files/<path:nombre_archivo>/save-content", methods=["POST"])
def api_guardar_contenido(nombre_archivo: str):
    """Guarda contenido editado o recuperado tras un apagón directamente en el archivo."""
    validar_nombre(nombre_archivo, MONITORED_DIR)
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict) or "contenido_texto" not in datos:
        return jsonify(error="Se requiere contenido_texto en el cuerpo JSON."), 400

    contenido = datos["contenido_texto"]
    ruta_local = MONITORED_DIR / nombre_archivo
    ruta_local.parent.mkdir(parents=True, exist_ok=True)
    ruta_local.write_text(contenido, encoding="utf-8")

    resultado = sincronizar_archivo_guardado(
        ruta_local, detalle_personalizado="Guardado desde la consola web (Autoguardado/Edición)"
    )
    return jsonify({"ok": True, "nombre_archivo": nombre_archivo, "resultado": resultado})


@app.route("/api/organize", methods=["POST"])
def api_organizar_departamentos():
    """Organiza automáticamente archivos sueltos de la raíz en sus subcarpetas departamentales."""
    organizados = []
    for p in list(MONITORED_DIR.iterdir()):
        if p.is_file() and not es_archivo_temporal_o_ignorado(p):
            depto = inferir_departamento(p.name)
            destino_dir = MONITORED_DIR / depto
            destino_dir.mkdir(parents=True, exist_ok=True)
            nuevo_path = destino_dir / p.name
            if not nuevo_path.exists():
                p.rename(nuevo_path)
                sincronizar_archivo_guardado(
                    nuevo_path,
                    detalle_personalizado=f"Organizado automáticamente en departamento {depto}"
                )
                organizados.append({"archivo": p.name, "nuevo_destino": f"{depto}/{p.name}"})
    return jsonify({"ok": True, "organizados": organizados, "total": len(organizados)})


@app.route("/api/analytics", methods=["GET"])
def api_analitica_metadatos():
    """Entrega métricas forenses y de rendimiento cloud para el dashboard."""
    datos = obtener_analitica_metadatos()
    return jsonify(datos)


@app.route("/api/diagnostic/integrity", methods=["GET"])
def api_diagnostico_integridad():
    """Verifica la integridad de cada archivo local comparando su hash de 4MB con el registrado en Dropbox."""
    archivos = []
    total_integros = 0
    total_discrepancias = 0

    if MONITORED_DIR.exists():
        for ruta in sorted(MONITORED_DIR.rglob("*")):
            if ruta.is_file() and not es_archivo_temporal_o_ignorado(ruta):
                rel_name = obtener_nombre_relativo(ruta)
                try:
                    hash_local = calcular_content_hash_dropbox(ruta)
                    tamano = ruta.stat().st_size
                    registro = obtener_archivo_por_nombre(rel_name)
                    if registro:
                        hash_cloud = registro.get("content_hash_actual")
                        rev_dropbox = registro.get("rev_actual")
                        version = registro.get("version_actual")
                        departamento = registro.get("departamento", "General")
                        if hash_local == hash_cloud:
                            estado = "INTEGRO"
                            total_integros += 1
                        else:
                            estado = "DISCREPANCIA"
                            total_discrepancias += 1
                    else:
                        hash_cloud = None
                        rev_dropbox = None
                        version = None
                        departamento = inferir_departamento(rel_name)
                        estado = "PENDIENTE_SINCRONIZACION"
                        total_discrepancias += 1

                    archivos.append({
                        "nombre_archivo": rel_name,
                        "departamento": departamento,
                        "estado": estado,
                        "hash_local": hash_local,
                        "hash_cloud": hash_cloud,
                        "rev_dropbox": rev_dropbox,
                        "version_actual": version,
                        "tamano_bytes": tamano,
                    })
                except Exception as e:
                    archivos.append({
                        "nombre_archivo": rel_name,
                        "departamento": inferir_departamento(rel_name),
                        "estado": "ERROR_LECTURA",
                        "error": str(e),
                    })
                    total_discrepancias += 1

    return jsonify({
        "ok": True,
        "total_archivos": len(archivos),
        "integros": total_integros,
        "discrepancias": total_discrepancias,
        "archivos": archivos,
    })


@app.route("/api/diagnostic/recovery-test", methods=["POST"])
@app.route("/api/simulator/ransomware", methods=["POST"])
def api_simulador_ransomware():
    """Prueba asistida de recuperación ante corrupción o alteración no autorizada."""
    datos = request.get_json(silent=True) or {}
    nombre_archivo = datos.get("nombre_archivo")
    modo = datos.get("modo", "alterar" if request.path.endswith("recovery-test") else "simular")
    if modo == "alterar":
        modo = "simular"
    elif modo == "restaurar":
        modo = "rollback"

    if not nombre_archivo:
        archivos = listar_archivos_monitoreados()
        if not archivos:
            return jsonify(error="No hay archivos disponibles para la prueba de recuperación."), 400
        nombre_archivo = archivos[0]["nombre_archivo"]

    validar_nombre(nombre_archivo, MONITORED_DIR)
    ruta_local = MONITORED_DIR / nombre_archivo

    if modo == "simular":
        payload_malicioso = (
            "=== LOCKBIT_ENCRYPTED_FILE ===\n"
            "Todos sus archivos han sido cifrados por una clave RSA-4096.\n"
            "No intente recuperar sus datos manualmente.\n"
            "ID de rescate: 0xDEADBEEF2026\n"
            "=== FIN DE CIFRADO MALICIOSO ==="
        )
        ruta_local.parent.mkdir(parents=True, exist_ok=True)
        ruta_local.write_text(payload_malicioso, encoding="utf-8")
        sincronizado = sincronizar_archivo_guardado(
            ruta_local,
            tipo_operacion_forzada="MODIFICADO",
            detalle_personalizado="[PRUEBA DE RECUPERACIÓN] Archivo alterado con firma de prueba (LOCKBIT)"
        )
        return jsonify({
            "ok": True,
            "modo": "simular",
            "nombre_archivo": nombre_archivo,
            "mensaje": f"Archivo {nombre_archivo} alterado controladamente con firma de prueba. Se generó registro de auditoría.",
            "resultado": sincronizado
        })
    elif modo == "rollback":
        versiones = listar_versiones_de_archivo(nombre_archivo)
        if len(versiones) < 2:
            return jsonify(error="Se requieren al menos 2 versiones para ejecutar la recuperación."), 400
        version_limpia = None
        for v in versiones[1:]:
            if v.get("nivel_riesgo") != "CRITICO":
                version_limpia = v
                break
        if not version_limpia:
            version_limpia = versiones[-1]

        with bloqueo_archivo(nombre_archivo):
            confirmar_auditoria_pendiente(nombre_archivo)
            resultado_restore = _restaurar_version(
                nombre_archivo,
                version_limpia["rev_dropbox"],
                version_limpia["numero_version"],
                bool(version_limpia["es_texto"])
            )
        return jsonify({
            "ok": True,
            "modo": "rollback",
            "nombre_archivo": nombre_archivo,
            "version_restaurada": version_limpia["numero_version"],
            "mensaje": f"Recuperación ejecutada con éxito. Se restauró en disco la versión limpia v{version_limpia['numero_version']}.",
            "detalle": resultado_restore.get_json() if hasattr(resultado_restore, 'get_json') else resultado_restore
        })
    else:
        return jsonify(error="Modo desconocido (use 'alterar'/'simular' o 'restaurar'/'rollback')."), 400


@app.route("/api/activity", methods=["GET"])
def api_registro_actividad():
    archivo = request.args.get("archivo")
    departamento = request.args.get("departamento")
    nivel_riesgo = request.args.get("nivel_riesgo")
    if archivo:
        validar_nombre(archivo, MONITORED_DIR)
    limite = entero_positivo(request.args.get("limite", "100"), 'limite', 1000)
    eventos = listar_actividad_reciente(
        limite=limite,
        nombre_archivo=archivo,
        departamento=departamento,
        nivel_riesgo=nivel_riesgo
    )
    return jsonify({"eventos": eventos})
