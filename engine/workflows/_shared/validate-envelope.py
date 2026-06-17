#!/usr/bin/env python3
"""validate-envelope — the ONE validator every harness workflow envelope is checked against.

Reuses the single schema at engine/workflows/_shared/envelope.schema.json (no per-workflow
copy) so all workflows speak the same receipt format (A1). Pure stdlib — interprets the small
subset of JSON-Schema we use (required / type / enum / const). Fail-closed: any breach exits 1.

    python engine/workflows/_shared/validate-envelope.py <envelope.json>
    python engine/workflows/_shared/validate-envelope.py <envelope.json> --payload <payload-file>
    python engine/workflows/_shared/validate-envelope.py --self-test

--payload recomputes sha256(payload) and asserts it equals envelope.content_sha256: this is the
envelope<->payload binding that catches a stale receipt pointing at a changed payload (drift).
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = HERE / "envelope.schema.json"

_JSON_TYPES = {
    "string": str, "boolean": bool, "object": dict, "array": list,
    "integer": int, "number": (int, float), "null": type(None),
}


def _load_schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def _type_ok(value, spec_type) -> bool:
    types = spec_type if isinstance(spec_type, list) else [spec_type]
    for t in types:
        py = _JSON_TYPES.get(t)
        if py is None:
            return True  # unknown type keyword -> don't block
        # bool is a subclass of int in python; keep them distinct
        if t == "integer" and isinstance(value, bool):
            continue
        if isinstance(value, py):
            return True
    return False


def validate(envelope: dict, schema: dict | None = None) -> list[str]:
    """Return a list of error strings (empty == valid)."""
    schema = schema or _load_schema()
    errors: list[str] = []
    if not isinstance(envelope, dict):
        return ["envelope is not a JSON object"]
    for req in schema.get("required", []):
        if req not in envelope:
            errors.append(f"missing required field '{req}'")
    props = schema.get("properties", {})
    for key, value in envelope.items():
        spec = props.get(key)
        if not spec:
            continue  # extra fields allowed
        if "const" in spec and value != spec["const"]:
            errors.append(f"field '{key}'={value!r} must equal const {spec['const']!r}")
        if "type" in spec and not _type_ok(value, spec["type"]):
            errors.append(f"field '{key}'={value!r} not of type {spec['type']!r}")
        if "enum" in spec and value not in spec["enum"]:
            errors.append(f"field '{key}'={value!r} not in enum {spec['enum']!r}")
    return errors


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check_payload(envelope: dict, payload: Path) -> list[str]:
    if not payload.exists():
        return [f"payload not found: {payload}"]
    want = envelope.get("content_sha256", "")
    got = _sha256(payload.read_bytes())
    if want != got:
        return [f"content_sha256 drift: envelope={want[:12]}… payload={got[:12]}… (payload changed since the receipt)"]
    return []


def _self_test() -> int:
    schema = _load_schema()
    good = {
        "schema_version": "1", "workflow": "impact-analysis",
        "artifact_type": "risk-assessment", "artifact_path": "rounds/x/01.md",
        "status": "DONE", "summary_for_router": "local change, no contract.",
        "requires_human_review": False, "content_sha256": "deadbeef",
        "risk_level": "LOW", "next_recommended_workflow": "incremental-impl",
    }
    assert validate(good, schema) == [], "valid envelope rejected"
    assert validate({**good, "schema_version": "2"}, schema), "bad const accepted"
    assert validate({k: v for k, v in good.items() if k != "workflow"}, schema), "missing field accepted"
    assert validate({**good, "requires_human_review": "yes"}, schema), "bad type accepted"
    assert validate({**good, "risk_level": "CATASTROPHIC"}, schema), "bad enum accepted"
    # payload binding round-trip
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "payload.md"
        p.write_text("hello", encoding="utf-8")
        env = {**good, "content_sha256": _sha256(b"hello")}
        assert _check_payload(env, p) == [], "matching payload flagged"
        assert _check_payload({**good, "content_sha256": "x"}, p), "drifted payload accepted"
    print("validate-envelope self-test: OK")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return _self_test()
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    env_path = Path(args[0])
    if not env_path.exists():
        print(f"FAIL: envelope not found: {env_path}")
        return 1
    try:
        envelope = json.loads(env_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: envelope is not valid JSON: {exc}")
        return 1
    errors = validate(envelope)
    if "--payload" in argv:
        i = argv.index("--payload")
        if i + 1 < len(argv):
            errors += _check_payload(envelope, Path(argv[i + 1]))
    if errors:
        print(f"FAIL: {env_path}")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK: {env_path} (valid envelope)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
