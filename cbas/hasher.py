"""
Modulo de calculo criptografico de integridad compatible con Dropbox API v2.
Implementa el algoritmo oficial content_hash de Dropbox:
Divide el archivo en bloques de 4 MB, calcula el digest SHA-256 de cada bloque,
concatena los digests binarios y calcula el SHA-256 final en hexadecimal.
"""

import hashlib
from pathlib import Path

DROPBOX_BLOCK_SIZE = 4 * 1024 * 1024  # 4 MB exactos (4,194,304 bytes)


def calcular_content_hash_dropbox(ruta_archivo: str | Path) -> str:
    """Calcula el content_hash oficial de Dropbox para verificar integridad sin transferir el archivo."""
    hashes_bloques = bytearray()
    with open(ruta_archivo, "rb") as archivo:
        while True:
            bloque = archivo.read(DROPBOX_BLOCK_SIZE)
            if not bloque:
                break
            hashes_bloques.extend(hashlib.sha256(bloque).digest())
    return hashlib.sha256(hashes_bloques).hexdigest()
