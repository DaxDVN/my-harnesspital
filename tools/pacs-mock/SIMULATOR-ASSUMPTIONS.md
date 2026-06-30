# PACS Mock — Simulator Assumptions

This mock intentionally bakes in simplifications so the HIS team can test connectivity and serialization before the real PACS is available. Every item below maps to a decision in `docs/business/pacs/DECISIONS.md` or a known gap that must be verified with VIETRAD/MINERVA.

## Vendor & format

1. **Vendor = VIETRAD / MINERVA.** The contract comes from their integration PDFs.
2. **FHIR-first, JSON-thuần fallback.** The mock ships both payload families. The canonical HIS design uses FHIR-shaped DTOs; plain JSON is the fallback if vendor production FHIR is not stable.
3. **Payloads are vendor samples copied verbatim.** They are NOT regenerated from HIS code — that would make the test circular.

## Authentication

4. **Inbound HIS→mock = HTTP Basic Auth.** HIS must send `Authorization: Basic base64(user:pass)` matching `EXPECTED_BASIC_USER/PASS`.
5. **Outbound mock→HIS callback = `X-Api-Key`.** The mock sends `X-Api-Key: HIS_INBOUND_APIKEY`, NOT Basic Auth, matching the HIS-side `LisApiBase` pattern. This is a simulator simplification: the vendor docs show Basic for PACS→HIS callback, but the HIS project chose API-key inbound.
6. **No encryption of secrets inside the mock.** In production, HIS stores PACS credentials encrypted (`AesEncryptionHelper` + env `Encryption__Key`). The mock uses plaintext env vars because it is a throwaway tool.

## Signed URL

7. **Signed-URL formula — RESOLVED, synced to HIS.** The mock computes `md5(user + token + expires)` — **NO separators, lowercase hex** — to match the authoritative HIS implementation in `MyHospital.ServiceInterface/Pacs/Core/PacsSignedUrlHelper.cs` (`Sign()`: `user + token + expiresUnix` → MD5 → `ToLowerInvariant()`). The build-task binding-fact's dotted form `md5(user + "." + token + "." + expires)` was a misread — the vendor doc's dots are notation only (analysis/01 §10.1: "các tham số nối liền nhau, KHÔNG dấu phân cách"). Mock signatures now cross-check correctly against real HIS-generated URLs. (MD5 itself is still cryptographically weak — see #8.)
8. **Recommend HMAC-SHA256.** HIS should propose upgrading the signed-URL algorithm to HMAC-SHA256 with a server-side secret; keep MD5 only as a fallback with documented residual risk.
9. **`expires` TTL ≤ 2 hours.** Per vendor docs. The mock does not enforce TTL, only computes and compares the signature.

## Order / result semantics

10. **Body may be a single Bundle or an array of Bundles.** Vendor docs state order POST body is `Array(jsonMessage)`, but the sample shows one Bundle. The mock accepts both.
11. **`OrderNumber` is the connection key.** In FHIR it lives in `ServiceRequest.note.extension.valueCodeableConcept.text` with coding `SO_PHIEU`; in plain JSON it is root `orderNumber`.
12. **`ServiceRequest.id` / `orders[].id` is the per-service ID** used for PUT/DELETE and result matching.
13. **Minimal validation only.** The mock checks resource type and presence of required keys. It does NOT validate clinical/business rules, identifier consistency, or FHIR conformance.
14. **DELETE returns 204.** The vendor doc says successful cancel is `204 No Content`. POST/PUT return `201` with an ACK shape. The build task only required a 201 ACK for successful receive, but using 204 for DELETE matches the vendor contract.
15. **Fault modes are synthetic.** `http400` / `http500` return the corresponding status after auth; `timeout` hangs the response indefinitely (or for a very long delay) to test HIS retry/outbox.

## Callback

16. **Callback substitutes `orderNumber` and `serviceId` into the chosen fixture.** For FHIR this updates `SO_PHIEU`, `DiagnosticReport.identifier.value`, `ServiceRequest.id`, `ImagingStudy.id`, and `Bundle.id`. For plain JSON it updates root `orderNumber`, root `serviceID`, and `orders[0].id`.
17. **The mock returns the real HTTP status + body from HIS.** It does not always ack 200, matching decision D6.

## Catalog pull

18. **Catalog endpoints are `GET /his/api/GetListUser`, `/GetListService`, `/GetListModality`.** The mock validates the expected shapes (`userInfor[]`, `serviceInfor[]`, `modalityInfor[]`) and returns a summary.
19. **No auth model for catalog in vendor docs.** The mock calls them without auth. HIS must protect these endpoints (whitelist IP / token) in production.

## Realistic study handling (added for multi-vendor / real-PACS testing)

The mock now maintains an in-memory study registry:
- Order receive → auto create study with generated `studyInstanceUid` + `accessionNumber`.
- ACKs return these IDs (realistic PACS behavior).
- Result callbacks auto-inject study data when `orderNumber` matches a received study.
This makes I/O roundtrips much closer to what a real PACS does (order → assigned IDs → result referencing the study).

This is intentional to help prove HIS handles linked study data stably before swapping to any real vendor API.

## Pending vendor confirmation (DECISIONS.md §D)

20. **FHIR endpoint production stability.** Confirm whether production runs FHIR or whether the team must fall back to plain JSON.
21. **AccessionNumber length / uniqueness.** Vendor mentions ≤10 characters for manual modality entry, ≤20 otherwise; confirm length and scope (site vs global).
22. **CT split rule.** Confirm whether CT services split `<32` / `≥32` slices by service or by machine, and whether that produces two accession numbers.
23. **Scheduled datetime.** Confirm whether PACS accepts order creation time as scheduled time or requires real appointment slots.
24. **Modality code table.** Confirm mapping `DX` vs `DR` and the full modality enum.
25. **HTTPS + HMAC-SHA256 support.** Confirm whether vendor supports TLS and a stronger signed-URL algorithm.
26. **Callback retry/ack, cancel-after-capture, and emergency-merge behavior** are left open in the vendor docs and must be closed before go-live.
