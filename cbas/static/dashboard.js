'use strict';

const $ = id => document.getElementById(id);

const state = {
  files: [],
  file: null,
  versions: [],
  version: null,
  detail: null,
  mode: 'content', // 'content', 'diff'
  view: 'files',   // 'files', 'audit', 'diagnostic'
  refreshing: false,
  restoring: false,
  loading: false,
  generation: 0,
  activeMilestoneVer: null,
};

const operations = {
  CREADO: 'Primer respaldo en la nube',
  MODIFICADO: 'Archivo modificado y respaldado',
  RESTAURADO: 'Versión restaurada desde la nube'
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
  const ext = (extension || '').toLowerCase().replace('.', '');
  let typeClass = 'file-icon-generic';
  let svgInner = '';

  if (['docx', 'doc'].includes(ext)) {
    typeClass = 'file-icon-word';
    svgInner = '<path d="M7 2h14l7 7v27H7V2Zm14 0v8h7M11 15h12M11 19h12M11 23h8" stroke="currentColor" stroke-width="1.6"/>';
  } else if (['xlsx', 'xls', 'csv'].includes(ext)) {
    typeClass = 'file-icon-excel';
    svgInner = '<path d="M7 2h14l7 7v27H7V2Zm14 0v8h7M11 15h12M11 20h12M11 25h12M17 15v10" stroke="currentColor" stroke-width="1.6"/>';
  } else if (ext === 'pdf') {
    typeClass = 'file-icon-pdf';
    svgInner = '<path d="M7 2h14l7 7v27H7V2Zm14 0v8h7M12 17a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM10 25v-4h4" stroke="currentColor" stroke-width="1.6"/>';
  } else if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext)) {
    typeClass = 'file-icon-image';
    svgInner = '<rect x="6" y="5" width="22" height="28" rx="3" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="11" r="2" fill="currentColor"/><path d="m8 27 6-8 4 5 3-3 5 6H8Z" stroke="currentColor" stroke-width="1.4"/>';
  } else if (['json', 'py', 'sql', 'sh', 'js'].includes(ext)) {
    typeClass = 'file-icon-code';
    svgInner = '<path d="M7 2h14l7 7v27H7V2Zm14 0v8h7M13 16l-3 3 3 3M19 16l3 3-3 3" stroke="currentColor" stroke-width="1.6"/>';
  } else if (ext === 'md') {
    typeClass = 'file-icon-md';
    svgInner = '<path d="M7 2h14l7 7v27H7V2Zm14 0v8h7M11 15v8l3-3 3 3v-8" stroke="currentColor" stroke-width="1.6"/>';
  } else {
    typeClass = 'file-icon-txt';
    svgInner = '<path d="M7 2h14l7 7v27H7V2Zm14 0v8h7M11 15h12M11 19h12M11 23h7" stroke="currentColor" stroke-width="1.6"/>';
  }

  const wrap = element('span', `file-icon ${typeClass}`);
  wrap.setAttribute('aria-hidden', 'true');
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 34 39');
  svg.setAttribute('fill', 'none');
  svg.innerHTML = svgInner;
  wrap.append(svg, element('span', '', ext.slice(0, 4).toUpperCase()));
  return wrap;
}

function renderFiles() {
  const list = $('file-list');
  list.replaceChildren();
  const query = $('search').value.trim().toLocaleLowerCase();

  let filtered = state.files;
  if (query) {
    filtered = filtered.filter(f => f.nombre_archivo.toLocaleLowerCase().includes(query));
  }

  $('file-count').textContent = filtered.length;
  if (!filtered.length) {
    list.append(element('p', 'empty small', query ? 'Ningún archivo coincide con tu búsqueda.' : 'No hay archivos monitoreados en la carpeta.'));
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
      const lock = element('span', 'file-lock-badge', ' [Auditado]');
      lock.title = 'Documento congelado / auditado';
      titleRow.append(lock);
    }

    const sub = element('span', 'file-sub', `${bytes(file.tamano_bytes)} · v${file.version_actual}`);
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
      header.append(element('span', 'milestone-badge', `[Hito] ${version.etiqueta_hito || ''}`));
    }
    if (version.nivel_riesgo === 'CRITICO') {
      header.append(element('span', 'risk-pill critico', 'CRÍTICO'));
    } else if (version.nivel_riesgo === 'ADVERTENCIA') {
      header.append(element('span', 'risk-pill advertencia', 'ALERTA'));
    }

    const dateSpan = element('span', 'version-date', date(version.fecha_registro_utc));
    const opSpan = element('span', 'version-operation', operations[version.tipo_operacion] || version.tipo_operacion);

    const actions = element('div', 'version-actions-row');
    const viewBtn = element('button', 'version-view-btn', 'Ver versión');
    viewBtn.type = 'button';
    viewBtn.addEventListener('click', e => {
      e.stopPropagation();
      if (!state.restoring) selectVersion(version.numero_version);
    });
    actions.append(viewBtn);

    const milestoneBtn = element('button', `milestone-btn${version.es_hito ? ' is-milestone' : ''}`, version.es_hito ? 'Quitar hito' : 'Marcar hito');
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
  $('show-content').setAttribute('aria-pressed', String(mode === 'content'));
  $('show-diff').setAttribute('aria-pressed', String(mode === 'diff'));

  $('preview').hidden = mode !== 'content';
  $('diff-view').hidden = mode !== 'diff';
  $('compare-label').hidden = mode !== 'diff';
}

function renderDetail() {
  const data = state.detail;
  const v = data.version_seleccionada;
  const curFile = state.files.find(f => f.nombre_archivo === state.file);

  $('file-name').textContent = state.file;
  $('file-type').textContent = state.file.split('.').pop().toUpperCase();

  // Botón proteger / congelar
  const isProtected = curFile?.protegido;
  $('btn-toggle-protect').className = `protect-btn${isProtected ? ' protected' : ''}`;
  $('btn-toggle-protect').textContent = isProtected ? '[Solo lectura / Auditado]' : '[Edición permitida]';

  $('file-meta').textContent = `Versión ${v.numero_version} · ${bytes(v.tamano_bytes)} · ${date(v.fecha_registro_utc)}`;

  // Alerta de riesgo / anomalía
  const alertBanner = $('file-risk-alert');
  if (v.nivel_riesgo && v.nivel_riesgo !== 'NORMAL') {
    alertBanner.hidden = false;
    alertBanner.className = `risk-banner ${v.nivel_riesgo === 'CRITICO' ? 'risk-critico' : 'risk-advertencia'}`;
    alertBanner.textContent = `[${v.nivel_riesgo}] ${v.alerta_metadatos || 'Anomalía de integridad detectada en esta versión.'}`;
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
    ['Estado', isProtected ? 'CONGELADO / AUDITADO' : 'ACTIVO'],
    ['Estructura de Contenido', data.metadatos_analiticos?.resumen_estructural || '—'],
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
  if (data.metadatos_analiticos?.total_palabras) {
    details.splice(3, 0, ['Volumen de Datos', `${data.metadatos_analiticos.total_palabras} palabras · ${data.metadatos_analiticos.total_lineas || 0} líneas`]);
  }
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
    const sync = data.sincronizacion;
    const activeSessions = sync.sesiones_activas || 0;

    $('connection').className = `connection ${data.dropbox.conectado ? 'connected' : 'offline'}`;
    $('connection-text').textContent = data.dropbox.conectado ? 'Dropbox conectado' : 'Dropbox sin conexión';
    $('total-files').textContent = data.resumen.total_archivos;
    $('total-versions').textContent = data.resumen.total_versiones;
    $('total-milestones').textContent = data.resumen.total_hitos || 0;
    $('total-savings').textContent = bytes(data.resumen.ahorro_delta_bytes || 0);
    $('folder-path').textContent = data.directorio_monitoreado;

    if (activeSessions > 0) {
      $('session-status').textContent = `Sesión activa: ${activeSessions} archivo(s) en edición en disco.`;
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
  populateDiagnosticSelects();

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
    const filterRisk = $('audit-risk-filter').value;

    let url = `/api/activity?limite=150`;
    if (filterFile) url += `&archivo=${encodeURIComponent(filterFile)}`;
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
        element('td', '', operations[ev.tipo_operacion] || ev.tipo_operacion),
        element('td', '', `v${ev.numero_version}${ev.es_hito ? ' [Hito]' : ''}`)
      );

      // Estado / Alerta
      const riskTd = element('td');
      const isCritical = ev.nivel_riesgo === 'CRITICO';
      const isWarning = ev.nivel_riesgo === 'ADVERTENCIA';
      const pillLabel = isCritical ? 'Alerta de seguridad' : isWarning ? 'Advertencia' : 'Normal';
      const pill = element('span', `risk-pill ${ev.nivel_riesgo?.toLowerCase() || 'normal'}`, pillLabel);
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

function populateDiagnosticSelects() {
  const selFile = $('diag-file-select');
  const selCompact = $('diag-compact-select');
  if (!selFile || !selCompact) return;

  const currentFileVal = selFile.value || state.file;
  const currentCompactVal = selCompact.value || state.file;

  selFile.replaceChildren();
  selCompact.replaceChildren();

  if (!state.files || !state.files.length) {
    selFile.append(new Option('No hay archivos monitoreados', ''));
    selCompact.append(new Option('No hay archivos monitoreados', ''));
    return;
  }

  for (const f of state.files) {
    selFile.append(new Option(f.nombre_archivo, f.nombre_archivo));
    selCompact.append(new Option(f.nombre_archivo, f.nombre_archivo));
  }

  if (currentFileVal && state.files.some(f => f.nombre_archivo === currentFileVal)) {
    selFile.value = currentFileVal;
  }
  if (currentCompactVal && state.files.some(f => f.nombre_archivo === currentCompactVal)) {
    selCompact.value = currentCompactVal;
  }
}

async function loadDiagnosticView() {
  populateDiagnosticSelects();
  try {
    const statusData = await api('/api/status');
    if (statusData.dropbox) {
      const dbx = statusData.dropbox;
      $('kpi-dbx-badge').textContent = dbx.conectado ? 'Conectado' : 'Sin conexión';
      $('kpi-dbx-badge').className = `kpi-badge ${dbx.conectado ? 'kpi-badge-ok' : 'kpi-badge-danger'}`;
      $('kpi-dbx-account').textContent = dbx.nombre_mostrar || dbx.email || 'Dropbox Cloud';
      $('kpi-dbx-vault').textContent = `Bóveda: ${dbx.carpeta_boveda || '/CBAS_Pyme_Vault'}`;
      $('kpi-storage-val').textContent = `${dbx.espacio_usado_mb || 0} MB en uso`;
    }
    const analytics = await api('/api/analytics').catch(() => null);
    if (analytics) {
      $('kpi-storage-sub').textContent = `Ahorro delta sync: ${bytes(analytics.ahorro_delta_bytes)}`;
    }
  } catch (err) {
    // Continuar si falla un indicador secundario
  }
  await runIntegrityCheck();
}

async function runIntegrityCheck() {
  const container = $('integrity-results');
  container.innerHTML = '<p class="loading">Comprobando archivos locales contra Dropbox Cloud…</p>';
  try {
    const data = await api('/api/diagnostic/integrity');

    // Actualizar indicador de cabecera y tarjeta de salud
    const tag = $('integrity-summary-tag');
    if (data.discrepancias > 0) {
      tag.textContent = `${data.discrepancias} discrepancia(s) detectada(s)`;
      tag.className = 'summary-tag tag-danger';
      $('kpi-health-badge').textContent = 'Atención Requerida';
      $('kpi-health-badge').className = 'kpi-badge kpi-badge-danger';
      $('kpi-health-val').textContent = `${data.discrepancias} archivo(s) alterado(s)`;
      $('kpi-health-sub').textContent = 'Requieren restauración desde la nube';
    } else {
      tag.textContent = `${data.total_archivos} archivos al día`;
      tag.className = 'summary-tag tag-ok';
      $('kpi-health-badge').textContent = '100% Íntegros';
      $('kpi-health-badge').className = 'kpi-badge kpi-badge-ok';
      $('kpi-health-val').textContent = `${data.integros} de ${data.total_archivos} verificados`;
      $('kpi-health-sub').textContent = 'Coinciden exactamente con Dropbox Cloud';
    }

    container.replaceChildren();
    const tableWrap = element('div', 'table-scroll');
    const table = element('table', 'diag-health-table');
    table.innerHTML = `
      <colgroup>
        <col style="width: 36%;">
        <col style="width: 14%;">
        <col style="width: 14%;">
        <col style="width: 22%;">
        <col style="width: 14%;">
      </colgroup>
      <thead>
        <tr>
          <th>Archivo</th>
          <th>Tamaño</th>
          <th>Versión en Nube</th>
          <th>Estado</th>
          <th>Acción</th>
        </tr>
      </thead>
      <tbody></tbody>
    `;
    const tbody = table.querySelector('tbody');

    for (const item of data.archivos) {
      const tr = element('tr');
      if (item.estado !== 'INTEGRO') {
        tr.classList.add('row-alert');
      }

      // Columna 1: Icono de formato + Nombre
      const tdFile = element('td', 'cell-diag-file');
      const ext = item.nombre_archivo.includes('.') ? item.nombre_archivo.split('.').pop() : '';
      const icon = fileIcon(ext);
      const nameSpan = element('span', 'diag-filename', item.nombre_archivo);
      tdFile.append(icon, nameSpan);

      // Columna 2: Tamaño
      const tdSize = element('td', 'cell-diag-size', bytes(item.tamano_bytes));

      // Columna 3: Versión
      const tdVer = element('td', 'cell-diag-ver', item.version_actual ? `v${item.version_actual}` : 'Pendiente');

      // Columna 4: Estado
      const tdStatus = element('td', 'cell-diag-status');
      let statusClass = 'badge-status-ok';
      let statusLabel = 'Al día en Dropbox';

      if (item.estado === 'DISCREPANCIA') {
        statusClass = 'badge-status-danger';
        statusLabel = 'Modificado / Alterado';
      } else if (item.estado === 'PENDIENTE_SINCRONIZACION') {
        statusClass = 'badge-status-warning';
        statusLabel = 'Pendiente de subir';
      } else if (item.estado === 'ERROR_LECTURA') {
        statusClass = 'badge-status-danger';
        statusLabel = 'Error de lectura';
      }
      const badge = element('span', `diag-badge ${statusClass}`, statusLabel);
      tdStatus.append(badge);

      // Columna 5: Acción rápida
      const tdAction = element('td', 'cell-diag-action');
      if (item.estado === 'DISCREPANCIA') {
        const btnFix = element('button', 'button-link danger small', 'Restaurar');
        btnFix.type = 'button';
        btnFix.title = 'Restaurar versión limpia desde Dropbox';
        btnFix.addEventListener('click', async () => {
          $('diag-file-select').value = item.nombre_archivo;
          $('btn-recovery-restore').click();
        });
        tdAction.append(btnFix);
      } else {
        const btnView = element('button', 'button-link small', 'Ver archivo');
        btnView.type = 'button';
        btnView.addEventListener('click', async () => {
          switchView('files');
          await selectFile(item.nombre_archivo);
        });
        tdAction.append(btnView);
      }

      tr.append(tdFile, tdSize, tdVer, tdStatus, tdAction);
      tbody.append(tr);
    }

    tableWrap.append(table);
    container.append(tableWrap);
  } catch (err) {
    container.innerHTML = `<p class="text-red">Error en la comprobación: ${err.message}</p>`;
  }
}

function switchView(viewName) {
  state.view = viewName;
  $('workspace').hidden = viewName !== 'files';
  $('audit-view').hidden = viewName !== 'audit';
  $('diagnostic-view').hidden = viewName !== 'diagnostic';

  $('tab-files').classList.toggle('active', viewName === 'files');
  $('tab-audit').classList.toggle('active', viewName === 'audit');
  $('tab-diagnostic').classList.toggle('active', viewName === 'diagnostic');

  if (viewName === 'audit') {
    loadAnalytics();
    loadAudit();
  } else if (viewName === 'diagnostic') {
    loadDiagnosticView();
  }
}

// Proteger / Desproteger archivo
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
  if (!confirm(`¿Deseas podar las versiones intermedias de «${state.file}»? Se conservarán la v1, la versión actual y todos los hitos formalmente fijados.`)) {
    return;
  }
  try {
    const res = await api(`/api/files/${encodeURIComponent(state.file)}/compact`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({mantener_recientes: 3}),
    });
    notice(`Poda completada: ${res.versiones_eliminadas} micro-versiones eliminadas. ${res.versiones_restantes} conservadas.`, true);
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

// Modal Reporte / Resumen de Actividad
$('btn-export-audit').addEventListener('click', async () => {
  try {
    $('cert-date').textContent = new Date().toLocaleString('es-ES', {
      dateStyle: 'long',
      timeStyle: 'short'
    });
    const analytics = await api('/api/analytics');
    const act = await api('/api/activity?limite=20');

    $('cert-stats').innerHTML = `
      <div class="cert-stat-item">
        <span class="stat-num">${analytics.total_versiones ?? 0}</span>
        <span class="stat-lbl">Versiones en nube</span>
      </div>
      <div class="cert-stat-item">
        <span class="stat-num">${bytes(analytics.ahorro_delta_bytes)}</span>
        <span class="stat-lbl">Ahorro de red</span>
      </div>
      <div class="cert-stat-item">
        <span class="stat-num">${analytics.total_protegidos ?? 0}</span>
        <span class="stat-lbl">Archivos protegidos</span>
      </div>
      <div class="cert-stat-item">
        <span class="stat-num">${analytics.total_hitos ?? 0}</span>
        <span class="stat-lbl">Hitos fijados</span>
      </div>
    `;

    $('cert-rows').replaceChildren();
    for (const ev of (act.eventos || [])) {
      const tr = element('tr');

      const tdFile = element('td', 'cell-filename', ev.nombre_archivo);
      const tdVer = element('td', 'cell-ver', `v${ev.numero_version}`);
      const tdOp = element('td', 'cell-action', operations[ev.tipo_operacion] || ev.tipo_operacion);

      const tdUser = element('td', 'cell-user');
      tdUser.append(document.createTextNode(ev.usuario_so || 'Sistema '));
      if (ev.nombre_equipo) {
        const sub = element('span', 'cell-sub', `(${ev.nombre_equipo})`);
        tdUser.append(sub);
      }

      const tdDate = element('td', 'cell-date', date(ev.fecha_registro_utc));

      tr.append(tdFile, tdVer, tdOp, tdUser, tdDate);
      $('cert-rows').append(tr);
    }
    $('cert-dialog').showModal();
  } catch (err) {
    notice(`No se pudo generar el resumen: ${err.message}`);
  }
});

$('btn-close-cert').addEventListener('click', () => $('cert-dialog').close());
$('btn-print-window').addEventListener('click', () => window.print());

// Vista de Salud y Recuperación
$('btn-check-integrity').addEventListener('click', runIntegrityCheck);

$('btn-recovery-alter').addEventListener('click', async () => {
  const chosenFile = $('diag-file-select')?.value || state.file;
  if (!chosenFile) {
    notice('Selecciona un archivo para la prueba.');
    return;
  }
  const resBox = $('recovery-test-result');
  resBox.hidden = false;
  resBox.className = 'lab-status-box status-loading';
  resBox.textContent = `Aplicando alteración de prueba en «${chosenFile}»…`;
  try {
    const res = await api('/api/diagnostic/recovery-test', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({nombre_archivo: chosenFile, modo: 'alterar'}),
    });
    resBox.className = 'lab-status-box status-alter';
    resBox.innerHTML = `
      <strong>Paso 2 completado: Archivo alterado</strong><br>
      Se introdujo una modificación en el archivo local «${chosenFile}». El agente en segundo plano detectó la alteración y generó alerta de seguridad.<br>
      Comprueba arriba en la tabla cómo se marca la discrepancia en rojo.<br>
      <em>Presiona ahora <strong>Paso 3 (Restaurar Versión Sana)</strong> para revertir el daño usando la copia de Dropbox.</em>
    `;
    await refresh();
    await runIntegrityCheck();
  } catch (err) {
    resBox.className = 'lab-status-box status-error';
    resBox.textContent = `Error: ${err.message}`;
  }
});

$('btn-recovery-restore').addEventListener('click', async () => {
  const chosenFile = $('diag-file-select')?.value || state.file;
  if (!chosenFile) {
    notice('Selecciona un archivo para la prueba.');
    return;
  }
  const resBox = $('recovery-test-result');
  resBox.hidden = false;
  resBox.className = 'lab-status-box status-loading';
  resBox.textContent = `Descargando y restaurando versión sana desde Dropbox para «${chosenFile}»…`;
  try {
    const res = await api('/api/diagnostic/recovery-test', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({nombre_archivo: chosenFile, modo: 'restaurar'}),
    });
    resBox.className = 'lab-status-box status-restored';
    resBox.innerHTML = `
      <strong>Paso 3 completado con éxito: Archivo restaurado</strong><br>
      Se descargó la versión limpia custodiada en Dropbox Cloud y se reparó el archivo local «${chosenFile}».<br>
      La integridad ha quedado restablecida al 100%.
    `;
    await refresh();
    await runIntegrityCheck();
  } catch (err) {
    resBox.className = 'lab-status-box status-error';
    resBox.textContent = `Error: ${err.message}`;
  }
});

$('btn-run-compact').addEventListener('click', async () => {
  const targetFile = $('diag-compact-select')?.value || state.file;
  if (!targetFile) {
    notice('Selecciona un archivo para podar.');
    return;
  }
  if (!confirm(`¿Deseas optimizar las versiones de «${targetFile}»? Se eliminarán borradores intermedios pero se conservarán la v1, la versión actual y todos los hitos.`)) {
    return;
  }
  const resBox = $('compact-result');
  resBox.hidden = false;
  resBox.className = 'lab-status-box status-loading';
  resBox.textContent = `Optimizando árbol de versiones para «${targetFile}»…`;
  try {
    const res = await api(`/api/files/${encodeURIComponent(targetFile)}/compact`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({mantener_recientes: 3}),
    });
    resBox.className = 'lab-status-box status-compacted';
    resBox.innerHTML = `
      <strong>Optimización completada</strong><br>
      Se podaron ${res.versiones_eliminadas} micro-versiones intermedias.<br>
      Se conservaron ${res.versiones_restantes} versiones importantes (incluyendo versión inicial e hitos).
    `;
    notice(`Optimización lista para «${targetFile}»: ${res.versiones_eliminadas} podadas.`, true);
    await refresh();
    await runIntegrityCheck();
  } catch (err) {
    resBox.className = 'lab-status-box status-error';
    resBox.textContent = `Error: ${err.message}`;
  }
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
    $('download').textContent = 'Descargar copia';
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
$('tab-diagnostic').addEventListener('click', () => switchView('diagnostic'));

$('show-content').addEventListener('click', () => changeMode('content'));
$('show-diff').addEventListener('click', () => changeMode('diff'));

$('search').addEventListener('input', renderFiles);
$('compare').addEventListener('change', () => {
  if (state.version) selectVersion(state.version);
});
$('audit-filter').addEventListener('change', loadAudit);
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
      state.view === 'audit' ? Promise.all([loadAnalytics(), loadAudit()]) : Promise.resolve(),
      state.view === 'diagnostic' ? runIntegrityCheck() : Promise.resolve()
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