import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cbas import agent, backend, database, dropbox_service
from cbas.hasher import calcular_content_hash_dropbox


class CbasTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'watched'
        self.root.mkdir()
        self.patches = [
            patch.object(database, 'DATABASE_PATH', self.root.parent / 'audit.db'),
            patch.object(agent, 'MONITORED_DIR', self.root),
            patch.object(backend, 'MONITORED_DIR', self.root),
            patch.object(dropbox_service, 'MONITORED_DIR', self.root),
        ]
        for p in self.patches:
            p.start()
        database.inicializar_base_datos()
        agent.HASHES_SINCRONIZADOS.clear()
        if hasattr(agent, 'PENDIENTES_AUDITORIA'):
            agent.PENDIENTES_AUDITORIA.clear()
        self.client = backend.app.test_client()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.temp.cleanup()

    def cloud_result(self, path, nombre=None, contenido=None):
        return dict(dropbox_file_id='id:test', nombre_archivo=path.name,
                    ruta_dropbox='/vault/' + path.name, rev='abc123',
                    content_hash=calcular_content_hash_dropbox(path),
                    tamano_bytes=path.stat().st_size, fecha_servidor_utc='2026-10-28 12:00:00 UTC')

    def seed(self):
        p = self.root / 'demo.txt'
        p.write_text('original\n', encoding='utf-8')
        with patch.object(agent, 'subir_version_archivo', side_effect=self.cloud_result):
            agent.sincronizar_archivo_guardado(p)
        return p

    def test_files_get_has_no_upload_side_effect(self):
        (self.root / 'new.txt').write_text('demo')
        with patch.object(backend, 'sincronizar_archivo_guardado') as upload:
            self.assertEqual(self.client.get('/api/files').status_code, 200)
            upload.assert_not_called()

    def test_invalid_inputs_are_400_without_cloud_calls(self):
        self.seed()
        for url in ['/api/activity?limite=no', '/api/activity?limite=-1',
                    '/api/files/demo.txt/diff?version=no',
                    '/api/files/demo.txt/diff?compare_to=bad']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 400)
        with patch.object(backend, 'restaurar_version_en_carpeta') as restore:
            for payload in [[], {'nombre_archivo': '../escape.txt', 'rev': 'abc'},
                            {'nombre_archivo': 'C:\\escape.txt', 'rev': 'abc'},
                            {'nombre_archivo': 'demo.txt', 'rev': []},
                            {'nombre_archivo': 'demo.txt', 'rev': 'not-registered'}]:
                with self.subTest(payload=payload):
                    self.assertIn(self.client.post('/api/restore', json=payload).status_code, (400, 404))
            restore.assert_not_called()

    def test_large_text_is_not_downloaded_for_preview(self):
        v = dict(es_texto=1, tamano_bytes=512*1024+1, contenido_texto=None,
                 nombre_archivo='big.txt', rev_dropbox='abc', id=1)
        with patch.object(backend, 'descargar_bytes_version') as download:
            self.assertIsNone(backend.obtener_texto_de_version(v))
            download.assert_not_called()

    def test_audit_failure_does_not_mark_hash_or_reupload(self):
        p = self.root / 'demo.txt'
        p.write_text('hello')
        with patch.object(agent, 'subir_version_archivo', side_effect=self.cloud_result) as upload:
            with patch.object(agent, 'registrar_nueva_version', side_effect=RuntimeError('sqlite busy')):
                with self.assertRaises(RuntimeError):
                    agent.sincronizar_archivo_guardado(p)
            self.assertIsNone(agent.obtener_hash_sincronizado(p.name))
            agent.sincronizar_archivo_guardado(p)
            self.assertEqual(upload.call_count, 1)
            self.assertEqual(len(database.listar_versiones_de_archivo(p.name)), 1)

    def test_failed_backup_is_retried_and_deduplicated(self):
        p = self.root / 'demo.txt'
        p.write_text('hello')
        with patch.object(agent, 'subir_version_archivo', side_effect=RuntimeError('offline')):
            agent.reconciliar_carpeta()
        self.assertIsNone(database.obtener_archivo_por_nombre(p.name))
        with patch.object(agent, 'subir_version_archivo', side_effect=self.cloud_result) as upload:
            agent.reconciliar_carpeta()
            agent.reconciliar_carpeta()
            self.assertEqual(upload.call_count, 1)
        self.assertEqual(len(database.listar_versiones_de_archivo(p.name)), 1)

    def test_restore_registers_once_and_watcher_deduplicates(self):
        p = self.seed()
        result = dict(self.cloud_result(p), nueva_rev_activa='def456',
                      fecha_servidor_utc='2026-10-28 13:00:00 UTC', _contenido=p.read_bytes())
        with patch.object(backend, 'restaurar_version_en_carpeta', return_value=result):
            response = self.client.post('/api/restore', json={'nombre_archivo': p.name, 'rev': 'abc123'})
        self.assertEqual(response.status_code, 200)
        with patch.object(agent, 'subir_version_archivo') as upload:
            self.assertIsNone(agent.sincronizar_archivo_guardado(p))
            upload.assert_not_called()
        self.assertEqual(len(database.listar_versiones_de_archivo(p.name)), 2)

    def test_offline_status_and_missing_files(self):
        with patch.object(backend, 'verificar_cuenta_dropbox', side_effect=RuntimeError('offline')):
            r = self.client.get('/api/status')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json['dropbox']['conectado'])
        self.assertIn('sincronizacion', r.json)
        self.assertEqual(self.client.get('/api/files/missing.txt/versions').status_code, 404)

    def test_concurrent_events_upload_once(self):
        from concurrent.futures import ThreadPoolExecutor
        p = self.root / 'same.txt'
        p.write_text('same')
        with patch.object(agent, 'subir_version_archivo', side_effect=self.cloud_result) as upload:
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(lambda _: agent.sincronizar_archivo_guardado(p), range(4)))
            self.assertEqual(upload.call_count, 1)
        self.assertEqual(len(database.listar_versiones_de_archivo(p.name)), 1)

    def test_upload_and_snapshot_use_same_bytes_even_if_source_changes(self):
        from cbas.hasher import calcular_hash_bytes
        p = self.root / 'changing.txt'
        p.write_bytes(b'first\n')
        def upload(path, name, contenido):
            self.assertEqual(contenido, b'first\n')
            result = self.cloud_result(path)
            p.write_bytes(b'second\n')
            return result
        with patch.object(agent, 'subir_version_archivo', side_effect=upload):
            agent.sincronizar_archivo_guardado(p)
        version = database.obtener_version_especifica(p.name, numero_version=1)
        self.assertEqual(version['contenido_texto'], 'first\n')
        self.assertEqual(version['content_hash'], calcular_hash_bytes(b'first\n'))

    def test_unavailable_download_does_not_reencode_snapshot(self):
        self.seed()
        with patch.object(backend, 'descargar_bytes_version', side_effect=RuntimeError('offline')):
            response = self.client.get('/api/files/demo.txt/versions/abc123/download')
        self.assertEqual(response.status_code, 503)
        self.assertIn('error', response.json)

    def test_diff_exposes_added_and_removed_lines(self):
        p = self.seed()
        p.write_text('updated\n')
        with patch.object(agent, 'subir_version_archivo', side_effect=self.cloud_result):
            agent.sincronizar_archivo_guardado(p)
        response = self.client.get('/api/files/demo.txt/diff?version=2&compare_to=prev')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['diff']['lineas_agregadas'], 1)
        self.assertEqual(response.json['diff']['lineas_eliminadas'], 1)

    def test_restore_snapshot_does_not_reread_later_editor_save(self):
        p = self.seed()
        original = p.read_bytes().decode('utf-8')
        result = dict(self.cloud_result(p), nueva_rev_activa='def456',
                      fecha_servidor_utc='2026-10-28 13:00:00 UTC', _contenido=p.read_bytes())
        def restore(*args):
            p.write_text('editor saved after restore\n')
            return result
        with patch.object(backend, 'restaurar_version_en_carpeta', side_effect=restore):
            response = self.client.post('/api/restore', json={'nombre_archivo': p.name, 'rev': 'abc123'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(database.obtener_version_especifica(p.name, numero_version=2)['contenido_texto'], original)

    def test_compare_current_with_itself_has_no_changes(self):
        self.seed()
        response = self.client.get('/api/files/demo.txt/diff?version=1&compare_to=current')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['diff']['lineas_agregadas'], 0)
        self.assertEqual(response.json['diff']['lineas_eliminadas'], 0)

    def test_debounce_restarts_interval_after_another_event(self):
        from unittest.mock import Mock, call
        worker = agent.AgenteCBAS.__new__(agent.AgenteCBAS)
        worker.fin = Mock()
        worker.fin.is_set.side_effect = [False, False, False, True]
        worker.despertar = Mock()
        worker.despertar.wait.side_effect = [True, True, False]
        with patch.object(agent, 'reconciliar_carpeta') as scan, patch.object(agent.time, 'monotonic', return_value=0):
            worker._ejecutar()
        scan.assert_called_once()
        self.assertEqual(worker.despertar.wait.call_args_list, [call(15), call(1), call(1)])

    def test_continuous_events_cannot_starve_reconciliation(self):
        from unittest.mock import Mock, call
        worker = agent.AgenteCBAS.__new__(agent.AgenteCBAS)
        worker.fin = Mock()
        worker.fin.is_set.side_effect = [False, False, False, True]
        worker.despertar = Mock()
        worker.despertar.wait.side_effect = [True, True]
        with patch.object(agent, 'reconciliar_carpeta'), \
             patch.object(agent.time, 'monotonic', side_effect=[0, 0, 16]):
            worker._ejecutar()
        self.assertEqual(worker.despertar.wait.call_args_list, [call(15), call(1)])

    def test_launcher_opens_panel_without_cloud_requests(self):
        import run_cbas
        with patch.object(run_cbas, 'inicializar_base_datos'), \
             patch.object(run_cbas, 'MONITORED_DIR', self.root), \
             patch.object(run_cbas, 'iniciar_observador_en_segundo_plano') as watcher, \
             patch.object(run_cbas.app, 'run') as serve, \
             patch.object(dropbox_service, 'obtener_cliente_dropbox', side_effect=AssertionError('cloud blocks startup')):
            run_cbas.main()
        serve.assert_called_once()
        watcher.return_value.stop.assert_called_once()

    def test_oauth_updates_credentials_without_overwriting_settings(self):
        from types import SimpleNamespace
        from scripts import setup_oauth
        env = self.root.parent / '.env'
        env.write_text('CBAS_BACKEND_PORT=6060\nCUSTOM_SETTING=keep\n')
        with patch.object(setup_oauth, 'ENV_FILE', env), \
             patch('builtins.input', side_effect=['key', 'code']), \
             patch.object(setup_oauth, 'getpass', return_value='secret'), \
             patch.object(setup_oauth, 'DropboxOAuth2FlowNoRedirect') as flow:
            flow.return_value.start.return_value = 'https://example.invalid/oauth'
            flow.return_value.finish.return_value = SimpleNamespace(refresh_token='fake-token')
            setup_oauth.configurar_oauth_interactivo()
        result = env.read_text()
        self.assertIn('CBAS_BACKEND_PORT=6060', result)
        self.assertIn('CUSTOM_SETTING=keep', result)
        self.assertIn('DROPBOX_REFRESH_TOKEN=', result)


if __name__ == '__main__':
    unittest.main()
