const API_BASE = (import.meta.env.VITE_RADICACION_API_URL || '').replace(/\/$/, '');

function api(path) {
  return `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`;
}

const jobs = {};
let statTotal = 0, statOk = 0, statFail = 0;

// ── API health ────────────────────────────────────────────────────────────

async function pingAPI() {
  try {
    const r = await fetch(api('/health'));
    const ok = r.ok;
    document.getElementById('api-dot').style.background = ok ? '#4ade80' : '#f87171';
    document.getElementById('api-label').textContent = ok ? 'api · online' : 'api · offline';
  } catch {
    document.getElementById('api-dot').style.background = '#f87171';
    document.getElementById('api-label').textContent = 'api · offline';
  }
}

// ── Dates ─────────────────────────────────────────────────────────────────

function calcDias() {
  const ini = document.getElementById('fecha_inicio').value;
  const fin = document.getElementById('fecha_fin').value;
  if (ini && fin) {
    const diff = (new Date(fin) - new Date(ini)) / 86400000;
    if (diff >= 0) document.getElementById('dias').value = String(diff + 1);
  }
}

function toPortalDate(iso) {
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}

// ── File drops ────────────────────────────────────────────────────────────

function setupDrop(dropId, inputId, textId) {
  const drop = document.getElementById(dropId);
  const input = document.getElementById(inputId);
  const text = document.getElementById(textId);
  input.addEventListener('change', () => {
    if (input.files[0]) { text.textContent = input.files[0].name; drop.classList.add('has-file'); }
  });
  drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('dragover'); });
  drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
  drop.addEventListener('drop', e => {
    e.preventDefault(); drop.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) {
      const dt = new DataTransfer(); dt.items.add(file);
      input.files = dt.files;
      text.textContent = file.name; drop.classList.add('has-file');
    }
  });
}

// ── Transcripción toggle ──────────────────────────────────────────────────

function setupToggle() {
  const toggle = document.getElementById('toggle-transcripcion');
  const fields = document.getElementById('transcripcion-fields');
  toggle.addEventListener('change', () => {
    fields.classList.toggle('visible', toggle.checked);
  });
}

// ── Submit ────────────────────────────────────────────────────────────────

async function radicar() {
  const btn = document.getElementById('btn-radicar');
  const esTranscripcion = document.getElementById('toggle-transcripcion').checked;

  const f = {
    tipo_doc_empleador: document.getElementById('tipo_doc_empleador').value,
    num_doc_empleador: document.getElementById('num_doc_empleador').value.trim(),
    clave: document.getElementById('clave').value,
    tipo_doc_trabajador: document.getElementById('tipo_doc_trabajador').value,
    cedula: document.getElementById('cedula').value.trim(),
    prefijo_incap: document.getElementById('prefijo_incap').value.trim(),
    numero_incap: document.getElementById('numero_incap').value.trim(),
    fecha_inicio: document.getElementById('fecha_inicio').value,
    fecha_fin: document.getElementById('fecha_fin').value,
    dias: document.getElementById('dias').value,
  };

  // Validación
  const required = [
    [f.tipo_doc_empleador, 'Tipo de documento del empleador'],
    [f.num_doc_empleador, 'Número de documento del empleador'],
    [f.clave, 'Clave del portal'],
    [f.cedula, 'N° documento del trabajador'],
    [f.prefijo_incap, 'Prefijo del número de incapacidad'],
    [f.numero_incap, 'Número de incapacidad'],
    [f.fecha_inicio, 'Fecha inicio'],
    [f.fecha_fin, 'Fecha fin'],
  ];
  for (const [val, label] of required) {
    if (!val) { alert(`Campo requerido: ${label}`); return; }
  }

  const pdfIncap = document.getElementById('pdf_incap').files[0];
  if (esTranscripcion && !pdfIncap) {
    alert('Para transcripciones se debe adjuntar el PDF de la incapacidad.');
    return;
  }

  const fd = new FormData();
  fd.append('tipo_documento_empleador', f.tipo_doc_empleador);
  fd.append('numero_documento_empleador', f.num_doc_empleador);
  fd.append('clave_empleador', f.clave);
  fd.append('tipo_documento_trabajador', f.tipo_doc_trabajador);
  fd.append('cedula_trabajador', f.cedula);
  fd.append('prefijo_incapacidad', f.prefijo_incap);
  fd.append('numero_incapacidad', f.numero_incap);
  fd.append('fecha_inicio', toPortalDate(f.fecha_inicio));
  fd.append('fecha_fin', toPortalDate(f.fecha_fin));
  fd.append('dias_incapacidad', f.dias);
  fd.append('es_transcripcion', esTranscripcion ? 'true' : 'false');
  if (pdfIncap) fd.append('pdf_incapacidad', pdfIncap);
  const pdfHist = document.getElementById('pdf_historia').files[0];
  if (pdfHist) fd.append('pdf_historia_clinica', pdfHist);

  btn.disabled = true;
  btn.textContent = 'ENVIANDO...';

  try {
    const r = await fetch(api('/api/radicar/sura'), { method: 'POST', body: fd });
    let data;
    try { data = await r.json(); } catch { throw new Error(`Respuesta no JSON (${r.status})`); }
    if (!r.ok) throw new Error(data?.detail ?? JSON.stringify(data));
    if (data.job_id) {
      addLogEntry(data.job_id, f.cedula, `${f.prefijo_incap}-${f.numero_incap}`, esTranscripcion);
      pollJob(data.job_id);
    }
  } catch (e) {
    alert(`Error al conectar con la API: ${e.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = 'RADICAR INCAPACIDAD →';
  }
}

// ── Log entries ───────────────────────────────────────────────────────────

function addLogEntry(jobId, cedula, numIncap, esTranscripcion) {
  document.getElementById('empty-state')?.remove();
  statTotal++;
  document.getElementById('stat-total').textContent = String(statTotal);
  jobs[jobId] = 'procesando';

  const container = document.getElementById('log-entries');
  const el = document.createElement('div');
  el.className = 'log-entry procesando';
  el.id = `job-${jobId}`;
  el.innerHTML = `
    <div class="log-status-icon procesando"><div class="spinner"></div></div>
    <div class="log-body">
      <div class="log-title">CC ${cedula} · ${numIncap}</div>
      <div class="log-sub" id="msg-${jobId}">procesando radicación...</div>
    </div>
    <div class="log-badge${esTranscripcion ? ' transcripcion' : ''}">
      ${esTranscripcion ? 'TRANSCRIPT.' : 'SURA'}
    </div>
  `;
  container.insertBefore(el, container.firstChild);
}

function updateLogEntry(jobId, status, msg, radicado) {
  const el = document.getElementById(`job-${jobId}`);
  if (!el) return;
  el.className = `log-entry ${status}`;
  const icon = el.querySelector('.log-status-icon');
  icon.className = `log-status-icon ${status}`;
  if (status === 'exitoso') {
    icon.innerHTML = '✓';
    statOk++;
    document.getElementById('stat-ok').textContent = String(statOk);
  } else {
    icon.innerHTML = '✕';
    statFail++;
    document.getElementById('stat-fail').textContent = String(statFail);
  }
  const msgEl = document.getElementById(`msg-${jobId}`);
  if (radicado) {
    msgEl.className = 'log-sub success';
    msgEl.textContent = `Radicado: ${radicado}`;
  } else {
    msgEl.className = 'log-sub danger';
    msgEl.textContent = msg;
  }
}

function clearLog() {
  document.getElementById('log-entries').innerHTML =
    `<div class="empty-state" id="empty-state"><div class="empty-icon">◎</div><span>Sin radicaciones aún</span></div>`;
  statTotal = statOk = statFail = 0;
  ['stat-total', 'stat-ok', 'stat-fail'].forEach(id => document.getElementById(id).textContent = '0');
}

function pollJob(jobId) {
  let attempts = 0;
  const interval = setInterval(async () => {
    if (++attempts > 120) { clearInterval(interval); return; }
    try {
      const r = await fetch(api(`/api/estado/${jobId}`));
      const data = await r.json();
      if (data.status !== 'procesando') {
        clearInterval(interval);
        updateLogEntry(jobId, data.status, data.mensaje, data.numero_radicado);
      }
    } catch { /* retry */ }
  }, 3000);
}

// ── Init ──────────────────────────────────────────────────────────────────

function init() {
  pingAPI();
  setInterval(pingAPI, 15000);
  document.getElementById('fecha_inicio').addEventListener('change', calcDias);
  document.getElementById('fecha_fin').addEventListener('change', calcDias);
  setupDrop('drop-incap', 'pdf_incap', 'drop-incap-text');
  setupDrop('drop-historia', 'pdf_historia', 'drop-historia-text');
  setupToggle();
  document.getElementById('btn-radicar').addEventListener('click', () => void radicar());
  document.getElementById('btn-clear').addEventListener('click', clearLog);
}

init();
