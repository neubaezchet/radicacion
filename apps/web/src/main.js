const API_BASE = (import.meta.env.VITE_RADICACION_API_URL || '').replace(/\/$/, '');

function api(path) {
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE}${p}`;
}

const jobs = {};
let statTotal = 0;
let statOk = 0;
let statFail = 0;

async function pingAPI() {
  try {
    const r = await fetch(api('/health'));
    if (r.ok) {
      document.getElementById('api-dot').style.background = '#4ade80';
      document.getElementById('api-label').textContent = 'api · online';
    } else {
      throw new Error('bad status');
    }
  } catch {
    document.getElementById('api-dot').style.background = '#f87171';
    document.getElementById('api-label').textContent = 'api · offline';
  }
}

function calcDias() {
  const ini = document.getElementById('fecha_inicio').value;
  const fin = document.getElementById('fecha_fin').value;
  if (ini && fin) {
    const diff = (new Date(fin) - new Date(ini)) / 86400000;
    if (diff >= 0) document.getElementById('dias').value = String(diff + 1);
  }
}

function setupDrop(dropId, inputId, textId) {
  const drop = document.getElementById(dropId);
  const input = document.getElementById(inputId);
  const text = document.getElementById(textId);
  input.addEventListener('change', () => {
    if (input.files[0]) {
      text.textContent = input.files[0].name;
      drop.classList.add('has-file');
    }
  });
  drop.addEventListener('dragover', (e) => {
    e.preventDefault();
    drop.classList.add('dragover');
  });
  drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
  drop.addEventListener('drop', (e) => {
    e.preventDefault();
    drop.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) {
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      text.textContent = file.name;
      drop.classList.add('has-file');
    }
  });
}

function formatFecha(iso) {
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}

async function radicar() {
  const btn = document.getElementById('btn-radicar');
  const fields = {
    nit: document.getElementById('nit').value.trim(),
    clave: document.getElementById('clave').value,
    cedula: document.getElementById('cedula').value.trim(),
    num_incap: document.getElementById('num_incap').value.trim(),
    fecha_inicio: document.getElementById('fecha_inicio').value,
    fecha_fin: document.getElementById('fecha_fin').value,
    dias: document.getElementById('dias').value,
  };
  const pdfIncap = document.getElementById('pdf_incap').files[0];

  if (
    !fields.nit ||
    !fields.clave ||
    !fields.cedula ||
    !fields.num_incap ||
    !fields.fecha_inicio ||
    !fields.fecha_fin ||
    !pdfIncap
  ) {
    alert('Completa todos los campos obligatorios y sube el PDF de la incapacidad.');
    return;
  }

  const fd = new FormData();
  fd.append('nit_empleador', fields.nit);
  fd.append('clave_empleador', fields.clave);
  fd.append('cedula_trabajador', fields.cedula);
  fd.append('numero_incapacidad', fields.num_incap);
  fd.append('fecha_inicio', formatFecha(fields.fecha_inicio));
  fd.append('fecha_fin', formatFecha(fields.fecha_fin));
  fd.append('dias_incapacidad', fields.dias);
  fd.append('pdf_incapacidad', pdfIncap);
  const pdfHist = document.getElementById('pdf_historia').files[0];
  if (pdfHist) fd.append('pdf_historia_clinica', pdfHist);

  btn.disabled = true;
  btn.textContent = 'ENVIANDO...';

  try {
    const r = await fetch(api('/api/radicar/sura'), { method: 'POST', body: fd });
    let data;
    try {
      data = await r.json();
    } catch {
      throw new Error(`Respuesta no JSON (${r.status})`);
    }
    if (!r.ok) {
      const detail = data?.detail ?? JSON.stringify(data);
      throw new Error(detail);
    }
    if (data.job_id) {
      addLogEntry(data.job_id, fields.cedula, fields.num_incap);
      pollJob(data.job_id);
    }
  } catch (e) {
    alert(`Error al conectar con la API: ${e.message}`);
  } finally {
    btn.disabled = false;
    btn.textContent = 'RADICAR INCAPACIDAD →';
  }
}

function addLogEntry(jobId, cedula, numIncap) {
  document.getElementById('empty-state')?.remove();
  statTotal += 1;
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
    <div class="log-eps">SURA</div>
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
    statOk += 1;
    document.getElementById('stat-ok').textContent = String(statOk);
  } else {
    icon.innerHTML = '✕';
    statFail += 1;
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
  const container = document.getElementById('log-entries');
  container.innerHTML = `<div class="empty-state" id="empty-state"><div class="empty-icon">◎</div><span>Sin radicaciones aún</span></div>`;
  statTotal = 0;
  statOk = 0;
  statFail = 0;
  document.getElementById('stat-total').textContent = '0';
  document.getElementById('stat-ok').textContent = '0';
  document.getElementById('stat-fail').textContent = '0';
}

function pollJob(jobId) {
  let attempts = 0;
  const interval = setInterval(async () => {
    attempts += 1;
    if (attempts > 120) {
      clearInterval(interval);
      return;
    }
    try {
      const r = await fetch(api(`/api/estado/${jobId}`));
      const data = await r.json();
      if (data.status !== 'procesando') {
        clearInterval(interval);
        updateLogEntry(jobId, data.status, data.mensaje, data.numero_radicado);
      }
    } catch {
      /* continuar intentando */
    }
  }, 3000);
}

function warnMissingApiUrl() {
  if (import.meta.env.DEV) return;
  const base = (import.meta.env.VITE_RADICACION_API_URL || '').trim();
  if (base) return;
  const banner = document.createElement('div');
  banner.setAttribute('role', 'alert');
  banner.style.cssText =
    'background:#3d1a1a;color:#fecaca;padding:10px 16px;text-align:center;font-family:IBM Plex Mono,monospace;font-size:12px;border-bottom:1px solid #f87171';
  banner.textContent =
    'Falta VITE_RADICACION_API_URL en Vercel (Settings → Environment Variables). Redeploy después de guardar.';
  document.body.insertBefore(banner, document.body.firstChild);
}

function init() {
  warnMissingApiUrl();
  pingAPI();
  setInterval(pingAPI, 15000);

  document.getElementById('fecha_fin').addEventListener('change', calcDias);
  document.getElementById('fecha_inicio').addEventListener('change', calcDias);
  setupDrop('drop-incap', 'pdf_incap', 'drop-incap-text');
  setupDrop('drop-historia', 'pdf_historia', 'drop-historia-text');
  document.getElementById('btn-radicar').addEventListener('click', () => void radicar());
  document.getElementById('btn-clear').addEventListener('click', clearLog);
}

init();
