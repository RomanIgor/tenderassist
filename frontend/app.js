const API = 'http://localhost:5000';

function navigate(viewId, el, label) {
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  if (el) el.classList.add('active');
  const view = document.getElementById('view-' + viewId);
  if (view) { view.classList.add('active'); }
  document.getElementById('breadcrumbCurrent').textContent = label;
  if (viewId === 'database') loadTendersFromDB();
}

async function checkBackend() {
  try {
    const r = await fetch(`${API}/api/health`, { signal: AbortSignal.timeout(2000) });
    const d = await r.json();
    if (d.status === 'ok') {
      document.querySelector('.status-pill').innerHTML = '<div class="status-dot"></div>Backend aktiv · lokal';
    }
  } catch {
    document.querySelector('.status-pill').innerHTML = '⚠ Backend offline';
    document.querySelector('.status-pill').style.color = 'var(--amber)';
    document.querySelector('.status-pill').style.background = 'var(--amber-soft)';
    document.querySelector('.status-pill').style.borderColor = '#FDE68A';
  }
}
checkBackend();

let lastFile = null;
let lastAnalysisData = null;

function handleDrop(ev) {
  ev.preventDefault();
  document.getElementById('uploadZone').classList.remove('drag');
  const file = ev.dataTransfer.files[0];
  if (file) { lastFile = file; startRealAnalysis(file); }
}
function handleFileSelect(ev) {
  const file = ev.target.files[0];
  if (file) { lastFile = file; startRealAnalysis(file); }
}
function loadDemo(name, size) { startSimulatedAnalysis(name, size); }

async function startRealAnalysis(file) {
  const size = (file.size / 1024 / 1024).toFixed(1) + ' MB';
  prepareUIForAnalysis(file.name, size);
  const formData = new FormData();
  formData.append('file', file);
  let data;
  try {
    setStep('step1', 'running');
    const t0 = Date.now();
    const resp = await fetch(`${API}/api/analyze`, { method: 'POST', body: formData });
    if (!resp.ok) {
      setStep('step1', 'error'); return;
    }
    data = await resp.json();
    const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
    setStep('step1', 'done', elapsed + 's');

    setStep('step2', 'running');
    await sleep(200);
    setStep('step2', 'done', data.summary.found + ' Anforderungen');

    setStep('step3', 'running');
    await sleep(200);
    const bestScore = data.match_results && data.match_results[0] ? data.match_results[0].score + '%' : '—';
    setStep('step3', 'done', bestScore + ' bestes Match');

    setStep('step4', 'running');
    await sleep(150);
    setStep('step4', 'done', 'fertig');

    document.getElementById('pipelineDot').className = 'dot green';
    document.getElementById('pipelineTitle').textContent = 'Analyse abgeschlossen';
    lastAnalysisData = data;
    showRealResults(data);
  } catch(e) {
    startSimulatedAnalysis(file.name, size, true);
  }
}

function showRealResults(data) {
  document.getElementById('analysisResults').style.display = 'block';
  document.getElementById('resultFilename').textContent =
    data.filename + ' · ' + data.pages + ' Seiten · ' + data.summary.found + ' Anforderungen';

  // ── Product match cards ──────────────────────────────────────────────────
  const cardsEl = document.getElementById('productCards');
  if (cardsEl && data.match_results && data.match_results.length > 0) {
    cardsEl.innerHTML = '';
    data.match_results.forEach((m, i) => {
      const isHigh = m.score >= 80;
      const scoreClass = isHigh ? 'high' : 'mid';
      const fillClass  = isHigh ? '' : ' mid';
      const selectedClass = i === 0 ? ' selected' : '';
      cardsEl.innerHTML += `
        <div class="product-card${selectedClass}" onclick="selectProduct(this);showMatchDetail(${JSON.stringify(m.id)})">
          <div class="product-name">${m.name}</div>
          <div class="product-match ${scoreClass}">${m.score}%</div>
          <div class="match-bar"><div class="match-fill${fillClass}" style="width:${m.score}%"></div></div>
          <div class="product-specs">
            <div class="product-spec">Pumpe <span>${m.specs_display.pump}</span></div>
            <div class="product-spec">Tank <span>${m.specs_display.tank}</span></div>
            <div class="product-spec">Antrieb <span>${m.specs_display.drive.replace('antrieb','').trim()}</span></div>
          </div>
          <div style="margin-top:8px;font-size:11px;font-family:var(--mono);color:var(--text-3)">
            ${m.met} erfüllt · ${m.not_met} nicht erfüllt
          </div>
        </div>`;
    });
    // Store match data globally for detail view
    window._matchResults = data.match_results;
    // Auto-fill offer form with best match
    if (data.match_results[0]) {
      const best = data.match_results[0];
      if (document.getElementById('fVehicle')) {
        const sel = document.getElementById('fVehicle');
        for (let opt of sel.options) {
          if (opt.value.toLowerCase().includes(best.type.toLowerCase()) ||
              best.name.toLowerCase().includes(opt.value.toLowerCase())) {
            sel.value = opt.value; break;
          }
        }
      }
    }
  }

  // ── Update req count badge ───────────────────────────────────────────────
  const badge = document.getElementById('reqCountBadge');
  if (badge) badge.textContent = data.summary.found + ' gefunden · ' + data.summary.missing + ' fehlen';

  // ── Requirements table ───────────────────────────────────────────────────
  const tbody = document.querySelector('#reqTableBody');
  if (!tbody) return;
  tbody.innerHTML = '';
  const catBadge = { technik:'badge-blue', frist:'badge-gray', rechtlich:'badge-gray', garantie:'badge-green' };
  const statusBadge = {
    found:   ['badge-green', '✓ Gefunden'],
    missing: ['badge-red',   '✗ Fehlt'],
    check:   ['badge-amber', '⚠ Prüfen'],
  };

  // Best vehicle requirements for cross-reference column
  const bestVehicleReqs = (data.match_results && data.match_results[0])
    ? data.match_results[0].requirements : [];
  const matchBadge = {
    met:     ['badge-green', '✓ Erfüllt'],
    not_met: ['badge-red',   '✗ Nicht erfüllt'],
    neutral: ['badge-gray',  '— Neutral'],
    missing: ['badge-amber', '⚠ Fehlt im PDF'],
  };

  data.requirements.forEach(req => {
    const cb = catBadge[req.category] || 'badge-gray';
    const [sb, sl] = statusBadge[req.status] || ['badge-gray', '?'];
    const lbl = req.category.charAt(0).toUpperCase() + req.category.slice(1);
    const bestReq = bestVehicleReqs.find(r => r.label === req.label);
    const [mb, ml] = bestReq ? (matchBadge[bestReq.match] || ['badge-gray','?']) : ['badge-gray','—'];
    const vehVal = bestReq ? bestReq.vehicle_value : '—';
    tbody.innerHTML += `<tr>
      <td><span class="badge ${cb}">${lbl}</span></td>
      <td>${req.label}</td>
      <td class="mono">${req.value}</td>
      <td class="mono" style="color:var(--text-2)">${vehVal}</td>
      <td><span class="badge ${mb}">${ml}</span></td>
    </tr>`;
  });

  // ── Pre-fill offer form ──────────────────────────────────────────────────
  const find = label => (data.requirements.find(r => r.label === label) || {}).value || '';
  const specs = [find('Motorleistung'), find('Feuerlöschkreiselpumpe'), find('Löschwassertank')].filter(Boolean).join(', ');
  if (specs && document.getElementById('fSpecs')) document.getElementById('fSpecs').value = specs;
  if (find('Lieferzeit') && document.getElementById('fDelivery')) document.getElementById('fDelivery').value = find('Lieferzeit');
}

function showMatchDetail(vehicleId) {
  if (!window._matchResults) return;
  // Could open a detail panel — placeholder for future extension
}

async function startSimulatedAnalysis(filename, size, fallback) {
  if (!fallback) prepareUIForAnalysis(filename, size);
  const steps = [
    { id:'step1', dur:800,  label:'47 Seiten' },
    { id:'step2', dur:900,  label:'23 Anforderungen' },
    { id:'step3', dur:600,  label:'96% bestes Match' },
    { id:'step4', dur:400,  label:'fertig' },
  ];
  for (const step of steps) {
    setStep(step.id, 'running');
    await sleep(step.dur);
    setStep(step.id, 'done', step.label);
  }
  document.getElementById('pipelineDot').className = 'dot green';
  document.getElementById('pipelineTitle').textContent = 'Analyse abgeschlossen';
  document.getElementById('analysisResults').style.display = 'block';
  document.getElementById('resultFilename').textContent = filename + ' · Demo-Vorschau';
}

function prepareUIForAnalysis(filename, size) {
  document.getElementById('uploadZone').classList.add('done');
  document.getElementById('uploadIconWrap').textContent = '✅';
  document.getElementById('uploadTitle').textContent = filename;
  document.getElementById('uploadSub').textContent = size + ' · Analyse startet…';
  document.getElementById('pipelineDot').className = 'dot amber';
  document.getElementById('pipelineTitle').textContent = 'Analysiere…';
  document.getElementById('analysisResults').style.display = 'none';
  ['step1','step2','step3','step4'].forEach(id => {
    const el = document.getElementById(id);
    el.classList.remove('done','running');
    el.querySelector('.step-indicator').textContent = id.replace('step','');
    const t = el.querySelector('.step-time');
    if (t) t.remove();
  });
}

function setStep(id, state, time) {
  const el = document.getElementById(id);
  el.classList.remove('done','running');
  if (state === 'running') { el.classList.add('running'); el.querySelector('.step-indicator').textContent = '↻'; }
  else if (state === 'done') {
    el.classList.add('done'); el.querySelector('.step-indicator').textContent = '✓';
    if (time) { const t = document.createElement('div'); t.className = 'step-time'; t.textContent = time; el.querySelector('.step-content').appendChild(t); }
  } else { el.querySelector('.step-indicator').textContent = '✗'; }
}


function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function selectProduct(card) {
  document.querySelectorAll('.product-card').forEach(c => c.classList.remove('selected'));
  card.classList.add('selected');
}

async function generateOffer() {
  const btn = document.getElementById('genBtn');
  btn.textContent = '⏳ Generiere…'; btn.disabled = true;
  const body = {
    client: document.getElementById('fClient').value,
    vehicle: document.getElementById('fVehicle').value,
    price: document.getElementById('fPrice').value,
    delivery: document.getElementById('fDelivery').value,
    ref: document.getElementById('fRef').value,
    specs: document.getElementById('fSpecs').value,
  };
  if (lastAnalysisData) {
    const find = label => (lastAnalysisData.requirements.find(r => r.label === label) || {}).value || '';
    body.motor = find('Motorleistung'); body.pump = find('Feuerlöschkreiselpumpe');
    body.tank = find('Löschwassertank'); body.drive = find('Antrieb');
    body.guarantee = find('Herstellergarantie');
  }
  showOfferPreview(body);
  try {
    const resp = await fetch(`${API}/api/generate-offer`, {
      method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)
    });
    if (resp.ok) {
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'Angebot_' + body.vehicle.replace(/[^a-zA-Z0-9]/g,'_') + '.pdf';
      a.click(); URL.revokeObjectURL(url);
      document.getElementById('genTime').textContent = '✓ PDF lokal generiert & heruntergeladen';
    } else {
      document.getElementById('genTime').textContent = 'Vorschau · PDF: Backend starten';
    }
  } catch { document.getElementById('genTime').textContent = 'Vorschau-Modus · Backend offline'; }
  btn.textContent = '⚡ Neu generieren'; btn.disabled = false;
}

function showOfferPreview(b) {
  const today = new Date().toLocaleDateString('de-DE',{day:'2-digit',month:'long',year:'numeric'});
  document.getElementById('offerPlaceholder').style.display = 'none';
  document.getElementById('docFilename').textContent = 'Angebot_' + b.vehicle.replace(/\s/g,'_') + '.pdf';
  document.getElementById('offerBody').innerHTML = `
    <div class="doc-letterhead">
      <div><div class="doc-logo">ZIEGLER <span>Albert Ziegler GmbH</span></div></div>
      <div class="doc-company-info">Rosenheimer Str. 9 · 87616 Marktoberdorf<br>www.ziegler.de</div>
    </div>
    <div class="doc-meta">
      <div class="doc-meta-item"><div class="lbl">AN</div><div class="val">${b.client}</div></div>
      <div class="doc-meta-item"><div class="lbl">DATUM</div><div class="val">${today}</div></div>
      <div class="doc-meta-item"><div class="lbl">AZ</div><div class="val">${b.ref||'—'}</div></div>
      <div class="doc-meta-item"><div class="lbl">GÜLTIG</div><div class="val">90 Tage</div></div>
    </div>
    <div class="doc-subject">Betr.: Angebot — ${b.vehicle}${b.ref?' Az. '+b.ref:''}</div>
    <div class="doc-body">
      <p>Sehr geehrte Damen und Herren,<br>wir bieten Ihnen ein einsatzbereites <b>${b.vehicle}</b> an, das alle Anforderungen Ihrer Leistungsbeschreibung erfüllt.</p>
      <table class="doc-table"><thead><tr><th>Anforderung</th><th>Ausführung</th><th>Norm</th></tr></thead><tbody>
        <tr><td>Fahrzeugtyp</td><td>${b.vehicle}</td><td>DIN 14530-27</td></tr>
        <tr><td>Motorleistung</td><td>${b.motor||'min. 290 kW'}</td><td>DIN EN 1846</td></tr>
        <tr><td>Pumpe</td><td>${b.pump||'FPN 10-3000'}</td><td>DIN EN 1028</td></tr>
        <tr><td>Tank</td><td>${b.tank||'2.000 Liter'}</td><td>EN 1846-2</td></tr>
        <tr><td>Lieferzeit</td><td>${b.delivery}</td><td>gem. Ausschreibung</td></tr>
        <tr><td>Garantie</td><td>${b.guarantee||'24 Monate'}</td><td>§443 BGB</td></tr>
      </tbody></table>
      <div class="doc-price-box">
        <div><div class="doc-price-label">ANGEBOTSPREIS (netto)</div><div class="doc-price-value">${b.price}</div></div>
        <div style="text-align:right"><div class="doc-price-label">LIEFERZEIT</div><div style="font-size:14px;font-weight:600">${b.delivery.split(' ab')[0]}</div></div>
      </div>
      <p>Mit freundlichen Grüßen,<br><br>Vertriebsleiter Ausschreibungen · Albert Ziegler GmbH</p>
    </div>
    <div class="doc-footer"><div>Albert Ziegler GmbH · HRB 13592</div><div>🔒 Lokal generiert · DSGVO-konform</div></div>`;
  document.getElementById('offerDocWrap').style.display = 'block';
  document.getElementById('genTime').textContent = 'Vorschau bereit · PDF wird generiert…';
}

function exportPDF() { generateOffer(); }

async function loadTendersFromDB() {
  try {
    const resp = await fetch(`${API}/api/tenders`);
    const tenders = await resp.json();
    if (!tenders.length) return;
    const tbody = document.getElementById('tenderBody');
    tbody.innerHTML = '';
    tenders.forEach(t => {
      const sc = {analyse:'badge-blue',offen:'badge-amber',gewonnen:'badge-green',verloren:'badge-red'}[t.status]||'badge-gray';
      tbody.innerHTML += '<tr><td>'+(t.client||t.filename)+'</td><td class="mono">'+(t.vehicle||'—')+'</td><td class="mono">'+(t.value?'€ '+t.value.toLocaleString('de-DE'):'—')+'</td><td class="mono">'+(t.created_at?t.created_at.substring(0,10):'—')+'</td><td class="mono">'+(t.req_count?t.req_count+' Req.':'—')+'</td><td><span class="badge '+sc+'">'+t.status+'</span></td></tr>';
    });
  } catch(e) { /* Demo-Daten bleiben */ }
}

function filterTable(q) {
  document.querySelectorAll('#tenderBody tr').forEach(r => {
    r.style.display = r.textContent.toLowerCase().includes(q.toLowerCase()) ? '' : 'none';
  });
}
