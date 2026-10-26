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
)

app = Flask(__name__, template_folder="templates")

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
    if not version_dict.get("es_texto"):
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
        return None


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
            "error": str(exc),
            "nombre_mostrar": "Sin conexion",
            "email": "-",
        }

    return jsonify(
        {
            "resumen": resumen,
            "estacion_local": estacion,
            "dropbox": cuenta_dropbox,
            "directorio_monitoreado": str(MONITORED_DIR),
        }
    )


@app.route("/api/files", methods=["GET"])
def api_listar_archivos():
    # Escaneo rapido por si se agrego un archivo nuevo a directorio_pyme
    if MONITORED_DIR.exists():
        for ruta in sorted(MONITORED_DIR.iterdir()):
            if ruta.is_file() and not es_archivo_temporal_o_ignorado(ruta):
                if obtener_archivo_por_nombre(ruta.name) is None:
                    try:
                        sincronizar_archivo_guardado(ruta)
                    except Exception:
                        pass

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
        ver_objetivo = obtener_version_especifica(nombre_archivo, numero_version=int(num_solicitado))
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
        if num_actual != num_obj:
            ver_base = obtener_version_especifica(nombre_archivo, numero_version=num_actual)
    else:
        try:
            ver_base = obtener_version_especifica(nombre_archivo, numero_version=int(modo_comparacion))
        except ValueError:
            ver_base = None

    es_texto = bool(ver_objetivo["es_texto"])
    texto_objetivo = obtener_texto_de_version(ver_objetivo) if es_texto else None
    texto_base = obtener_texto_de_version(ver_base) if (ver_base and es_texto) else None

    resultado_diff = calcular_resumen_y_diff(texto_base, texto_objetivo)

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
    num_v = ver_local["numero_version"] if ver_local else "hist"

    ruta_p = Path(nombre_archivo)
    nombre_descarga = f"{ruta_p.stem}_v{num_v}_{rev[:8]}{ruta_p.suffix}"

    # Si tenemos la instantanea exacta en base de datos para texto, o bien descargamos de Dropbox
    try:
        contenido_bytes, _ = descargar_bytes_version(nombre_archivo, rev=rev)
    except Exception as exc:
        if ver_local and ver_local.get("contenido_texto") is not None:
            contenido_bytes = ver_local["contenido_texto"].encode("utf-8")
        else:
            return jsonify({"error": f"No se pudo descargar la version desde Dropbox: {exc}"}), 500

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
    datos = request.get_json(force=True)
    nombre_archivo = datos.get("nombre_archivo")
    rev_objetivo = datos.get("rev")
    num_version_origen = datos.get("numero_version")

    if not nombre_archivo or not rev_objetivo:
        return jsonify({"error": "Debe indicar nombre_archivo y rev."}), 400

    try:
        restaurado = restaurar_version_en_carpeta(nombre_archivo, rev_objetivo)
    except Exception as exc:
        return jsonify({"error": f"Error al restaurar desde Dropbox API: {exc}"}), 500

    # Registrar el nuevo content_hash para que Watchdog no duplique el evento
    registrar_hash_sincronizado(nombre_archivo, restaurado["content_hash"])

    ruta_local = MONITORED_DIR / nombre_archivo
    es_txt = es_archivo_texto(ruta_local)
    texto_recuperado = (
        ruta_local.read_text(encoding="utf-8", errors="replace") if es_txt else None
    )

    estacion = obtener_metadatos_estacion()
    etiqueta_origen = f"v{num_version_origen} ({rev_objetivo[:10]})" if num_version_origen else rev_objetivo

    nueva_ver = registrar_nueva_version(
        {
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
    )

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
    limite = int(request.args.get("limite", "100"))
    eventos = listar_actividad_reciente(limite=limite, nombre_archivo=archivo)
    return jsonify({"eventos": eventos})
