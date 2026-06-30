#!/usr/bin/env python3
"""
PACS DICOM Mock (Mức 2) - Realistic DICOM + REST for HIS integration testing.

- DICOM SCP: C-ECHO + C-STORE (receives real .dcm from storescu / modalities)
- Stores files + extracts key DICOM tags (AccessionNumber, StudyInstanceUID, etc.)
- SQLite study registry (persistent)
- REST API: list studies, get metadata, trigger result callback
- Can fire callbacks to real HIS or to the Node REST mock

Use with:
  pip install -r requirements.txt
  cp .env.example .env
  python -m app

Test with dcmtk:
  storescu -aec MOCKPACS localhost 4242 /path/to/some.dcm
"""

import os
import json
import sqlite3
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# DICOM
from pynetdicom import AE, evt, AllStoragePresentationContexts, debug_logger
from pynetdicom.sop_class import Verification
import pydicom
from pydicom.dataset import Dataset

load_dotenv()

# === Config ===
DICOM_PORT = int(os.getenv("DICOM_PORT", "4242"))
DICOM_AE_TITLE = os.getenv("DICOM_AE_TITLE", "MOCKPACS")
REST_PORT = int(os.getenv("REST_PORT", "9081"))
REST_HOST = os.getenv("REST_HOST", "0.0.0.0")
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", "./dicom_storage"))
DB_PATH = os.getenv("DB_PATH", "./studies.db")
HIS_CALLBACK_URL = os.getenv("HIS_CALLBACK_URL", "")
HIS_INBOUND_APIKEY = os.getenv("HIS_INBOUND_APIKEY", "")
AUTO_FIRE_DELAY_MS = int(os.getenv("AUTO_FIRE_DELAY_MS", "0"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# === DB helpers (simple SQLite for studies) ===
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS studies (
            order_number TEXT PRIMARY KEY,
            accession_number TEXT,
            study_instance_uid TEXT,
            patient_id TEXT,
            patient_name TEXT,
            modality TEXT,
            file_path TEXT,
            received_at TEXT,
            status TEXT DEFAULT 'RECEIVED',
            extra TEXT
        )
    """)
    conn.commit()
    conn.close()
    print(f"[DICOM-MOCK] DB initialized at {DB_PATH}")

def save_study(study: Dict[str, Any]):
    conn = get_db()
    conn.execute("""
        INSERT OR REPLACE INTO studies 
        (order_number, accession_number, study_instance_uid, patient_id, patient_name, 
         modality, file_path, received_at, status, extra)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        study.get("order_number"),
        study.get("accession_number"),
        study.get("study_instance_uid"),
        study.get("patient_id"),
        study.get("patient_name"),
        study.get("modality"),
        study.get("file_path"),
        study.get("received_at"),
        study.get("status", "RECEIVED"),
        json.dumps(study.get("extra", {}))
    ))
    conn.commit()
    conn.close()

def get_study(order_number: str) -> Optional[Dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM studies WHERE order_number = ?", (order_number,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["extra"] = json.loads(d.get("extra") or "{}")
    return d

def list_studies() -> list:
    conn = get_db()
    rows = conn.execute("SELECT * FROM studies ORDER BY received_at DESC").fetchall()
    conn.close()
    return [dict(r) | {"extra": json.loads(r["extra"] or "{}")} for r in rows]

init_db()

# === DICOM Handlers ===
def handle_echo(event):
    """C-ECHO"""
    print(f"[DICOM] C-ECHO received from {event.assoc.remote}")
    return 0x0000  # Success

def handle_store(event):
    """C-STORE - receive DICOM file"""
    ds: Dataset = event.dataset
    ds.file_meta = event.file_meta

    # Extract key tags (like real PACS)
    accession = getattr(ds, "AccessionNumber", None) or getattr(ds, "StudyID", None) or f"ACC{int(datetime.now().timestamp())}"
    study_uid = getattr(ds, "StudyInstanceUID", None) or f"1.2.840.113619.auto.{int(datetime.now().timestamp())}"
    patient_id = getattr(ds, "PatientID", "UNKNOWN")
    patient_name = str(getattr(ds, "PatientName", "UNKNOWN"))
    modality = getattr(ds, "Modality", "OT")

    # Save file
    study_dir = STORAGE_DIR / study_uid
    study_dir.mkdir(parents=True, exist_ok=True)
    filename = study_dir / f"{getattr(ds, 'SOPInstanceUID', 'image')}.dcm"
    ds.save_as(str(filename), write_like_original=False)

    # Persist study
    order_number = accession  # In many real systems AccessionNumber == orderNumber / SO_PHIEU
    study = {
        "order_number": order_number,
        "accession_number": accession,
        "study_instance_uid": study_uid,
        "patient_id": patient_id,
        "patient_name": patient_name,
        "modality": modality,
        "file_path": str(filename),
        "received_at": datetime.utcnow().isoformat() + "Z",
        "status": "RECEIVED",
        "extra": {
            "series_count": 1,
            "source_ae": str(event.assoc.remote),
        }
    }
    save_study(study)

    print(f"[DICOM] C-STORE success: Accession={accession} StudyUID={study_uid} saved to {filename}")

    # Optional: auto schedule result callback (very powerful for end-to-end)
    if AUTO_FIRE_DELAY_MS > 0 and HIS_CALLBACK_URL:
        asyncio.create_task(schedule_result_fire(order_number, study, AUTO_FIRE_DELAY_MS))

    return 0x0000  # Success

handlers = [
    (evt.EVT_C_ECHO, handle_echo),
    (evt.EVT_C_STORE, handle_store),
]

# === FastAPI REST ===
app = FastAPI(title="PACS DICOM Mock (Mức 2)", version="1.0")

class TriggerCallbackBody(BaseModel):
    order_number: str
    service_id: Optional[str] = None
    delay_ms: int = 0
    custom_result: Optional[Dict] = None

@app.get("/health")
async def health():
    return {"status": "ok", "dicom_ae": DICOM_AE_TITLE, "studies": len(list_studies())}

@app.get("/studies")
async def get_studies(accession: Optional[str] = None):
    studies = list_studies()
    if accession:
        studies = [s for s in studies if s.get("accession_number") == accession or s.get("order_number") == accession]
    return {"count": len(studies), "studies": studies}

@app.get("/studies/{order_number}")
async def get_study_detail(order_number: str):
    study = get_study(order_number)
    if not study:
        raise HTTPException(404, "Study not found")
    return study

@app.post("/studies")
async def manual_create_study(body: Dict[str, Any]):
    """Seed a study manually (for testing)"""
    required = ["order_number"]
    for k in required:
        if k not in body:
            raise HTTPException(400, f"{k} is required")
    study = {
        "order_number": body["order_number"],
        "accession_number": body.get("accession_number", body["order_number"]),
        "study_instance_uid": body.get("study_instance_uid") or f"1.2.840.113619.manual.{int(datetime.now().timestamp())}",
        "patient_id": body.get("patient_id", "TEST"),
        "patient_name": body.get("patient_name", "TEST PATIENT"),
        "modality": body.get("modality", "CT"),
        "file_path": body.get("file_path"),
        "received_at": datetime.utcnow().isoformat() + "Z",
        "status": body.get("status", "RECEIVED"),
        "extra": body.get("extra", {})
    }
    save_study(study)
    return study

async def _fire_callback(order_number: str, study: Dict, custom: Optional[Dict] = None):
    """Fire a result callback. Uses plain JSON shape by default (easy to customize)."""
    if not HIS_CALLBACK_URL:
        print("[DICOM-MOCK] No HIS_CALLBACK_URL set — cannot fire callback")
        return

    payload = custom or {
        "status": "APPROVED",
        "orderNumber": order_number,
        "serviceID": study.get("service_id") or order_number,
        "studyIUID": study.get("study_instance_uid"),
        "studyDate": study.get("received_at"),
        "executionStartTime": study.get("received_at"),
        "modality": study.get("modality"),
        "patient": {
            "id": study.get("patient_id"),
            "name": study.get("patient_name"),
        },
        "orders": [{
            "id": study.get("service_id") or order_number,
            "diagnosis": [{
                "reading": "Mock result from DICOM mock (Mức 2). Replace with real content.",
                "conclude": "No significant abnormality (generated by mock).",
                "signedDate": datetime.utcnow().isoformat() + "Z",
                "modality": {"code": study.get("modality", "OT")},
                "signStatus": "signed"
            }]
        }]
    }

    headers = {"Content-Type": "application/json"}
    if HIS_INBOUND_APIKEY:
        headers["X-Api-Key"] = HIS_INBOUND_APIKEY

    import httpx
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.post(HIS_CALLBACK_URL, json=payload, headers=headers)
            print(f"[DICOM-MOCK] Callback fired to {HIS_CALLBACK_URL} → {r.status_code}")
            update_status = {"status": "RESULT_SENT"}
            # naive update
            conn = get_db()
            conn.execute("UPDATE studies SET status=? WHERE order_number=?", ("RESULT_SENT", order_number))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[DICOM-MOCK] Callback error: {e}")

async def schedule_result_fire(order_number: str, study: Dict, delay_ms: int):
    await asyncio.sleep(delay_ms / 1000.0)
    await _fire_callback(order_number, study)

@app.post("/trigger-callback")
async def trigger_callback(body: TriggerCallbackBody, background: BackgroundTasks):
    study = get_study(body.order_number)
    if not study:
        # Allow triggering even without prior DICOM receive (for pure REST testing)
        study = {
            "order_number": body.order_number,
            "study_instance_uid": "1.2.840.113619.manual-trigger",
            "received_at": datetime.utcnow().isoformat(),
            "modality": "OT"
        }

    if body.delay_ms > 0:
        background.add_task(schedule_result_fire, body.order_number, study, body.delay_ms)
        return {"scheduled": True, "delay_ms": body.delay_ms}
    else:
        await _fire_callback(body.order_number, study, body.custom_result)
        return {"fired": True}

# === Startup: run DICOM SCP in background ===
@app.on_event("startup")
async def start_dicom():
    ae = AE(ae_title=DICOM_AE_TITLE)
    ae.supported_contexts = AllStoragePresentationContexts + [Verification]
    ae.add_supported_context(Verification)

    # Run SCP in background thread
    def run_scp():
        print(f"[DICOM-MOCK] Starting DICOM SCP on port {DICOM_PORT} as AE {DICOM_AE_TITLE}")
        ae.start_server(('', DICOM_PORT), block=True, evt_handlers=handlers)

    import threading
    t = threading.Thread(target=run_scp, daemon=True)
    t.start()

if __name__ == "__main__":
    print("=== PACS DICOM Mock (Mức 2) ===")
    print(f"DICOM: {DICOM_AE_TITLE} on :{DICOM_PORT}")
    print(f"REST : http://{REST_HOST}:{REST_PORT}")
    print(f"Storage: {STORAGE_DIR}")
    uvicorn.run(app, host=REST_HOST, port=REST_PORT)