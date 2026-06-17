#!/usr/bin/env python3
"""API smoke checks for careflow BA fixes.

This is a Python replacement for the old PowerShell smoke script. It uses only
the Python standard library so it can run on Linux without shell-specific setup.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener


def unwrap(value):
    if isinstance(value, dict) and "Data" in value:
        return value["Data"]
    return value


class Client:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def request_json(self, method: str, path: str, body=None):
        data = None
        headers = {}
        if body is not None:
            data = json.dumps(body, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = Request(
            f"{self.base_url}{path}", data=data, headers=headers, method=method
        )
        with self.opener.open(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
        return unwrap(json.loads(raw) if raw else {})

    def get(self, path: str):
        return self.request_json("GET", path)

    def post(self, path: str, body):
        return self.request_json("POST", path, body)


def result_error(exc: Exception) -> str:
    if isinstance(exc, HTTPError):
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return body or str(exc)
    return str(exc)


def run_smoke(base_url: str) -> tuple[dict[str, str], int]:
    client = Client(base_url)
    results: dict[str, str] = {}

    try:
        auth = client.post(
            "/auth",
            {
                "provider": "credentials",
                "UserName": "lynkhanh9822@gmail.com",
                "Password": "12.[s7HXZQ;NfAoF",
                "Meta": {"code": "bvtest3"},
            },
        )
        results["auth"] = "PASS" if auth.get("UserId") else "FAIL: no UserId"
    except Exception as exc:
        results["auth"] = f"FAIL: {result_error(exc)}"
        return results, 1

    try:
        inpatient = client.get("/medical-visits/inpatient?$top=5")
        items = list(inpatient.get("ListOfObject") or [])
        has_visit_code_prop = not items or "MedicalVisitCode" in items[0]
        visit_row = next(
            (
                item
                for item in items
                if item.get("RowType") != "AdmissionOrder" and item.get("VisitId")
            ),
            None,
        )
        results["#11_MedicalVisitCode_field"] = (
            "PASS" if has_visit_code_prop else "FAIL: property missing"
        )
        if visit_row:
            code = visit_row.get("MedicalVisitCode")
            results["#11_sample_code"] = (
                f"PASS ({code})" if code else "WARN: visit row has null code"
            )
        else:
            results["#11_sample_code"] = "SKIP: no admission visit rows"
    except Exception as exc:
        results["#11_MedicalVisitCode_field"] = f"FAIL: {result_error(exc)}"

    try:
        settings = client.get(
            "/settings?"
            + urlencode(
                [
                    ("Keys", "InpatientAdvanceGateEnabled"),
                    ("Keys", "InpatientAdvanceGateEnabled"),
                ]
            )
        )
        row = next(
            (
                item
                for item in (settings if isinstance(settings, list) else [])
                if item.get("Key") == "InpatientAdvanceGateEnabled"
            ),
            None,
        )
        results["#4_advance_gate_setting"] = (
            f"PASS (value={row.get('Value')})"
            if row
            else "WARN: setting row missing (defaults false)"
        )
    except Exception as exc:
        results["#4_advance_gate_setting"] = f"FAIL: {result_error(exc)}"

    try:
        active_patient_id = None
        emr = client.get("/emr/patient-records?$top=10")
        in_treatment = next(
            (
                item
                for item in emr.get("ListOfObject", [])
                if item.get("TreatmentStatus") == "in-treatment"
            ),
            None,
        )
        if not in_treatment:
            inpatient = client.get("/medical-visits/inpatient?$top=10")
            in_treatment = next(
                (
                    {"PatientId": item.get("PatientId")}
                    for item in inpatient.get("ListOfObject", [])
                    if item.get("Status") in {"Pending", "InProgress"}
                    and item.get("PatientId")
                ),
                None,
            )
        if in_treatment:
            active_patient_id = in_treatment.get("PatientId")

        if not active_patient_id:
            results["#18_active_episode_block"] = (
                "SKIP: no in-treatment patient in EMR list"
            )
        else:
            service_id = 1000
            try:
                inpatient = client.get("/medical-visits/inpatient?$top=5")
                visit_row = next(
                    (
                        item
                        for item in inpatient.get("ListOfObject", [])
                        if item.get("VisitId")
                    ),
                    None,
                )
                if visit_row:
                    ordered = client.get(
                        f"/medical-visits/{visit_row['VisitId']}/ordered-services"
                    )
                    clinical = next(iter(ordered.get("ClinicalServices") or []), None)
                    if clinical and clinical.get("MedicalServiceId"):
                        service_id = clinical["MedicalServiceId"]
            except Exception:
                pass

            payload = {
                "Patient": {"PatientId": active_patient_id},
                "Visit": {
                    "PatientTypeId": 1,
                    "ReasonForVisitId": 1,
                    "TreatmentTypeId": 1,
                    "ReceptionTime": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    "ServiceMarkupRate": 0,
                },
                "Services": [{"ServiceId": service_id, "Quantity": 1}],
            }
            try:
                client.post("/medical-visits", payload)
                results["#18_active_episode_block"] = (
                    "FAIL: create visit succeeded for in-treatment patient"
                )
            except Exception as exc:
                err = result_error(exc)
                if "PATIENT_HAS_ACTIVE_TREATMENT_EPISODE" in err:
                    results["#18_active_episode_block"] = "PASS"
                else:
                    results["#18_active_episode_block"] = (
                        f"WARN: blocked but message={err}"
                    )
    except Exception as exc:
        results["#18_active_episode_block"] = f"SKIP: {result_error(exc)}"

    exit_code = 1 if any(value.startswith("FAIL") for value in results.values()) else 0
    return results, exit_code


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run careflow BA fixes API smoke checks."
    )
    parser.add_argument("--base-url", default="http://localhost:5001")
    args = parser.parse_args()
    results, exit_code = run_smoke(args.base_url)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
