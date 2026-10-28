"""Verificación opcional del panel activo; no modifica archivos ni restaura respaldos."""
from pathlib import Path
import json
import os
from playwright.sync_api import sync_playwright

BASE = os.environ.get('CBAS_CHECK_URL', 'http://127.0.0.1:5050')
OUTPUT = Path(__file__).resolve().parent.parent / '.cbas-checks'


def main():
    OUTPUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        results = []
        for name, width, height in [('desktop', 1440, 1000), ('mobile', 390, 844)]:
            page = browser.new_page(viewport={'width': width, 'height': height})
            errors = []
            page.on('pageerror', lambda err: errors.append(str(err)))
            page.goto(BASE)
            page.wait_for_selector('.file-row', timeout=45000)
            page.wait_for_function("document.querySelector('#restore').disabled === false", timeout=45000)
            assert page.locator('#file-name').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Desbordamiento horizontal'
            page.locator('#search').fill('ningun-archivo-coincide-123')
            assert page.locator('.file-row').count() == 0
            page.get_by_text('Ningún archivo coincide con tu búsqueda.').wait_for()
            page.locator('#search').fill('')
            page.locator('#show-diff').click()
            assert page.locator('#diff-lines .diff-line').count() > 0
            page.wait_for_function("document.querySelector('#refresh').disabled === false", timeout=45000)
            page.evaluate('scrollTo(0, 0)')
            page.screenshot(path=str(OUTPUT / f'{name}.png'), full_page=True)
            page.locator('#show-content').click()
            page.route('**/api/files/*/versions/*/download', lambda route: route.fulfill(status=503, json={'error': 'Descarga temporalmente no disponible'}))
            page.locator('#download').click()
            page.get_by_text('Descarga temporalmente no disponible', exact=True).wait_for()
            assert page.locator('#workspace').is_visible()
            page.unroute('**/api/files/*/versions/*/download')
            page.locator('#dismiss-notice').click()
            page.locator('#restore').click()
            assert page.locator('#restore-dialog').evaluate('(d) => d.open')
            page.locator('#cancel-restore').click()
            assert not page.locator('#restore-dialog').evaluate('(d) => d.open')
            page.locator('#tab-audit').click()
            page.wait_for_selector('#audit-rows tr')
            page.locator('.audit-open').first.click()
            page.wait_for_function("document.querySelector('#restore').disabled === false")
            selected = page.locator('#file-name').inner_text()
            page.locator('#refresh').click()
            page.wait_for_function("document.querySelector('#refresh').disabled === false", timeout=45000)
            assert page.locator('#file-name').inner_text() == selected
            # Un nombre malicioso nunca debe convertirse en HTML.
            malicious = '<img src=x onerror=alert(1)>.txt'
            page.route('**/api/files', lambda route: route.fulfill(json={'archivos': [
                {'nombre_archivo': malicious, 'tamano_bytes': 10, 'version_actual': 1}]}))
            page.route('**/api/files/*/versions', lambda route: route.fulfill(status=503, json={'error': 'Fallo simulado recuperable'}))
            page.locator('#refresh').click()
            page.get_by_text(malicious, exact=True).first.wait_for()
            assert page.locator('#file-list img').count() == 0
            page.get_by_text('Fallo simulado recuperable', exact=True).wait_for()
            page.unroute('**/api/files')
            page.unroute('**/api/files/*/versions')
            page.locator('#refresh').click()
            page.wait_for_function("document.querySelector('#restore').disabled === false", timeout=45000)
            assert not errors, errors
            results.append({'viewport': name, 'width': width, 'javascript_errors': errors, 'result': 'pass'})
            page.close()
        # Primera carga sin archivos y sin Dropbox.
        page = browser.new_page()
        page.route('**/api/files', lambda route: route.fulfill(json={'archivos': []}))
        page.route('**/api/status', lambda route: route.fulfill(json={
            'dropbox': {'conectado': False}, 'resumen': {'total_archivos': 0, 'total_versiones': 0, 'bytes_totales': 0},
            'directorio_monitoreado': 'directorio_pyme', 'sincronizacion': {'agente_activo': True, 'fallidos': 0, 'pendientes': 0}}))
        page.goto(BASE)
        page.get_by_text('Dropbox sin conexión', exact=True).wait_for()
        page.get_by_text('Todavía no hay respaldos.', exact=False).wait_for()
        assert page.locator('#no-selection').is_visible()
        page.screenshot(path=str(OUTPUT / 'empty-offline.png'), full_page=True)
        results.append({'scenario': 'empty-offline', 'result': 'pass'})
        browser.close()
        print(json.dumps(results, ensure_ascii=False))


if __name__ == '__main__':
    main()
