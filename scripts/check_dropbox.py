"""Prueba real opcional: crea UN archivo sintético remoto, sin tocar los documentos del usuario."""
import argparse
from contextlib import ExitStack
from pathlib import Path
import sys
import time
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cbas import agent, backend, database, dropbox_service


def wait_version(nombre, numero):
    limite = time.monotonic() + 75
    while time.monotonic() < limite:
        version = database.obtener_archivo_por_nombre(nombre)
        if version and version['version_actual'] >= numero:
            return database.listar_versiones_de_archivo(nombre)
        time.sleep(.25)
    raise AssertionError('El agente no registró la versión esperada a tiempo.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-real', action='store_true', help='Autoriza crear un archivo sintético en Dropbox.')
    if not parser.parse_args().run_real:
        parser.error('Esta prueba escribe en Dropbox. Usa --run-real para ejecutarla.')
    nombre = 'cbas_verificacion_' + uuid4().hex[:12] + '.txt'
    folder = Path(__file__).resolve().parent.parent / '.cbas-checks' / nombre.removesuffix('.txt')
    folder.mkdir(parents=True)
    original = b'CBAS: prueba sintetica\nversion uno\n'
    changed = b'CBAS: prueba sintetica\nversion dos\n'
    with ExitStack() as stack:
        for module in [agent, backend, dropbox_service]:
            stack.enter_context(patch.object(module, 'MONITORED_DIR', folder))
        stack.enter_context(patch.object(database, 'DATABASE_PATH', folder / '.audit.db'))
        database.inicializar_base_datos()
        observador = agent.iniciar_observador_en_segundo_plano()
        try:
            path = folder / nombre
            path.write_bytes(original)
            v1 = wait_version(nombre, 1)[0]
            path.write_bytes(changed)
            wait_version(nombre, 2)
            client = backend.app.test_client()
            diff = client.get(f'/api/files/{nombre}/diff?version=2&compare_to=prev')
            assert diff.status_code == 200 and diff.json['diff']['lineas_eliminadas'] == 1
            download = client.get(f'/api/files/{nombre}/versions/{v1["rev_dropbox"]}/download')
            assert download.status_code == 200 and download.data == original
            assert path.read_bytes() == changed, 'La descarga cambió el archivo local'
            restored = client.post('/api/restore', json={'nombre_archivo': nombre, 'rev': v1['rev_dropbox'], 'numero_version': 1})
            assert restored.status_code == 200, restored.json
            assert path.read_bytes() == original
            time.sleep(3)
            versions = database.listar_versiones_de_archivo(nombre)
            assert len(versions) == 3, f'Número inesperado de versiones: {len(versions)}'
            assert versions[0]['tipo_operacion'] == 'RESTAURADO'
            assert database.obtener_version_especifica(nombre, numero_version=3)['contenido_texto'].encode() == original
            print('PASS: Watchdog, dos respaldos, diff, descarga exacta y restauración sin duplicados.')
            print('Archivo sintético conservado en Dropbox: ' + nombre)
            print('La base de auditoría de producción y los documentos del usuario no se modificaron.')
        finally:
            observador.stop()
            observador.join()


if __name__ == '__main__':
    main()
