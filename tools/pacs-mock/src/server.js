const express = require('express');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const https = require('https');

const app = express();

const PORT = process.env.PORT || '9080';
const TLS_CERT = process.env.TLS_CERT || '';
const TLS_KEY = process.env.TLS_KEY || '';
const EXPECTED_BASIC_USER = process.env.EXPECTED_BASIC_USER || '';
const EXPECTED_BASIC_PASS = process.env.EXPECTED_BASIC_PASS || '';
const HIS_CALLBACK_URL = process.env.HIS_CALLBACK_URL || '';
const HIS_INBOUND_APIKEY = process.env.HIS_INBOUND_APIKEY || '';
const HIS_BASE_URL = process.env.HIS_BASE_URL || '';
const FAULT_MODE = process.env.FAULT_MODE || 'none';
const FIXTURE_DIR = process.env.FIXTURE_DIR || './fixtures';
const STUDIES_FILE = process.env.STUDIES_FILE || './studies.json';
const DEFAULT_DELAY_MS = parseInt(process.env.DEFAULT_DELAY_MS || '0', 10);
const AUTO_CALLBACK = process.env.AUTO_CALLBACK || 'false';
const AUTO_CALLBACK_DELAY_MS = parseInt(process.env.AUTO_CALLBACK_DELAY_MS || '4000', 10);

// === Persistent Study Registry (Mức 1 - close to real PACS behavior) ===
// - State survives restart (JSON file)
// - Real PACS thường gán và trả StudyInstanceUID + Accession ngay khi nhận order
// - Callbacks sau đó mang study data liên kết
let studies = new Map();

function loadStudies() {
  try {
    if (fs.existsSync(STUDIES_FILE)) {
      const data = JSON.parse(fs.readFileSync(STUDIES_FILE, 'utf8'));
      studies = new Map(Object.entries(data));
      console.log(`[PACS-MOCK] Loaded ${studies.size} studies from ${STUDIES_FILE}`);
    }
  } catch (e) {
    console.warn('[PACS-MOCK] Could not load studies.json, starting fresh');
    studies = new Map();
  }
}

function saveStudies() {
  try {
    const obj = Object.fromEntries(studies);
    fs.writeFileSync(STUDIES_FILE, JSON.stringify(obj, null, 2));
  } catch (e) {
    console.error('[PACS-MOCK] Failed to persist studies:', e.message);
  }
}

function generateStudyUid() {
  // Realistic-looking DICOM UID for testing only
  return '1.2.840.113619.2.55.3.' + Date.now() + '.' + Math.floor(Math.random() * 999999);
}

function getOrCreateStudy(orderNumber, serviceId) {
  let study = studies.get(orderNumber);
  if (!study) {
    study = {
      orderNumber,
      accessionNumber: orderNumber,
      studyInstanceUid: generateStudyUid(),
      serviceRequestIds: [],
      receivedAt: new Date().toISOString(),
      status: 'RECEIVED',
      lastUpdated: new Date().toISOString()
    };
    studies.set(orderNumber, study);
    saveStudies();
  }
  if (serviceId && !study.serviceRequestIds.includes(serviceId)) {
    study.serviceRequestIds.push(serviceId);
    study.lastUpdated = new Date().toISOString();
    saveStudies();
  }
  return study;
}

function updateStudyStatus(orderNumber, status) {
  const study = studies.get(orderNumber);
  if (study) {
    study.status = status;
    study.lastUpdated = new Date().toISOString();
    saveStudies();
  }
  return study;
}

// Load on startup
loadStudies();

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

function logInbound(req, extraBody) {
  console.log('---');
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.originalUrl || req.url}`);
  console.log('Headers:', JSON.stringify(req.headers, null, 2));
  const body = extraBody !== undefined ? extraBody : req.body;
  if (body !== undefined && body !== null && Object.keys(body).length > 0) {
    console.log('Body:', JSON.stringify(body, null, 2));
  }
}

function errorResponse(message) {
  return { status: false, data: { error: message }, code: null };
}

function okResponse(data) {
  return { status: true, data, code: null };
}

function checkBasicAuth(req, res) {
  const auth = req.headers.authorization || '';
  if (!auth.startsWith('Basic ')) {
    res.status(401).json(errorResponse('Missing or unsupported Authorization header'));
    return false;
  }
  const decoded = Buffer.from(auth.slice(6), 'base64').toString('utf8');
  const sep = decoded.indexOf(':'); // RFC 7617: username has no colon; password may
  const user = sep === -1 ? decoded : decoded.slice(0, sep);
  const pass = sep === -1 ? '' : decoded.slice(sep + 1);
  if (user !== EXPECTED_BASIC_USER || pass !== EXPECTED_BASIC_PASS) {
    res.status(401).json(errorResponse('Invalid Basic credentials'));
    return false;
  }
  return true;
}

function applyFault(req, res) {
  if (FAULT_MODE === 'http400') {
    res.status(400).json(errorResponse('Fault mode: forced HTTP 400'));
    return true;
  }
  if (FAULT_MODE === 'http500') {
    res.status(500).json(errorResponse('Fault mode: forced HTTP 500'));
    return true;
  }
  if (FAULT_MODE === 'timeout') {
    // Intentionally never respond (or longer than any reasonable HIS timeout).
    return true;
  }
  return false;
}

function findOrderNumberFhir(bundle) {
  if (!bundle || bundle.resourceType !== 'Bundle' || !Array.isArray(bundle.entry)) return null;
  for (const entry of bundle.entry) {
    const r = entry && entry.resource;
    if (r && r.resourceType === 'ServiceRequest' && Array.isArray(r.note)) {
      for (const note of r.note) {
        const ext = note && note.extension && note.extension[0];
        const vcc = ext && ext.valueCodeableConcept;
        if (vcc && Array.isArray(vcc.coding) && vcc.coding[0] && vcc.coding[0].code === 'SO_PHIEU') {
          return vcc.text || null;
        }
      }
    }
  }
  return null;
}

function findServiceIdFhir(bundle) {
  if (!bundle || bundle.resourceType !== 'Bundle' || !Array.isArray(bundle.entry)) return null;
  for (const entry of bundle.entry) {
    const r = entry && entry.resource;
    if (r && r.resourceType === 'ServiceRequest') return r.id || null;
  }
  return null;
}

function validateReceive(body, method) {
  if (method === 'DELETE') return { ok: true }; // no body expected per vendor spec
  if (!body || (typeof body === 'object' && Object.keys(body).length === 0)) {
    return { ok: false, error: 'Missing request body' };
  }

  let target = body;
  if (Array.isArray(body) && body.length > 0) target = body[0];

  if (target && target.resourceType === 'Bundle') {
    const orderNumber = findOrderNumberFhir(target);
    const serviceId = findServiceIdFhir(target);
    if (!serviceId) return { ok: false, error: 'FHIR payload missing ServiceRequest' };
    if (!orderNumber) return { ok: false, error: 'FHIR payload missing OrderNumber (SO_PHIEU)' };
    return { ok: true, orderNumber, serviceId, isFhir: true };
  }

  // Plain JSON thuan
  if (!target.orderNumber) return { ok: false, error: 'Plain JSON payload missing orderNumber' };
  if (!Array.isArray(target.orders) || target.orders.length === 0) {
    return { ok: false, error: 'Plain JSON payload missing orders' };
  }
  return { ok: true, orderNumber: target.orderNumber, serviceId: target.orders[0].id || target.serviceID, isFhir: false };
}

async function fireResultCallback({ orderNumber, serviceId, fixtureName = 'result-callback-fhir.json', customResult, delayMs = 0 }) {
  let resolvedServiceId = serviceId || '';
  if (orderNumber && !resolvedServiceId) {
    const regStudy = studies.get(orderNumber);
    if (regStudy && regStudy.serviceRequestIds && regStudy.serviceRequestIds.length > 0) {
      resolvedServiceId = regStudy.serviceRequestIds[0];
    }
  }

  const study = orderNumber ? studies.get(orderNumber) : null;
  const fixturePath = path.resolve(FIXTURE_DIR, fixtureName);

  const doFire = async () => {
    try {
      let payload;

      if (customResult) {
        payload = customResult;
        if (typeof payload === 'string') payload = JSON.parse(payload);
      } else {
        const raw = fs.readFileSync(fixturePath, 'utf8');
        payload = JSON.parse(raw);

        const name = fixtureName.toLowerCase();
        const studyIuid = study ? study.studyInstanceUid : generateStudyUid();
        const studyDate = new Date().toISOString();

        if (name.includes('fhir')) {
          if (orderNumber && Array.isArray(payload.entry)) {
            payload.entry.forEach((entry) => {
              const r = entry && entry.resource;
              if (r && r.resourceType === 'ServiceRequest' && Array.isArray(r.note)) {
                r.note.forEach((note) => {
                  const ext = note && note.extension && note.extension[0];
                  const vcc = ext && ext.valueCodeableConcept;
                  if (vcc && Array.isArray(vcc.coding) && vcc.coding[0] && vcc.coding[0].code === 'SO_PHIEU') {
                    vcc.text = orderNumber;
                  }
                });
              }
              if (r && r.resourceType === 'DiagnosticReport' && r.identifier) {
                r.identifier.value = orderNumber;
              }
              if (r && r.resourceType === 'ImagingStudy') {
                if (!r.uid) r.uid = studyIuid;
              }
            });
          }
          if (resolvedServiceId && Array.isArray(payload.entry)) {
            payload.entry.forEach((entry) => {
              const r = entry && entry.resource;
              if (r && (r.resourceType === 'ServiceRequest' || r.resourceType === 'ImagingStudy')) {
                r.id = resolvedServiceId;
              }
            });
            payload.id = resolvedServiceId;
          }
        } else {
          if (orderNumber) payload.orderNumber = orderNumber;
          if (resolvedServiceId) {
            payload.serviceID = resolvedServiceId;
            if (Array.isArray(payload.orders) && payload.orders[0]) payload.orders[0].id = resolvedServiceId;
          }
          if (!payload.studyIUID || payload.studyIUID === '') payload.studyIUID = studyIuid;
          if (!payload.studyDate) payload.studyDate = studyDate;
          if (!payload.executionStartTime) payload.executionStartTime = studyDate;
        }
      }

      if (!HIS_CALLBACK_URL) {
        console.error('No HIS_CALLBACK_URL configured');
        return;
      }

      const resp = await fetch(HIS_CALLBACK_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Api-Key': HIS_INBOUND_APIKEY,
        },
        body: JSON.stringify(payload),
      });
      const text = await resp.text();

      console.log(`[PACS-MOCK] Fired callback order=${orderNumber} studyIUID=${study ? study.studyInstanceUid : 'generated'} status=${resp.status}`);
      console.log(`HIS response: ${resp.status} ${text.substring(0, 600)}`);

      if (orderNumber) updateStudyStatus(orderNumber, 'RESULT_SENT');
    } catch (err) {
      console.error('fire-callback execution error:', err);
    }
  };

  if (delayMs > 0) {
    console.log(`[PACS-MOCK] Scheduling callback for order=${orderNumber} in ${delayMs}ms (simulating real PACS processing time)`);
    setTimeout(doFire, delayMs);
    return { scheduled: true, delayMs, orderNumber };
  }

  await doFire();
  return {
    fired: true,
    orderNumber,
    injectedStudy: study ? { studyInstanceUid: study.studyInstanceUid, accessionNumber: study.accessionNumber } : null
  };
}

app.post('/admin/fire-callback', async (req, res) => {
  logInbound(req);
  const orderNumber = req.query.orderNumber || req.body.orderNumber || '';
  const serviceId = req.query.serviceId || req.body.serviceId || '';
  const fixtureName = req.query.fixture || req.body.fixture || 'result-callback-fhir.json';
  const delayMs = parseInt(req.query.delay || req.body.delay || DEFAULT_DELAY_MS, 10);
  const customResult = req.body && (req.body.customResult || req.body.result) ? (req.body.customResult || req.body.result) : null;

  if (!HIS_CALLBACK_URL) {
    return res.status(400).json(errorResponse('HIS_CALLBACK_URL not configured'));
  }

  const result = await fireResultCallback({ orderNumber, serviceId, fixtureName, customResult, delayMs });

  if (result.scheduled) {
    return res.status(202).json(okResponse({ ...result, note: 'Result will be sent asynchronously' }));
  }

  res.status(200).json(okResponse(result));
});

app.post('/admin/pull-catalog', async (req, res) => {
  logInbound(req);
  if (!HIS_BASE_URL) {
    return res.status(400).json(errorResponse('HIS_BASE_URL not configured'));
  }

  const endpoints = [
    { key: 'user', path: '/pacs/GetListUser', field: 'userInfor' },
    { key: 'service', path: '/pacs/GetListService', field: 'serviceInfor' },
    { key: 'modality', path: '/pacs/GetListModality', field: 'modalityInfor' },
  ];

  const result = {};
  for (const ep of endpoints) {
    const url = `${HIS_BASE_URL}${ep.path}?format=raw`;
    try {
      const resp = await fetch(url, {
        headers: {
          'X-Api-Key': HIS_INBOUND_APIKEY,
          'Accept': 'application/json'
        }
      });
      const text = await resp.text();
      let json = null;
      try { json = JSON.parse(text); } catch { /* ignore parse failure */ }
      const isBare = Array.isArray(json);
      const isWrapped = json && Array.isArray(json[ep.field]);
      const arr = isBare ? json : (isWrapped ? json[ep.field] : null);
      const ok = resp.ok && arr !== null;
      const shape = isBare ? 'bare-array' : (isWrapped ? 'wrapped' : 'unknown');
      console.log(`Pull ${url}: status=${resp.status}, shapeOk=${ok}, count=${arr ? arr.length : 'N/A'}, shape=${shape}`);
      result[ep.key] = { ok, status: resp.status, shape, count: arr ? arr.length : 0, sample: arr && arr[0] ? arr[0] : null };
    } catch (err) {
      console.error(`Pull ${url} error:`, err.message);
      result[ep.key] = { ok: false, error: err.message, count: 0 };
    }
  }
  res.status(200).json(okResponse(result));
});

app.get('/admin/verify-signature', (req, res) => {
  logInbound(req);
  const { user, token, expires, signature } = req.query;
  // Authoritative HIS formula: md5(user + token + expires) — NO separators, lowercase hex.
  // Source: worktrees/combine-his-pacs/be/MyHospital.ServiceInterface/Pacs/Core/PacsSignedUrlHelper.cs:22
  const computed = crypto.createHash('md5').update(`${user}${token}${expires}`).digest('hex');
  const valid = computed === String(signature).toLowerCase();
  res.status(200).json({ valid, computed });
});

// === Study registry inspection + management (Mức 1 - realistic PACS) ===
app.get('/admin/studies', (req, res) => {
  logInbound(req);
  const list = Array.from(studies.values());
  const filtered = req.query.accession ? list.filter(s => s.accessionNumber === req.query.accession || s.orderNumber === req.query.accession) : list;
  res.json(okResponse({
    count: filtered.length,
    note: 'Studies created on order receive. Real PACS returns StudyInstanceUID + accession in ACK and results.',
    studies: filtered
  }));
});

app.get('/admin/studies/:orderNumber', (req, res) => {
  logInbound(req);
  const study = studies.get(req.params.orderNumber);
  if (!study) return res.status(404).json(errorResponse('Study not found'));
  res.json(okResponse(study));
});

// Create or update a study manually (useful for testing any scenario)
app.post('/admin/studies', (req, res) => {
  logInbound(req);
  const { orderNumber, accessionNumber, studyInstanceUid, status } = req.body;
  if (!orderNumber) return res.status(400).json(errorResponse('orderNumber required'));

  let study = studies.get(orderNumber);
  if (!study) {
    study = {
      orderNumber,
      accessionNumber: accessionNumber || orderNumber,
      studyInstanceUid: studyInstanceUid || generateStudyUid(),
      serviceRequestIds: [],
      receivedAt: new Date().toISOString(),
      status: status || 'RECEIVED'
    };
    studies.set(orderNumber, study);
  } else {
    if (accessionNumber) study.accessionNumber = accessionNumber;
    if (studyInstanceUid) study.studyInstanceUid = studyInstanceUid;
    if (status) study.status = status;
  }
  study.lastUpdated = new Date().toISOString();
  saveStudies();

  res.status(201).json(okResponse(study));
});

// Quick state + config
app.get('/admin/state', (req, res) => {
  res.json(okResponse({
    studiesCount: studies.size,
    faultMode: FAULT_MODE,
    hisCallback: HIS_CALLBACK_URL || '(not set)',
    defaultDelayMs: DEFAULT_DELAY_MS,
    autoCallback: AUTO_CALLBACK === 'true',
    autoCallbackDelayMs: AUTO_CALLBACK_DELAY_MS,
    studiesFile: STUDIES_FILE
  }));
});

// Manually mark a study complete (simulates radiologist reading)
app.post('/admin/studies/:orderNumber/complete', async (req, res) => {
  logInbound(req);
  const study = updateStudyStatus(req.params.orderNumber, 'COMPLETED');
  if (!study) return res.status(404).json(errorResponse('Study not found'));
  res.json(okResponse({ message: 'Study marked completed', study, note: 'Use /admin/fire-callback to send result if needed' }));
});

app.use(express.static(path.join(__dirname, '..', 'public')));

app.all('*', (req, res) => {
  logInbound(req);
  if (!['POST', 'PUT', 'DELETE'].includes(req.method)) {
    return res.status(405).json(errorResponse('Method not allowed'));
  }
  if (!checkBasicAuth(req, res)) return;
  if (applyFault(req, res)) return;

  const validation = validateReceive(req.body, req.method);
  if (!validation.ok) {
    return res.status(400).json(errorResponse(validation.error));
  }

  if (req.method === 'DELETE') {
    const pathParts = req.path.split('/').filter(Boolean);
    const id = pathParts[pathParts.length - 1];
    let foundOrderNumber = null;
    if (id) {
      for (const [orderNumber, study] of studies.entries()) {
        const hasServiceId = Array.isArray(study.serviceRequestIds) && study.serviceRequestIds.includes(id);
        const matchesAccession = study.accessionNumber === id;
        const matchesOrder = study.orderNumber === id;
        if (hasServiceId || matchesAccession || matchesOrder) {
          foundOrderNumber = orderNumber;
          break;
        }
      }
    }

    if (foundOrderNumber) {
      updateStudyStatus(foundOrderNumber, 'CANCELLED');
      console.log(`[PACS-MOCK] DELETE request for path ${req.path} matched study ${foundOrderNumber}, status set to CANCELLED`);
    } else {
      console.log(`[PACS-MOCK] DELETE request for path ${req.path} (extracted ID: ${id || 'none'}) did not match any study`);
    }
    return res.status(204).send();
  }

  const study = getOrCreateStudy(validation.orderNumber, validation.serviceId);

  const ackData = {
    receivedAt: new Date().toISOString(),
    method: req.method,
    path: req.originalUrl || req.url,
    orderNumber: validation.orderNumber,
    serviceId: validation.serviceId,
    isFhir: validation.isFhir,
    ack: 'received',
    // This is what makes it close to real PACS: return IDs PACS "owns"
    accessionNumber: study.accessionNumber,
    studyInstanceUid: study.studyInstanceUid,
    serviceRequestIds: study.serviceRequestIds,
    status: study.status,
  };
  console.log(`[PACS-MOCK] Order received → study created/updated: order=${validation.orderNumber} studyIUID=${study.studyInstanceUid}`);

  if (AUTO_CALLBACK === 'true' && HIS_CALLBACK_URL) {
    console.log(`[PACS-MOCK] AUTO_CALLBACK enabled — scheduling result for order=${validation.orderNumber} in ${AUTO_CALLBACK_DELAY_MS}ms`);
    fireResultCallback({
      orderNumber: validation.orderNumber,
      serviceId: validation.serviceId,
      delayMs: AUTO_CALLBACK_DELAY_MS,
    }).catch((err) => console.error('AUTO_CALLBACK error:', err));
  }

  res.status(201).json(okResponse(ackData));
});

function start() {
  if (TLS_CERT && TLS_KEY) {
    const opts = {
      cert: fs.readFileSync(TLS_CERT),
      key: fs.readFileSync(TLS_KEY),
    };
    https.createServer(opts, app).listen(PORT, () => {
      console.log(`PACS mock (HTTPS) listening on port ${PORT}`);
      console.log(`TLS cert: ${TLS_CERT}, key: ${TLS_KEY}`);
    });
  } else {
    app.listen(PORT, () => {
      console.log(`PACS mock (HTTP) listening on port ${PORT}`);
    });
  }
}

start();
