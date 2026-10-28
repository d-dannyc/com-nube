"""Validación compartida de nombres de primer nivel y revisiones."""
from pathlib import Path
import re


def validar_nombre(nombre: str, carpeta: Path | None = None) -> str:
    if (not isinstance(nombre, str) or not nombre.strip() or nombre in {'.', '..'}
            or any(c in nombre for c in '/\\:') or any(ord(c) < 32 for c in nombre)
            or nombre.endswith(('.', ' '))):
        raise ValueError('Indica un nombre de archivo válido, sin rutas ni subcarpetas.')
    if carpeta is not None:
        destino = carpeta / nombre
        if destino.is_symlink() or destino.resolve().parent != carpeta.resolve():
            raise ValueError('El archivo debe estar dentro de la carpeta monitoreada.')
    return nombre


def validar_revision(rev: str) -> str:
    if not isinstance(rev, str) or not re.fullmatch(r'[a-fA-F0-9]{1,128}', rev):
        raise ValueError('La revisión de Dropbox no es válida.')
    return rev
