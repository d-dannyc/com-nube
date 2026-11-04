'use strict';

const $ = id => document.getElementById(id);

const state = {
  files: [],
  file: null,
  dept: 'Todos',
  versions: [],
  version: null,
  detail: null,
  mode: 'content', // 'content', 'diff', 'editor'
  view: 'files',   // 'files', 'audit', 'simulator', 'architecture'
  refreshing: false,
  restoring: false,
  loading: false,
  generation: 0,
  activeMilestoneVer: null,
};

const operations = {
  CREADO: 'Primer respaldo',
  MODIFICADO: 'Contenido actualizado',
  RESTAURADO: 'Versión restaurada'
};

const bytes = n => {
  if (n === null || n === undefined || isNaN(n)) return '0 B';
  return n < 1024 ? `${n} B` : n < 1048576 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1048576).toFixed(1)} MB`;
};

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
  try {
    response = await fetch(url, {...options, signal: AbortSignal.timeout(45000)});
  } catch {
    throw new Error('No se pudo conectar con el servidor CBAS. Comprueba que run_cbas.py esté activo.');
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(data?.error || `Error en la solicitud (${response.status}).`);
    error.status = response.status;
    throw error;
  }
  if (!data) throw new Error('El servidor devolvió una respuesta no válida.');
  return data;
}

// Reloj UTC en vivo
function updateClock() {
  const now = new Date();
  const utcStr = now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
  if ($('live-clock')) $('live-clock').textContent = utcStr;
}
setInterval(updateClock, 1000);
updateClock();

function lockActions() {
  const disabled = state.loading || state.restoring || !state.detail;
  $('restore').disabled = disabled;
  $('download').hidden = disabled;
  $('compare').disabled = state.loading || state.restoring;
  $('btn-compact').disabled = disabled;
}

function fileIcon(extension) {
  const wrap = element('span', 'file-icon');
  wrap.setAttribute('aria-hidden', 'true');
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 34 39');
  svg.setAttribute('fill', 'none');
  const path = document.createElementNS(svg.namespaceURI, 'path');
  path.setAttribute('d', 'M7 2h14l7 7v27H7V2Zm14 0v8h7');
  path.setAttribute('stroke', 'currentColor');
  path.setAttribute('stroke-width', '1.4');
  svg.append(path);
  wrap.append(svg, element('span', '', extension.slice(0, 5)));
  return wrap;
}

function renderFiles() {
  const list = $('file-list');
  list.replaceChildren();
  const query = $('search').value.trim().toLocaleLowerCase();

  let filtered = state.files;
  if (state.dept !== 'Todos') {
    filtered = filtered.filter(f => (f.departamento || 'General') === state.dept);
  }
  if (query) {
    filtered = filtered.filter(f => f.nombre_archivo.toLocaleLowerCase().includes(query));
  }

  $('file-count').textContent = filtered.length;
  if (!filtered.length) {
    list.append(element('p', 'empty small', query ? 'Ningún archivo coincide con tu búsqueda.' : 'No hay archivos en este departamento.'));
    return;
  }

  for (const file of filtered) {
    const isSelected = file.nombre_archivo === state.file;
    const button = element('button', `file-row${isSelected ? ' selected' : ''}`);
    button.type = 'button';
    button.setAttribute('aria-pressed', String(isSelected));

    const copy = element('span', 'file-copy');
    const titleRow = element('div', 'file-title-row');
    const title = element('span', 'file-title', file.nombre_archivo);
    titleRow.append(title);
    if (file.protegido) {
      const lock = element('span', 'file-lock-icon', ' 🔒');
      lock.title = 'Documento congelado / auditado';
      titleRow.append(lock);
    }

    const sub = element('span', 'file-sub', `${file.departamento || 'General'} · ${bytes(file.tamano_bytes)} · v${file.version_actual}`);
    copy.append(titleRow, sub);

    const ext = file.nombre_archivo.split('.').pop().toUpperCase();
    button.append(fileIcon(ext), copy);
    button.addEventListener('click', () => {
      if (!state.restoring) selectFile(file.nombre_archivo);
    });
    list.append(button);
  }
}

function renderHistory() {
  $('history').replaceChildren();
  $('version-count').textContent = state.versions.length;

  for (const [index, version] of state.versions.entries()) {
    const isSelected = version.numero_version === state.version;
    const row = element('div', `version-row${isSelected ? ' selected' : ''}`);

    const header = element('div', 'version-top');
    const title = element('strong', '', `Versión ${version.numero_version}`);
    header.append(title);

    if (index === 0) {
      header.append(element('span', 'version-current', 'ACTIVA'));
    }
    if (version.es_hito) {
      header.append(element('span', 'milestone-badge', `⭐ ${version.etiqueta_hito || 'HITO'}`));
    }
    if (version.nivel_riesgo === 'CRITICO') {
      header.append(element('span', 'risk-pill critico', 'CRÍTICO'));
    } else if (version.nivel_riesgo === 'ADVERTENCIA') {
      header.append(element('span', 'risk-pill advertencia', 'ALERTA'));
    }

    const dateSpan = element('span', 'version-date', date(version.fecha_registro_utc));
    const opSpan = element('span', 'version-operation', operations[version.tipo_operacion] || version.tipo_operacion);

    const actions = element('div', 'version-actions-row');
    const viewBtn = element('button', 'button-link small', 'Ver');
    viewBtn.type = 'button';
    viewBtn.addEventListener('click', e => {
      e.stopPropagation();
      if (!state.restoring) selectVersion(version.numero_version);
    });
    actions.append(viewBtn);

    const milestoneBtn = element('button', 'milestone-btn', version.es_hito ? 'Quitar hito' : '⭐ Fijar hito');
    milestoneBtn.type = 'button';
    milestoneBtn.addEventListener('click', e => {
      e.stopPropagation();
      openMilestoneDialog(version.numero_version, version.es_hito, version.etiqueta_hito);
    });
    actions.append(milestoneBtn);

    row.append(header, dateSpan, opSpan, actions);
    row.addEventListener('click', () => {
      if (!state.restoring) selectVersion(version.numero_version);
    });
    $('history').append(row);
  }
}

function changeMode(mode) {
  state.mode = mode;
  $('show-content').classList.toggle('active', mode === 'content');
  $('show-diff').classList.toggle('active', mode === 'diff');
  $('show-editor').classList.toggle('active', mode === 'editor');
  $('show-content').setAttribute('aria-pressed', String(mode === 'content'));
  $('show-diff').setAttribute('aria-pressed', String(mode === 'diff'));
  $('show-editor').setAttribute('aria-pressed', String(mode === 'editor'));

  $('preview').hidden = mode !== 'content';
  $('diff-view').hidden = mode !== 'diff';
  $('editor-view').hidden = mode !== 'editor';
  $('compare-label').hidden = mode !== 'diff';

  if (mode === 'editor' && state.detail) {
    setupEditor();
  }
}

function checkDraftRecovery(fileName, serverContent) {
  const key = `cbas_draft_${fileName}`;
  const savedDraft = localStorage.getItem(key);
  const banner = $('draft-recovery-alert');
  if (savedDraft && savedDraft !== serverContent) {
    banner.hidden = false;
  } else {
    banner.hidden = true;
  }
}

function setupEditor() {
  if (!state.detail) return;
  const content = state.detail.contenido_texto || '';
  const editor = $('file-editor');
  
  // Si no se ha tocado o coincide con el servidor, cargamos
  const key = `cbas_draft_${state.file}`;
  const savedDraft = localStorage.getItem(key);
  editor.value = savedDraft || content;
  updateEditorStats();
  checkDraftRecovery(state.file, content);
}

function updateEditorStats() {
  const val = $('file-editor').value;
  const lines = val.split('\n').length;
  const chars = val.length;
  $('editor-stats').textContent = `Líneas: ${lines} · Caracteres: ${chars} · Autoguardado local activo`;
}

$('file-editor').addEventListener('input', () => {
  if (state.file) {
    localStorage.setItem(`cbas_draft_${state.file}`, $('file-editor').value);
    updateEditorStats();
  }
});

$('btn-restore-draft').addEventListener('click', () => {
  const saved = localStorage.getItem(`cbas_draft_${state.file}`);
  if (saved !== null) {
    $('file-editor').value = saved;
    updateEditorStats();
    notice('Borrador previo recuperado en el editor.', true);
  }
});

$('btn-dismiss-draft').addEventListener('click', () => {
  localStorage.removeItem(`cbas_draft_${state.file}`);
  if (state.detail) {
    $('file-editor').value = state.detail.contenido_texto || '';
    updateEditorStats();
  }
  $('draft-recovery-alert').hidden = true;
  notice('Borrador descartado.');
});

$('btn-save-content').addEventListener('click', async () => {
  if (!state.file) return;
  const content = $('file-editor').value;
  $('btn-save-content').disabled = true;
  $('btn-save-content').textContent = 'Guardando en Dropbox…';
  try {
    const res = await api(`/api/files/${encodeURIComponent(state.file)}/save-content`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({contenido_texto: content}),
    });
    localStorage.removeItem(`cbas_draft_${state.file}`);
    $('draft-recovery-alert').hidden = true;
    notice(`Archivo «${state.file}» guardado y sincronizado con Dropbox.`, true);
    await refresh();
    await selectFile(state.file);
  } catch (err) {
    notice(err.message);
  } finally {
    $('btn-save-content').disabled = false;
    $('btn-save-content').textContent = 'Guardar cambios en Dropbox';
  }
});

function renderDetail() {
  const data = state.detail;
  const v = data.version_seleccionada;
  const curFile = state.files.find(f => f.nombre_archivo === state.file);

  $('file-name').textContent = state.file;
  $('file-type').textContent = state.file.split('.').pop().toUpperCase();
  $('file-dept').textContent = curFile?.departamento || 'General';

  // Botón proteger / congelar
  const isProtected = curFile?.protegido;
  $('btn-toggle-protect').className = `protect-btn${isProtected ? ' protected' : ''}`;
  $('btn-toggle-protect').textContent = isProtected ? '🔒 Documento Congelado / Auditado' : '🔓 Documento Abierto';

  $('file-meta').textContent = `Versión ${v.numero_version} · ${bytes(v.tamano_bytes)} · ${date(v.fecha_registro_utc)}`;

  // Alerta de riesgo / anomalía
  const alertBanner = $('file-risk-alert');
  if (v.nivel_riesgo && v.nivel_riesgo !== 'NORMAL') {
    alertBanner.hidden = false;
    alertBanner.className = `risk-banner ${v.nivel_riesgo === 'CRITICO' ? 'risk-critico' : 'risk-advertencia'}`;
    alertBanner.textContent = `⚠️ [${v.nivel_riesgo}] ${v.alerta_metadatos || 'Anomalía de integridad detectada en esta versión.'}`;
  } else {
    alertBanner.hidden = true;
  }

  $('preview-state').textContent = data.tipo_vista_previa === 'docx'
    ? 'Texto principal de Word, sin formato ni imágenes.' : '';
  $('preview').classList.toggle('document-text', data.tipo_vista_previa === 'docx');
  $('preview').textContent = data.contenido_texto ?? (v.es_texto
    ? 'Este archivo supera el límite de vista previa (512 KiB). Descarga la versión para leerlo completo.'
    : data.tipo_vista_previa === 'docx' ? 'No se pudo extraer el texto del documento Word.'
    : 'Vista previa no disponible para este formato binario.');

  // Diff
  $('diff-summary').textContent = `${data.diff.resumen}${data.version_comparada ? ` · Base: v${data.version_comparada.numero_version} → seleccionada: v${v.numero_version}` : ''}`;
  $('diff-lines').replaceChildren();
  if (data.contenido_texto === null || !data.diff.lineas_diff.length) {
    $('diff-lines').append(element('p', 'empty small', data.diff.resumen || 'No hay texto para comparar.'));
  } else {
    const fragment = document.createDocumentFragment();
    for (const line of data.diff.lineas_diff) {
      const row = element('div', `diff-line ${line.tipo === 'agregada' ? 'added' : line.tipo === 'eliminada' ? 'removed' : ''}`);
      row.append(
        element('span', 'diff-number', line.num_ant ?? ''),
        element('span', 'diff-number', line.num_nueva ?? ''),
        element('span', 'diff-sign', line.tipo === 'agregada' ? '+' : line.tipo === 'eliminada' ? '−' : ' '),
        element('span', 'diff-text', line.texto)
      );
      fragment.append(row);
    }
    $('diff-lines').append(fragment);
  }

  $('download').href = `/api/files/${encodeURIComponent(state.file)}/versions/${encodeURIComponent(v.rev_dropbox)}/download`;
  $('restore').textContent = `Restaurar v${v.numero_version}`;

  const details = [
    ['Departamento', curFile?.departamento || 'General'],
    ['Estado', isProtected ? 'CONGELADO / AUDITADO' : 'ACTIVO'],
    ['Revisión rev', v.rev_dropbox],
    ['Content Hash (4MB)', v.content_hash],
    ['Bloques 4MB', v.bloques_4mb_total || 1],
    ['Ahorro Delta Sync', bytes(v.bytes_ahorrados_delta || 0)],
    ['Usuario SO', v.usuario_so],
    ['Equipo / Host', v.nombre_equipo],
    ['Dirección IP', v.direccion_ip],
    ['Fecha UTC', v.fecha_registro_utc],
    ['Detalle Operación', v.detalle_operacion || '—']
  ];
  $('technical-data').replaceChildren();
  for (const [lbl, val] of details) {
    $('technical-data').append(element('dt', '', lbl), element('dd', '', String(val)));
  }

  renderHistory();
  changeMode(state.mode);
}

async function selectFile(name, desiredVersion = null) {
  const token = ++state.generation;
  state.loading = true;
  state.file = name;
  state.detail = null;

  $('document').hidden = false;
  $('no-selection').hidden = true;
  $('file-name').textContent = name;
  $('file-meta').textContent = 'Cargando versiones…';
  $('preview-state').textContent = 'Cargando el archivo…';
  $('preview').textContent = '';
  $('diff-lines').replaceChildren();
  $('history').replaceChildren();
  $('technical-data').replaceChildren();
  lockActions();
  renderFiles();

  try {
    const data = await api(`/api/files/${encodeURIComponent(name)}/versions`);
    if (token !== state.generation) return;
    state.versions = data.versiones;
    state.version = desiredVersion && state.versions.some(v => v.numero_version === desiredVersion)
      ? desiredVersion
      : state.versions[0]?.numero_version;
    renderHistory();
    await loadDetail(token);
  } catch (err) {
    if (token === state.generation) {
      notice(err.message);
      $('preview-state').textContent = 'No se pudo cargar el archivo.';
    }
  } finally {
    if (token === state.generation) {
      state.loading = false;
      lockActions();
    }
  }
}

async function selectVersion(number) {
  const token = ++state.generation;
  state.version = number;
  state.loading = true;
  state.detail = null;
  lockActions();
  renderHistory();

  try {
    await loadDetail(token);
  } catch (err) {
    if (token === state.generation) notice(err.message);
  } finally {
    if (token === state.generation) {
      state.loading = false;
      lockActions();
    }
  }
}

async function loadDetail(token) {
  const url = `/api/files/${encodeURIComponent(state.file)}/diff?version=${state.version}&compare_to=${$('compare').value}`;
  const data = await api(url);
  if (token !== state.generation) return;
  state.detail = data;
  renderDetail();
}

async function loadStatus() {
  try {
    const data = await api('/api/status');
    $('connection').className = `connection ${data.dropbox.conectado ? 'connected' : 'offline'}`;
    $('connection-text').textContent = data.dropbox.conectado ? 'Dropbox conectado' : 'Dropbox sin conexión';
    $('total-files').textContent = data.resumen.total_archivos;
    $('total-versions').textContent = data.resumen.total_versiones;
    $('total-milestones').textContent = data.resumen.total_hitos || 0;
    $('total-savings').textContent = bytes(data.resumen.ahorro_delta_bytes || 0);
    $('folder-path').textContent = data.directorio_monitoreado;

    const sync = data.sincronizacion;
    const activeSessions = Object.keys(sync.sesiones_activas || {}).length;
    if (activeSessions > 0) {
      $('session-status').textContent = `⚡ ${activeSessions} sesión(es) de edición activa(s) detectada(s).`;
      $('session-status').className = 'session-status text-amber';
    } else {
      $('session-status').textContent = 'Monitoreo en tiempo real activo.';
      $('session-status').className = 'session-status';
    }

    $('sync-label').textContent = !sync.agente_activo
      ? 'Agente detenido'
      : sync.fallidos
      ? `${sync.fallidos} pendiente(s)`
      : sync.pendientes
      ? 'Sincronizando…'
      : 'Monitoreo activo';
  } catch (err) {
    $('connection').className = 'connection offline';
    $('connection-text').textContent = 'Servidor sin conexión';
  }
}

async function loadFiles() {
  const data = await api('/api/files');
  state.files = data.archivos;
  renderFiles();

  if (!state.files.length) {
    state.file = null;
    state.version = null;
    state.detail = null;
    state.versions = [];
    $('document').hidden = true;
    $('no-selection').hidden = false;
    $('history').replaceChildren(element('p', 'empty small', 'Selecciona un archivo para ver sus versiones.'));
    $('version-count').textContent = '0';
    lockActions();
    return;
  }

  const next = state.file && state.files.some(f => f.nombre_archivo === state.file)
    ? state.file
    : state.files[0].nombre_archivo;
  if (!state.detail || next !== state.file) {
    await selectFile(next, state.version);
  }
}

async function loadAnalytics() {
  try {
    const data = await api('/api/analytics');
    $('stat-wan-savings').textContent = bytes(data.ahorro_delta_bytes || 0);
    $('stat-protected-files').textContent = data.total_protegidos || 0;
    $('stat-total-milestones').textContent = data.total_hitos || 0;
    $('stat-alerts-count').textContent = (data.riesgos.advertencia || 0) + (data.riesgos.critico || 0);
  } catch (err) {
    console.warn('No se pudo cargar analítica:', err);
  }
}

async function loadAudit() {
  $('audit-state').textContent = 'Cargando auditoría e inteligencia…';
  try {
    const filterFile = $('audit-filter').value;
    const filterDept = $('audit-dept-filter').value;
    const filterRisk = $('audit-risk-filter').value;

    let url = `/api/activity?limite=150`;
    if (filterFile) url += `&archivo=${encodeURIComponent(filterFile)}`;
    if (filterDept && filterDept !== 'Todos') url += `&departamento=${encodeURIComponent(filterDept)}`;
    if (filterRisk && filterRisk !== 'Todos') url += `&nivel_riesgo=${encodeURIComponent(filterRisk)}`;

    const data = await api(url);
    $('audit-rows').replaceChildren();
    $('audit-state').textContent = data.eventos.length ? '' : 'No hay eventos de auditoría para el criterio seleccionado.';

    // Llenar selector de archivos
    const currentOpt = $('audit-filter').value;
    $('audit-filter').replaceChildren(new Option('Todos los archivos', ''));
    for (const f of state.files) {
      $('audit-filter').add(new Option(f.nombre_archivo, f.nombre_archivo));
    }
    $('audit-filter').value = currentOpt;

    for (const ev of data.eventos) {
      const row = element('tr');
      row.append(
        element('td', 'font-bold', ev.nombre_archivo),
        element('td', '', ev.departamento || 'General'),
        element('td', '', operations[ev.tipo_operacion] || ev.tipo_operacion),
        element('td', '', `v${ev.numero_version}${ev.es_hito ? ' ⭐' : ''}`)
      );

      // Riesgo
      const riskTd = element('td');
      const pill = element('span', `risk-pill ${ev.nivel_riesgo?.toLowerCase() || 'normal'}`, ev.nivel_riesgo || 'NORMAL');
      riskTd.append(pill);
      if (ev.alerta_metadatos) {
        riskTd.append(element('small', 'text-red block', ev.alerta_metadatos));
      }
      row.append(riskTd);

      const authorTd = element('td', '', ev.usuario_so);
      authorTd.append(element('small', '', `${ev.nombre_equipo} · ${ev.direccion_ip}`));
      row.append(authorTd, element('td', '', date(ev.fecha_registro_utc)));

      const actionTd = element('td');
      const openBtn = element('button', 'button-link small', 'Ver versión');
      openBtn.type = 'button';
      openBtn.addEventListener('click', () => {
        switchView('files');
        selectFile(ev.nombre_archivo, ev.numero_version);
      });
      actionTd.append(openBtn);
      row.append(actionTd);

      $('audit-rows').append(row);
    }
  } catch (err) {
    $('audit-state').textContent = err.message;
  }
}

function switchView(viewName) {
  state.view = viewName;
  $('workspace').hidden = viewName !== 'files';
  $('audit-view').hidden = viewName !== 'audit';
  $('simulator-view').hidden = viewName !== 'simulator';
  $('architecture-view').hidden = viewName !== 'architecture';

  $('tab-files').classList.toggle('active', viewName === 'files');
  $('tab-audit').classList.toggle('active', viewName === 'audit');
  $('tab-simulator').classList.toggle('active', viewName === 'simulator');
  $('tab-architecture').classList.toggle('active', viewName === 'architecture');

  if (viewName === 'audit') {
    loadAnalytics();
    loadAudit();
  }
}

// Auto-organizar carpetas departamentales
$('btn-organize').addEventListener('click', async () => {
  $('btn-organize').disabled = true;
  $('btn-organize').textContent = 'Organizando…';
  try {
    const res = await api('/api/organize', {method: 'POST'});
    notice(`Organización completada: ${res.total} archivo(s) clasificado(s) en departamentos.`, true);
    await refresh();
  } catch (err) {
    notice(err.message);
  } finally {
    $('btn-organize').disabled = false;
    $('btn-organize').textContent = 'Auto-organizar';
  }
});

// Píldoras de departamento
document.querySelectorAll('.dept-pill').forEach(pill => {
  pill.addEventListener('click', () => {
    document.querySelectorAll('.dept-pill').forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    state.dept = pill.getAttribute('data-dept');
    renderFiles();
  });
});

// Congelar / Descongelar archivo
$('btn-toggle-protect').addEventListener('click', async () => {
  if (!state.file) return;
  const curFile = state.files.find(f => f.nombre_archivo === state.file);
  const newProt = !curFile?.protegido;
  try {
    await api(`/api/files/${encodeURIComponent(state.file)}/protect`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({protegido: newProt}),
    });
    notice(newProt ? `Archivo «${state.file}» congelado y auditado.` : `Archivo «${state.file}» abierto para edición.`, true);
    await refresh();
    await selectFile(state.file, state.version);
  } catch (err) {
    notice(err.message);
  }
});

// Compactar versiones menores
$('btn-compact').addEventListener('click', async () => {
  if (!state.file) return;
  if (!confirm(`¿Deseas compactar las versiones menores de «${state.file}»? Se conservarán la v1, la versión actual, todos los hitos fijados y restauraciones.`)) {
    return;
  }
  try {
    const res = await api(`/api/files/${encodeURIComponent(state.file)}/compact`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({mantener_recientes: 3}),
    });
    notice(`Compactación exitosa: ${res.versiones_eliminadas} micro-versiones podadas. ${res.versiones_restantes} conservadas.`, true);
    await selectFile(state.file);
  } catch (err) {
    notice(err.message);
  }
});

// Modal de Hitos
function openMilestoneDialog(verNum, currentIsHito, currentLabel) {
  state.activeMilestoneVer = verNum;
  if (currentIsHito) {
    // Si ya era hito, desmarcar
    api(`/api/files/${encodeURIComponent(state.file)}/versions/${verNum}/milestone`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({es_hito: false}),
    }).then(() => {
      notice(`Hito retirado de la versión v${verNum}.`);
      selectFile(state.file, state.version);
    }).catch(err => notice(err.message));
    return;
  }
  $('milestone-label-input').value = currentLabel || `Hito Formal v${verNum}`;
  $('milestone-dialog').showModal();
}

$('cancel-milestone').addEventListener('click', () => $('milestone-dialog').close());

$('milestone-form').addEventListener('submit', async e => {
  e.preventDefault();
  const label = $('milestone-label-input').value.trim();
  try {
    await api(`/api/files/${encodeURIComponent(state.file)}/versions/${state.activeMilestoneVer}/milestone`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({es_hito: true, etiqueta_hito: label}),
    });
    $('milestone-dialog').close();
    notice(`Versión v${state.activeMilestoneVer} fijada como hito inmutable: «${label}».`, true);
    await selectFile(state.file, state.version);
  } catch (err) {
    notice(err.message);
  }
});

// Modal Dictamen ISO 27001
$('btn-export-audit').addEventListener('click', async () => {
  try {
    $('cert-date').textContent = new Date().toUTCString();
    const analytics = await api('/api/analytics');
    const act = await api('/api/activity?limite=20');

    $('cert-stats').innerHTML = `
      <p>&bull; Total de versiones custodiadas: <strong>${$('total-versions').textContent}</strong> | Ahorro Delta WAN: <strong>${bytes(analytics.ahorro_delta_bytes)}</strong></p>
      <p>&bull; Incidentes Críticos Detectados: <strong>${analytics.riesgos.critico || 0}</strong> | Hitos Inmutables: <strong>${analytics.total_hitos || 0}</strong></p>
    `;

    $('cert-rows').replaceChildren();
    for (const ev of act.eventos) {
      const tr = element('tr');
      tr.innerHTML = `
        <td>${ev.nombre_archivo}</td>
        <td>${ev.departamento || 'General'}</td>
        <td>v${ev.numero_version}</td>
        <td>${ev.tipo_operacion}</td>
        <td class="font-mono">${(ev.content_hash || '').substring(0, 16)}...</td>
        <td>${ev.usuario_so} (${ev.direccion_ip})</td>
        <td>${ev.fecha_registro_utc}</td>
      `;
      $('cert-rows').append(tr);
    }
    $('cert-dialog').showModal();
  } catch (err) {
    notice(err.message);
  }
});

$('btn-close-cert').addEventListener('click', () => $('cert-dialog').close());
$('btn-print-window').addEventListener('click', () => window.print());

// Simulador de Ciberataque y Resiliencia
$('btn-sim-attack').addEventListener('click', async () => {
  $('sim-attack-result').hidden = false;
  $('sim-attack-result').textContent = 'Ejecutando infección simulada por ransomware LockBit…';
  try {
    const res = await api('/api/simulator/ransomware', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({nombre_archivo: state.file, modo: 'simular'}),
    });
    $('sim-attack-result').innerHTML = `⚠️ <strong>ALERTA GENERADA:</strong> ${res.mensaje}<br>Se alteró el archivo en disco. El agente detectó la firma y la catalogó como CRÍTICO.`;
    await refresh();
    await selectFile(res.nombre_archivo);
  } catch (err) {
    $('sim-attack-result').textContent = `Error: ${err.message}`;
  }
});

$('btn-sim-rollback').addEventListener('click', async () => {
  $('sim-attack-result').hidden = false;
  $('sim-attack-result').textContent = 'Ejecutando reversión transaccional en Dropbox Cloud API…';
  try {
    const res = await api('/api/simulator/ransomware', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({nombre_archivo: state.file, modo: 'rollback'}),
    });
    $('sim-attack-result').innerHTML = `✅ <strong>DESASTRE NEUTRALIZADO:</strong> ${res.mensaje}<br>Se restauró el archivo a su estado limpio anterior.`;
    await refresh();
    await selectFile(res.nombre_archivo);
  } catch (err) {
    $('sim-attack-result').textContent = `Error: ${err.message}`;
  }
});

$('btn-sim-tamper').addEventListener('click', async () => {
  if (!state.file) {
    alert('Selecciona primero un archivo en el explorador.');
    return;
  }
  $('sim-tamper-result').hidden = false;
  $('sim-tamper-result').textContent = 'Congelando archivo y simulando alteración no autorizada…';
  try {
    // 1. Proteger
    await api(`/api/files/${encodeURIComponent(state.file)}/protect`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({protegido: true}),
    });
    // 2. Modificar
    await api(`/api/files/${encodeURIComponent(state.file)}/save-content`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({contenido_texto: 'ALTERACION NO AUTORIZADA SOBRE BALANCE AUDITADO\n'}),
    });
    $('sim-tamper-result').innerHTML = `🚨 <strong>VIOLACIÓN DETECTADA:</strong> El archivo estaba congelado. El motor forense registró el evento con nivel <strong>CRÍTICO</strong> y alertó al auditor.`;
    await refresh();
    await selectFile(state.file);
  } catch (err) {
    $('sim-tamper-result').textContent = `Error: ${err.message}`;
  }
});

$('btn-sim-crash').addEventListener('click', () => {
  if (!state.file) {
    alert('Selecciona un archivo primero.');
    return;
  }
  const key = `cbas_draft_${state.file}`;
  localStorage.setItem(key, `// TRABAJO EN CURSO PREVIO AL APAGÓN DE ENERGÍA\nTotal estimado: 999999 Bs\n`);
  $('sim-crash-result').hidden = false;
  $('sim-crash-result').innerHTML = `⚡ <strong>SIMULACIÓN DE APAGÓN:</strong> Se guardó un borrador no enviado en <code>localStorage</code>.<br>Ve a la pestaña <em>"Editor & Autoguardado"</em> de «${state.file}» para ver el banner de rescate.`;
  changeMode('editor');
});

// Descargar versión
$('download').addEventListener('click', async e => {
  e.preventDefault();
  if (!state.detail || state.loading || state.restoring) return;
  $('download').textContent = 'Descargando…';
  try {
    const res = await fetch($('download').href, {signal: AbortSignal.timeout(45000)});
    if (!res.ok) throw new Error('No se pudo descargar la versión.');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const link = element('a');
    link.href = url;
    const name = state.file.split('/').pop();
    const dot = name.lastIndexOf('.');
    link.download = dot > 0 ? `${name.slice(0, dot)}_v${state.version}${name.slice(dot)}` : `${name}_v${state.version}`;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (err) {
    notice(err.message);
  } finally {
    $('download').textContent = 'Descargar versión';
  }
});

// Diálogo de restauración
$('restore').addEventListener('click', () => {
  if (!state.detail || state.loading || state.restoring) return;
  $('restore-description').textContent = `Vas a restaurar «${state.file}» hacia la versión v${state.version}.`;
  $('restore-dialog').showModal();
});
$('cancel-restore').addEventListener('click', () => $('restore-dialog').close());

$('restore-form').addEventListener('submit', async e => {
  e.preventDefault();
  if (state.restoring || !state.detail) return;
  state.restoring = true;
  lockActions();
  $('confirm-restore').disabled = true;
  $('confirm-restore').textContent = 'Restaurando…';
  try {
    const res = await api('/api/restore', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        nombre_archivo: state.file,
        rev: state.detail.version_seleccionada.rev_dropbox,
        numero_version: state.version
      }),
    });
    notice(`Restauración exitosa. «${state.file}» se recuperó como v${res.nueva_version.numero_version}.`, true);
    state.version = res.nueva_version.numero_version;
  } catch (err) {
    notice(err.message);
  } finally {
    state.restoring = false;
    $('restore-dialog').close();
    $('confirm-restore').disabled = false;
    $('confirm-restore').textContent = 'Sí, restaurar versión';
    lockActions();
    await refresh();
    await selectFile(state.file);
  }
});

// Eventos de barra de navegación
$('tab-files').addEventListener('click', () => switchView('files'));
$('tab-audit').addEventListener('click', () => switchView('audit'));
$('tab-simulator').addEventListener('click', () => switchView('simulator'));
$('tab-architecture').addEventListener('click', () => switchView('architecture'));

$('show-content').addEventListener('click', () => changeMode('content'));
$('show-diff').addEventListener('click', () => changeMode('diff'));
$('show-editor').addEventListener('click', () => changeMode('editor'));

$('search').addEventListener('input', renderFiles);
$('compare').addEventListener('change', () => {
  if (state.version) selectVersion(state.version);
});
$('audit-filter').addEventListener('change', loadAudit);
$('audit-dept-filter').addEventListener('change', loadAudit);
$('audit-risk-filter').addEventListener('change', loadAudit);

$('dismiss-notice').addEventListener('click', () => {
  $('notice').hidden = true;
});

async function refresh() {
  if (state.refreshing || state.loading || state.restoring || $('restore-dialog').open) return;
  state.refreshing = true;
  $('refresh').disabled = true;
  try {
    await Promise.all([
      loadStatus(),
      loadFiles(),
      state.view === 'audit' ? Promise.all([loadAnalytics(), loadAudit()]) : Promise.resolve()
    ]);
    $('last-refresh').textContent = `Actualizado ${new Intl.DateTimeFormat('es', {timeStyle: 'short'}).format(new Date())} · cada 15 s`;
  } catch (err) {
    notice(err.message);
  } finally {
    state.refreshing = false;
    $('refresh').disabled = false;
  }
}

$('refresh').addEventListener('click', refresh);
document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
setInterval(() => { if (!document.hidden) refresh(); }, 15000);

refresh();
