"""
Servidor Backend y API REST de Control de Versiones y Auditoria para CBAS.
Sirve la interfaz web y expone endpoints rapidos para:
- Listar archivos monitoreados en directorio_pyme/.
- Consultar el historial de versiones de cualquier archivo al instante.
- Comparar los cambios linea por linea (Diff estilo Git) entre cualquier version y su version previa o actual.
- Descargar cualquier version historica (rev) directamente al navegador sin sobrescribir el archivo local.
- Restaurar una version elegida hacia directorio_pyme/ cuando el usuario lo solicite.
"""

import io
import json
from pathlib import Path
from flask import Flask, jsonify, request, render_template, send_file
from werkzeug.exceptions import HTTPException
from cbas.validation import validar_nombre, validar_revision

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
    MAX_TEXT_SNAPSHOT_BYTES,
    leer_snapshot_texto,
)
from cbas.dropbox_service import (
    verificar_cuenta_dropbox,
    descargar_bytes_version,
    restaurar_version_en_carpeta,
)
from cbas.agent import (
    sincronizar_archivo_guardado,
    registrar_hash_sincronizado,
    es_archivo_temporal_o_ignorado,
    obtener_estado_sincronizacion,
    bloqueo_archivo,
    confirmar_auditoria_pendiente,
    PENDIENTES_AUDITORIA,
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
    "Balance_Contable_2026.csv": (
        "fecha,codigo_cuenta,concepto,area_responsable,debe_bs,haber_bs,saldo_bs\n"
        "2026-10-01,1101-01,Apertura Caja General Octubre,Contabilidad,185000.00,0.00,185000.00\n"
        "2026-10-08,4102-04,Cobro Factura 4082 Cliente Corporativo,Ventas,64500.00,0.00,249500.00\n"
        "2026-10-15,5201-09,Pago Proveedores Materia Prima,Adquisiciones,0.00,42300.00,207200.00\n"
        "2026-10-20,5104-02,Provision Planilla Octubre 2026,Recursos Humanos,0.00,58900.00,148300.00\n"
    ),
    "Planilla_Sueldos_RRHH.csv": (
        "id_empleado,nombre_completo,cargo,departamento,haber_basico_bs,liquido_pagable_bs\n"
        "EMP-101,Saul Mijael Choquehuanca Huanca,Responsable de Operaciones TI,Sistemas,9800.00,9126.00\n"
        "EMP-102,Carlos Daniel Quispe Chambi,Administrador de Infraestructura,Sistemas,9500.00,8845.00\n"
        "EMP-103,Victor Bernardo Quispe Rojas,Contador General,Contabilidad,8900.00,8275.00\n"
        "EMP-104,Gabriel Yujra Machaca,Analista Administrativo,Administracion,8600.00,7980.00\n"
    ),
    "Configuracion_ERP_Pyme.json": json.dumps(
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
    "Contratos_Proveedores_2026.md": (
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
    en directorio_pyme/ hacia Dropbox.
    """
    inicializar_base_datos()
    MONITORED_DIR.mkdir(parents=True, exist_ok=True)

    archivos_existentes = [
        p for p in MONITORED_DIR.iterdir()
        if p.is_file() and not es_archivo_temporal_o_ignorado(p)
    ]
    if not archivos_existentes:
        for nombre, contenido in ARCHIVOS_INICIALES_CARPETA.items():
            ruta = MONITORED_DIR / nombre
            ruta.write_text(contenido, encoding="utf-8")

    resultados = []
    for ruta in sorted(MONITORED_DIR.iterdir()):
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
    if (not version_dict.get("es_texto")
            or version_dict['tamano_bytes'] > MAX_TEXT_SNAPSHOT_BYTES):
        return None
    if version_dict.get("contenido_texto") is not None:
        return version_dict["contenido_texto"]

    try:
        raw_bytes, _ = descargar_bytes_version(
            version_dict["nombre_archivo"], rev=version_dict["rev_dropbox"]
        )
        texto = raw_bytes.decode("utf-8", errors="replace")
        guardar_snapshot_texto_en_version(version_dict["id"], texto)
        return texto
    except Exception:
        raise RuntimeError('No se pudo recuperar el contenido de esta revisión.') from None


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
            "sincronizacion": obtener_estado_sincronizacion(),
        }
    )


@app.route("/api/files", methods=["GET"])
def api_listar_archivos():
    archivos = listar_archivos_monitoreados()
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
    Parametros opcionales:
    - version: numero_version a inspeccionar (por defecto la version mas reciente).
    - compare_to: 'prev' (version inmediata anterior, por defecto), 'current' (version actual),
                  o un numero de version especifico.
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

    # Determinar contra que version comparar
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
    texto_objetivo = obtener_texto_de_version(ver_objetivo) if es_texto else None
    texto_base = obtener_texto_de_version(ver_base) if (ver_base and es_texto) else None

    resultado_diff = calcular_resumen_y_diff(texto_base, texto_objetivo)
    if es_texto and (texto_objetivo is None or (ver_base and texto_base is None)):
        resultado_diff = dict(es_texto=True, lineas_diff=[], lineas_agregadas=0,
                              lineas_eliminadas=0, resumen='Comparación no disponible: límite de 512 KiB.')

    return jsonify(
        {
            "nombre_archivo": nombre_archivo,
            "version_seleccionada": {
                "numero_version": ver_objetivo["numero_version"],
                "rev_dropbox": ver_objetivo["rev_dropbox"],
                "content_hash": ver_objetivo["content_hash"],
                "tamano_bytes": ver_objetivo["tamano_bytes"],
                "es_texto": es_texto,
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
            "diff": resultado_diff,
        }
    )


@app.route("/api/files/<path:nombre_archivo>/versions/<rev>/download", methods=["GET"])
def api_descargar_version_especifica(nombre_archivo: str, rev: str):
    """
    Descarga directamente al navegador la version elegida (identificada por rev)
    sin necesidad de restaurarla ni sobrescribir el archivo local en directorio_pyme/.
    """
    ver_local = obtener_version_especifica(nombre_archivo, rev_dropbox=rev)
    if not ver_local:
        return jsonify(error='La revisión no está registrada para este archivo.'), 404
    num_v = ver_local["numero_version"] if ver_local else "hist"

    ruta_p = Path(nombre_archivo)
    nombre_descarga = f"{ruta_p.stem}_v{num_v}_{rev[:8]}{ruta_p.suffix}"

    # Si tenemos la instantanea exacta en base de datos para texto, o bien descargamos de Dropbox
    try:
        contenido_bytes, _ = descargar_bytes_version(nombre_archivo, rev=rev)
    except Exception as exc:
        # Una instantánea UTF-8 puede no conservar los bytes originales.
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
    except Exception as exc:
        raise RuntimeError('No se pudo restaurar desde Dropbox.') from None

    contenido = restaurado.pop('_contenido')
    texto_recuperado = (contenido.decode('utf-8', errors='replace')
                        if es_txt and len(contenido) <= MAX_TEXT_SNAPSHOT_BYTES else None)

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


@app.route("/api/activity", methods=["GET"])
def api_registro_actividad():
    archivo = request.args.get("archivo")
    if archivo:
        validar_nombre(archivo)
    limite = entero_positivo(request.args.get("limite", "100"), 'limite', 1000)
    eventos = listar_actividad_reciente(limite=limite, nombre_archivo=archivo)
    return jsonify({"eventos": eventos})
