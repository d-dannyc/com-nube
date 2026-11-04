"""Validación compartida de nombres de archivos, rutas departamentales y revisiones."""
from pathlib import Path, PurePosixPath
import re

DEPARTAMENTOS_VALIDOS = ["Contabilidad", "Recursos_Humanos", "Legal", "Sistemas_TI", "General"]


def inferir_departamento(ruta_relativa: str) -> str:
    """Infiere el departamento al que pertenece un archivo según su carpeta o nombre."""
    ruta_norm = str(ruta_relativa).replace("\\", "/").strip("/")
    if "/" in ruta_norm:
        primer_segmento = ruta_norm.split("/")[0].strip()
        for depto in DEPARTAMENTOS_VALIDOS:
            if primer_segmento.lower() == depto.lower():
                return depto
        return primer_segmento.replace(" ", "_")

    nombre_bajo = Path(ruta_norm).name.lower()
    if any(k in nombre_bajo for k in ["balance", "contab", "factura", "asiento", "iva", "libro", "fiscal"]):
        return "Contabilidad"
    if any(k in nombre_bajo for k in ["sueldo", "planilla", "rrhh", "empleado", "nomina", "personal"]):
        return "Recursos_Humanos"
    if any(k in nombre_bajo for k in ["contrato", "acta", "legal", "proveedor", "licencia", "nda", "acuerdo"]):
        return "Legal"
    if any(k in nombre_bajo for k in ["erp", "config", "sistema", "it", "red", "backup", ".json", ".sql", ".py", ".sh"]):
        return "Sistemas_TI"
    return "General"


def validar_nombre(nombre: str, carpeta: Path | None = None) -> str:
    if not isinstance(nombre, str) or not nombre.strip():
        raise ValueError('Indica un nombre de archivo válido.')

    nombre_norm = nombre.replace('\\', '/')
    if nombre_norm.startswith('/') or any(ord(c) < 32 for c in nombre) or ':' in nombre:
        raise ValueError('Ruta de archivo no válida.')

    partes = PurePosixPath(nombre_norm).parts
    if not partes or any(p in {'.', '..', ''} for p in partes):
        raise ValueError('Ruta de archivo no válida, no se permiten referencias relativas ni vacías.')

    if len(partes) > 2:
        raise ValueError('Estructura máxima permitida: Departamento/Archivo.')

    for p in partes:
        if p.endswith(('.', ' ')):
            raise ValueError('Los nombres de archivo o carpeta no pueden terminar en punto o espacio.')

    if carpeta is not None:
        destino = (carpeta / nombre_norm).resolve()
        carpeta_res = carpeta.resolve()
        if not (destino == carpeta_res or carpeta_res in destino.parents) or destino.is_symlink():
            raise ValueError('El archivo debe estar dentro de la carpeta monitoreada.')

    return nombre_norm


def validar_revision(rev: str) -> str:
    if not isinstance(rev, str) or not re.fullmatch(r'[a-fA-F0-9]{1,128}', rev):
        raise ValueError('La revisión de Dropbox no es válida.')
    return rev
