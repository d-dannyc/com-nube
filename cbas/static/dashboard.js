'use strict';
const $ = id => document.getElementById(id);
const state = {files: [], file: null, versions: [], version: null, detail: null,
  mode: 'content', audit: false, refreshing: false, restoring: false, loading: false, generation: 0};
const operations = {CREADO: 'Primer respaldo', MODIFICADO: 'Contenido actualizado', RESTAURADO: 'Versión restaurada'};
const bytes = n => n < 1024 ? `${n} B` : n < 1048576 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1048576).toFixed(1)} MB`;
function date(value) {
  if (!value) return '—';
  const parsed = new Date(value.includes(' UTC') ? value.replace(' UTC', 'Z').replace(' ', 'T') : value);
  return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat('es', {dateStyle: 'medium', timeStyle: 'short'}).format(parsed);
}
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function notice(message, success = false) {
  $('notice-text').textContent = message;
  $('notice').className = success ? 'notice success' : 'notice';
  $('notice').hidden = false;
}
async function api(url, options = {}) {
  let response;
  try { response = await fetch(url, {...options, signal: AbortSignal.timeout(45000)}); }
  catch { throw new Error('No se pudo conectar con CBAS. Comprueba que el servidor esté activo y pulsa Actualizar.'); }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(data?.error || `No se pudo completar la solicitud (${response.status}).`);
    error.status = response.status;
    throw error;
  }
  if (!data) throw new Error('El servidor devolvió una respuesta no válida.');
  return data;
}
function lockActions() {
  const disabled = state.loading || state.restoring || !state.detail;
  $('restore').disabled = disabled;
  $('download').hidden = disabled;
  $('compare').disabled = state.loading || state.restoring;
}
function fileIcon(extension) {
  const wrap = element('span', 'file-icon');
  wrap.setAttribute('aria-hidden', 'true');
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 34 39'); svg.setAttribute('fill', 'none');
  const path = document.createElementNS(svg.namespaceURI, 'path');
  path.setAttribute('d', 'M7 2h14l7 7v27H7V2Zm14 0v8h7');
  path.setAttribute('stroke', 'currentColor'); path.setAttribute('stroke-width', '1.4');
  svg.append(path); wrap.append(svg, element('span', '', extension.slice(0, 5)));
  return wrap;
}
function renderFiles() {
  const list = $('file-list'); list.replaceChildren();
  const query = $('search').value.trim().toLocaleLowerCase();
  const files = state.files.filter(f => f.nombre_archivo.toLocaleLowerCase().includes(query));
  $('file-count').textContent = state.files.length;
  if (!files.length) {
    list.append(element('p', 'empty small', query ? 'Ningún archivo coincide con tu búsqueda.' : 'Todavía no hay respaldos. Guarda un archivo en directorio_pyme y espera la sincronización.'));
  }
  for (const file of files) {
    const button = element('button', `file-row${file.nombre_archivo === state.file ? ' selected' : ''}`);
    button.type = 'button'; button.setAttribute('aria-pressed', String(file.nombre_archivo === state.file));
    const copy = element('span', 'file-copy');
    copy.append(element('span', 'file-title', file.nombre_archivo), element('span', 'file-sub', `${bytes(file.tamano_bytes)} · v${file.version_actual}`));
    button.append(fileIcon(file.nombre_archivo.split('.').pop().toUpperCase()), copy);
    button.addEventListener('click', () => { if (!state.restoring) selectFile(file.nombre_archivo); });
    list.append(button);
  }
  const filter = $('audit-filter'); const previous = filter.value;
  filter.replaceChildren(new Option('Todos los archivos', ''));
  for (const file of state.files) filter.add(new Option(file.nombre_archivo, file.nombre_archivo));
  filter.value = previous;
}
function renderHistory() {
  $('history').replaceChildren(); $('version-count').textContent = state.versions.length;
  for (const [index, version] of state.versions.entries()) {
    const row = element('button', `version-row${version.numero_version === state.version ? ' selected' : ''}`);
    row.type = 'button'; row.setAttribute('aria-pressed', String(version.numero_version === state.version));
    const top = element('span', 'version-top'); top.append(element('span', '', `Versión ${version.numero_version}`));
    if (index === 0) top.append(element('span', 'version-current', 'ÚLTIMO RESPALDO'));
    row.append(top, element('span', 'version-date', date(version.fecha_registro_utc)), element('span', 'version-operation', operations[version.tipo_operacion] || version.tipo_operacion));
    row.addEventListener('click', () => { if (!state.restoring) selectVersion(version.numero_version); });
    $('history').append(row);
  }
}
function changeMode(mode) {
  state.mode = mode;
  $('show-content').classList.toggle('active', mode === 'content');
  $('show-diff').classList.toggle('active', mode === 'diff');
  $('show-content').setAttribute('aria-pressed', String(mode === 'content'));
  $('show-diff').setAttribute('aria-pressed', String(mode === 'diff'));
  $('preview').hidden = mode !== 'content'; $('diff-view').hidden = mode !== 'diff';
  $('compare-label').hidden = mode !== 'diff';
}
function renderDetail() {
  const data = state.detail, v = data.version_seleccionada;
  $('file-name').textContent = state.file;
  $('file-type').textContent = state.file.split('.').pop().toUpperCase();
  $('file-meta').textContent = `Versión ${v.numero_version} · ${bytes(v.tamano_bytes)} · ${date(v.fecha_registro_utc)}`;
  $('preview-state').textContent = data.tipo_vista_previa === 'docx'
    ? 'Texto principal de Word, sin formato, imágenes, encabezados ni notas.' : '';
  $('preview').classList.toggle('document-text', data.tipo_vista_previa === 'docx');
  $('preview').textContent = data.contenido_texto ?? (v.es_texto
    ? 'Este archivo supera el límite de vista previa (512 KiB). Descarga la versión para leerlo completo.'
    : data.tipo_vista_previa === 'docx' ? 'No se pudo extraer el texto: documento no compatible o límite de tamaño excedido. Descarga la versión para abrirla en Word.'
    : 'La vista previa no está disponible para este formato. Descarga esta versión para abrirla con su aplicación.');
  $('diff-summary').textContent = `${data.diff.resumen}${data.version_comparada ? ` · Base: v${data.version_comparada.numero_version} → seleccionada: v${v.numero_version}` : ''}`;
  $('diff-lines').replaceChildren();
  if (data.contenido_texto === null || !data.diff.lineas_diff.length) {
    $('diff-lines').append(element('p', 'empty small', data.diff.resumen || 'No hay texto para comparar.'));
  } else {
    const fragment = document.createDocumentFragment();
    for (const line of data.diff.lineas_diff) {
      const row = element('div', `diff-line ${line.tipo === 'agregada' ? 'added' : line.tipo === 'eliminada' ? 'removed' : ''}`);
      row.append(element('span', 'diff-number', line.num_ant ?? ''), element('span', 'diff-number', line.num_nueva ?? ''),
        element('span', 'diff-sign', line.tipo === 'agregada' ? '+' : line.tipo === 'eliminada' ? '−' : ' '), element('span', 'diff-text', line.texto));
      fragment.append(row);
    }
    $('diff-lines').append(fragment);
  }
  $('download').href = `/api/files/${encodeURIComponent(state.file)}/versions/${encodeURIComponent(v.rev_dropbox)}/download`;
  $('restore').textContent = `Restaurar v${v.numero_version}`;
  const details = [['Revisión', v.rev_dropbox], ['Hash', v.content_hash], ['Usuario', v.usuario_so], ['Equipo', v.nombre_equipo], ['IP', v.direccion_ip], ['Fecha UTC', v.fecha_registro_utc]];
  $('technical-data').replaceChildren();
  for (const [label, value] of details) $('technical-data').append(element('dt', '', label), element('dd', '', value));
  renderHistory(); changeMode(state.mode);
}
async function selectFile(name, desiredVersion = null) {
  const token = ++state.generation;
  state.loading = true; state.file = name; state.detail = null;
  $('document').hidden = false; $('no-selection').hidden = true;
  $('file-name').textContent = name; $('file-meta').textContent = 'Cargando versiones…';
  $('preview-state').textContent = 'Cargando el archivo…'; $('preview').textContent = '';
  $('diff-lines').replaceChildren(); $('diff-summary').textContent = '';
  $('history').replaceChildren(); $('technical-data').replaceChildren();
  lockActions(); renderFiles();
  try {
    const data = await api(`/api/files/${encodeURIComponent(name)}/versions`);
    if (token !== state.generation) return;
    state.versions = data.versiones;
    state.version = desiredVersion && state.versions.some(v => v.numero_version === desiredVersion) ? desiredVersion : state.versions[0]?.numero_version;
    renderHistory();
    await loadDetail(token);
  } catch (err) { if (token === state.generation) { notice(err.message); $('preview-state').textContent = 'No se pudo cargar el archivo. Pulsa Actualizar para reintentar.'; } }
  finally { if (token === state.generation) { state.loading = false; lockActions(); } }
}
async function selectVersion(number) {
  const token = ++state.generation;
  state.version = number; state.loading = true; state.detail = null;
  $('preview').textContent = ''; $('diff-lines').replaceChildren();
  $('diff-summary').textContent = ''; $('technical-data').replaceChildren();
  $('preview-state').textContent = 'Cargando versión…'; lockActions(); renderHistory();
  try { await loadDetail(token); }
  catch (err) { if (token === state.generation) { notice(err.message); $('preview-state').textContent = 'No se pudo cargar esta versión. Selecciónala de nuevo para reintentar.'; } }
  finally { if (token === state.generation) { state.loading = false; lockActions(); } }
}
async function loadDetail(token) {
  const url = `/api/files/${encodeURIComponent(state.file)}/diff?version=${state.version}&compare_to=${$('compare').value}`;
  const data = await api(url);
  if (token !== state.generation) return;
  state.detail = data; renderDetail();
}
async function loadStatus() {
  try {
    const data = await api('/api/status');
    $('connection').className = `connection ${data.dropbox.conectado ? 'connected' : 'offline'}`;
    $('connection-text').textContent = data.dropbox.conectado ? 'Dropbox conectado' : 'Dropbox sin conexión';
    $('total-files').textContent = data.resumen.total_archivos;
    $('total-versions').textContent = data.resumen.total_versiones;
    $('total-size').textContent = bytes(data.resumen.bytes_totales);
    $('folder-path').textContent = data.directorio_monitoreado;
    const sync = data.sincronizacion;
    $('sync-label').textContent = !sync.agente_activo ? 'Agente detenido · reinicia run_cbas.py' : sync.fallidos ? `${sync.fallidos} archivo(s) pendiente(s) · reintento automático` : sync.pendientes ? 'Sincronizando archivos…' : 'Monitoreo activo · cambios respaldados automáticamente';
    if (!data.dropbox.conectado) notice('Dropbox no está disponible. Puedes consultar los respaldos registrados; comprueba conexión y credenciales para sincronizar, descargar o restaurar.');
    else if (sync.fallidos) notice(`Archivos pendientes: ${Object.keys(sync.errores).join(', ')}. Comprueba conexión, permisos y tamaño. CBAS volverá a intentarlo.`);
  } catch (err) { $('connection').className = 'connection offline'; $('connection-text').textContent = 'Servidor sin conexión'; notice(err.message); }
}
async function loadFiles() {
  const data = await api('/api/files'); state.files = data.archivos; renderFiles();
  if (!state.files.length) {
    state.file = null; state.version = null; state.detail = null; state.versions = [];
    $('document').hidden = true; $('no-selection').hidden = false;
    $('history').replaceChildren(element('p', 'empty small', 'Selecciona un archivo para ver sus versiones.'));
    $('version-count').textContent = '0'; lockActions(); return;
  }
  const next = state.file && state.files.some(f => f.nombre_archivo === state.file) ? state.file : state.files[0].nombre_archivo;
  const selected = state.files.find(f => f.nombre_archivo === next);
  if (!state.detail || next !== state.file || state.versions[0]?.numero_version !== selected.version_actual) {
    await selectFile(next, state.version);
  }
}
async function loadAudit() {
  $('audit-state').textContent = 'Cargando actividad…';
  try {
    const filter = $('audit-filter').value;
    const data = await api(`/api/activity?limite=100${filter ? `&archivo=${encodeURIComponent(filter)}` : ''}`);
    $('audit-rows').replaceChildren();
    $('audit-state').textContent = data.eventos.length ? '' : 'Todavía no hay actividad para mostrar.';
    for (const event of data.eventos) {
      const row = element('tr');
      row.append(element('td', '', event.nombre_archivo), element('td', '', operations[event.tipo_operacion] || event.tipo_operacion), element('td', '', `v${event.numero_version}`));
      const author = element('td', '', event.usuario_so); author.append(element('small', '', `${event.nombre_equipo} · ${event.direccion_ip}`));
      const cell = element('td'), open = element('button', 'audit-open', 'Ver versión'); open.type = 'button';
      open.addEventListener('click', () => { switchView(false); selectFile(event.nombre_archivo, event.numero_version); });
      cell.append(open); row.append(author, element('td', '', date(event.fecha_registro_utc)), cell); $('audit-rows').append(row);
    }
  } catch (err) { $('audit-state').textContent = err.message; notice(err.message); }
}
function switchView(audit) {
  state.audit = audit; $('workspace').hidden = audit; $('audit-view').hidden = !audit;
  for (const [id, active] of [['tab-files', !audit], ['tab-audit', audit]]) {
    $(id).classList.toggle('active', active);
    if (active) $(id).setAttribute('aria-current', 'page'); else $(id).removeAttribute('aria-current');
  }
  if (audit) loadAudit();
}
async function refresh() {
  if (state.refreshing || state.loading || state.restoring || $('restore-dialog').open) return;
  state.refreshing = true; $('refresh').disabled = true;
  try {
    await Promise.all([loadStatus(), loadFiles(), state.audit ? loadAudit() : Promise.resolve()]);
    $('last-refresh').textContent = `Actualizado ${new Intl.DateTimeFormat('es', {timeStyle: 'short'}).format(new Date())} · cada 15 s`;
  } catch (err) { notice(err.message); }
  finally { state.refreshing = false; $('refresh').disabled = false; }
}
$('refresh').addEventListener('click', refresh);
$('dismiss-notice').addEventListener('click', () => { $('notice').hidden = true; });
$('search').addEventListener('input', renderFiles);
$('tab-files').addEventListener('click', () => switchView(false));
$('tab-audit').addEventListener('click', () => switchView(true));
$('audit-filter').addEventListener('change', loadAudit);
$('show-content').addEventListener('click', () => changeMode('content'));
$('show-diff').addEventListener('click', () => changeMode('diff'));
$('compare').addEventListener('change', () => { if (state.version) selectVersion(state.version); });
$('restore').addEventListener('click', () => {
  if (!state.detail || state.loading || state.restoring) return;
  $('restore-description').textContent = `Vas a recuperar «${state.file}», versión ${state.version}.`;
  $('restore-dialog').showModal(); $('cancel-restore').focus();
});
let downloading = false;
$('download').addEventListener('click', async e => {
  e.preventDefault();
  if (downloading || !state.detail || state.loading || state.restoring) return;
  downloading = true; $('download').setAttribute('aria-busy', 'true');
  $('download').textContent = 'Descargando…';
  const name = state.file, version = state.version;
  try {
    const response = await fetch($('download').href, {signal: AbortSignal.timeout(45000)});
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || 'No se pudo descargar la versión. Comprueba Dropbox y vuelve a intentar.');
    }
    const url = URL.createObjectURL(await response.blob());
    const link = element('a'); link.href = url;
    const dot = name.lastIndexOf('.');
    link.download = dot > 0 ? `${name.slice(0, dot)}_v${version}${name.slice(dot)}` : `${name}_v${version}`;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (err) { notice(err.message || 'No se pudo descargar la versión. Comprueba la conexión.'); }
  finally { downloading = false; $('download').removeAttribute('aria-busy'); $('download').textContent = 'Descargar versión'; }
});
$('cancel-restore').addEventListener('click', () => { if (!state.restoring) $('restore-dialog').close(); });
$('restore-dialog').addEventListener('cancel', e => { if (state.restoring) e.preventDefault(); });
$('restore-form').addEventListener('submit', async e => {
  e.preventDefault(); if (state.restoring || !state.detail) return;
  const name = state.file, version = state.version, rev = state.detail.version_seleccionada.rev_dropbox;
  state.restoring = true; lockActions(); $('confirm-restore').disabled = true; $('cancel-restore').disabled = true;
  $('confirm-restore').textContent = 'Restaurando…';
  try {
    const data = await api('/api/restore', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({nombre_archivo: name, rev, numero_version: version})});
    state.version = data.nueva_version.numero_version;
    notice(`Restauración completada. ${name} se registró como versión ${state.version}.`, true);
  } catch (err) {
    notice(err.status === 409 ? err.message : `${err.message} Actualiza el historial antes de reintentar para comprobar si la operación llegó a completarse.`);
  }
  finally {
    state.restoring = false; $('restore-dialog').close(); $('confirm-restore').disabled = false;
    $('cancel-restore').disabled = false; $('confirm-restore').textContent = 'Sí, restaurar'; lockActions(); await refresh();
  }
});
document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
setInterval(() => { if (!document.hidden) refresh(); }, 15000);
refresh();
