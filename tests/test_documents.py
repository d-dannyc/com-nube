import io
import tempfile
import unittest
import zipfile
import os
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from cbas import backend, dropbox_service
from cbas.documents import texto_docx
from cbas.hasher import calcular_hash_bytes


def docx(text):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        archive.writestr('word/document.xml', f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Celda</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
        archive.writestr('word/media/image.png', b'x' * 600000)
    return output.getvalue()


class DocumentTests(unittest.TestCase):
    def test_docx_extracts_text_from_large_binary_revision(self):
        version = dict(es_texto=0, tamano_bytes=700000, contenido_texto=None,
                       nombre_archivo='test.docx', rev_dropbox='abc', id=1)
        with patch.object(backend, 'descargar_bytes_version', return_value=(docx('Hola'), {})), \
             patch.object(backend, 'guardar_snapshot_texto_en_version'):
            self.assertEqual(backend.obtener_texto_de_version(version), 'Hola\nCelda')

    def test_locked_destination_is_rejected_before_cloud_changes(self):
        @contextmanager
        def locked(path):
            raise PermissionError('locked')
            yield
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(dropbox_service, 'MONITORED_DIR', Path(tmp)), \
             patch.object(dropbox_service, 'destino_restaurable', locked), \
             patch.object(dropbox_service, 'obtener_cliente_dropbox') as client:
            with self.assertRaises(PermissionError):
                dropbox_service.restaurar_version_en_carpeta('test.docx', 'abc')
            client.return_value.files_restore.assert_not_called()

    def test_restoration_lock_error_is_actionable(self):
        with patch.object(backend, 'restaurar_version_en_carpeta', side_effect=PermissionError('locked')):
            response, status = None, None
            with backend.app.test_request_context():
                try:
                    backend._restaurar_version('test.docx', 'abc', 1, False)
                except Exception as exc:
                    response = backend.app.make_response(backend.app.handle_user_exception(exc))
            self.assertEqual(response.status_code, 409)
            self.assertIn('Cierra', response.get_json()['error'])

    def test_invalid_or_oversized_xml_has_no_preview(self):
        self.assertIsNone(texto_docx('bad.docx', b'not zip'))
        self.assertIsNone(texto_docx('old.doc', docx('hello')))
        for xml in [b'<!DOCTYPE d [<!ENTITY e "bad">]><d/>', b'x' * (4*1024*1024+1)]:
            output = io.BytesIO()
            with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('word/document.xml', xml)
            self.assertIsNone(texto_docx('test.docx', output.getvalue()))

    def test_binary_docx_revisions_are_compared_as_extracted_text(self):
        versions = [dict(id=2, numero_version=2, rev_dropbox='bbb', es_texto=0,
                         tamano_bytes=700000, contenido_texto=None, nombre_archivo='test.docx',
                         content_hash='hash', tipo_operacion='MODIFICADO', resumen_cambio='binario',
                         usuario_so='test', direccion_ip='127.0.0.1', nombre_equipo='pc',
                         fecha_registro_utc='2026-10-28', detalle_operacion='test'),
                    dict(id=1, numero_version=1, rev_dropbox='aaa', es_texto=0,
                         tamano_bytes=700000, contenido_texto=None, nombre_archivo='test.docx',
                         fecha_registro_utc='2026-10-27')]
        def version(name, numero_version):
            return next(v for v in versions if v['numero_version'] == numero_version)
        def download(name, rev):
            return docx('Nuevo' if rev == 'bbb' else 'Anterior'), {}
        with patch.object(backend, 'listar_versiones_de_archivo', return_value=versions), \
             patch.object(backend, 'obtener_version_especifica', side_effect=version), \
             patch.object(backend, 'descargar_bytes_version', side_effect=download), \
             patch.object(backend, 'guardar_snapshot_texto_en_version'):
            response = backend.app.test_client().get('/api/files/test.docx/diff?version=2&compare_to=prev')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['tipo_vista_previa'], 'docx')
        self.assertEqual(response.json['diff']['lineas_agregadas'], 1)
        self.assertEqual(response.json['diff']['lineas_eliminadas'], 1)

    def test_unlocked_destination_restores_exact_binary_bytes(self):
        from types import SimpleNamespace
        data = docx('Restaurado')
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(dropbox_service, 'MONITORED_DIR', Path(tmp)), \
             patch.object(dropbox_service, 'obtener_cliente_dropbox') as client:
            path = Path(tmp) / 'test.docx'
            path.write_bytes(b'current')
            client.return_value.files_download_to_file.side_effect = lambda target, *args, **kwargs: Path(target).write_bytes(data)
            client.return_value.files_restore.return_value = SimpleNamespace(
                content_hash=calcular_hash_bytes(data), server_modified=__import__('datetime').datetime.now(),
                path_display='/vault/test.docx', rev='bbb', size=len(data), id='id:demo')
            result = dropbox_service.restaurar_version_en_carpeta('test.docx', 'aaa')
            self.assertEqual(result['_contenido'], data)
            self.assertEqual(path.read_bytes(), data)

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing rules')
    def test_windows_document_lock_blocks_before_dropbox(self):
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(dropbox_service, 'MONITORED_DIR', Path(tmp)), \
             patch.object(dropbox_service, 'obtener_cliente_dropbox') as client:
            path = Path(tmp) / 'locked.docx'
            path.write_bytes(b'untouched')
            handle = kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0, None)
            self.assertNotEqual(handle, wintypes.HANDLE(-1).value)
            try:
                with self.assertRaises(PermissionError):
                    dropbox_service.restaurar_version_en_carpeta('locked.docx', 'aaa')
                client.assert_not_called()
            finally:
                kernel.CloseHandle(handle)
            self.assertEqual(path.read_bytes(), b'untouched')

    @unittest.skipUnless(os.name == 'nt', 'Windows readonly attribute')
    def test_readonly_destination_is_rejected_before_cloud_changes(self):
        import stat
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(dropbox_service, 'MONITORED_DIR', Path(tmp)), \
             patch.object(dropbox_service, 'obtener_cliente_dropbox') as client:
            path = Path(tmp) / 'readonly.docx'
            path.write_bytes(b'untouched')
            path.chmod(stat.S_IREAD)
            try:
                with self.assertRaises(PermissionError):
                    dropbox_service.restaurar_version_en_carpeta('readonly.docx', 'aaa')
                client.assert_not_called()
            finally:
                path.chmod(stat.S_IWRITE)


if __name__ == '__main__':
    unittest.main()
