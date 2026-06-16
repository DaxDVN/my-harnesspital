# Auth-coverage triage (audit V1) — OWNER DECISION required, NOT auto-applied

`mh_scan --only auth_coverage` on BE: **38 BLOCK** (API endpoints with no `[RequireAuth]`) + **21 HIGH** (`*Service.cs` methods — **not endpoints**, `[RequireAuth]` N/A; softer signal / scanner over-reach — review separately, ignore for auth).

## Why NOT auto-applied (deliberate)
Blindly locking these risks a **production outage**: many are likely **public-by-design** (payment gateway webhooks / POS-hardware callbacks, OTP verification), and the protected ones each need the **correct** `[RequireAuth(Functions.FunctionNames.<X>, Functions.Actions.<CanY>)]` — which depends on the BE permission model an agent shouldn't guess. The scanner is the durable safety net (flags these BLOCK; gate CI with `--fail-on block`). Fix per-Api, with the owner, with testing.

## Triage — 38 BLOCK endpoints
| Api | # | Likely purpose | Risk if locked | Recommendation |
|---|---|---|---|---|
| `PaymentSoundboxApi` | 4 | POS soundbox callback | 🔴 breaks POS | verify webhook → WHITELIST or token-auth |
| `PaymentPosDeviceApi` | 4 | POS device callback | 🔴 | same |
| `PaymentPosTransactionApi` | 2 | POS txn callback | 🔴 | same |
| `PaymentApi` | 3 | gateway callback / pay | 🔴 | verify which are webhooks vs internal |
| `PaymentReconcileApi` | 1 | reconcile (internal job?) | 🟠 | probably ADD-AUTH |
| `PaymentMethodsApi` | 1 | list methods (maybe public) | 🟡 | verify |
| `PaymentMerchantConfigApi` | 4 | admin config (holds creds) | 🟠 should be auth'd | ADD-AUTH (admin perm) — confirm no caller breaks |
| `VerificationCodeApi` | 1 | OTP send/verify | 🔴 breaks login/register | **WHITELIST** (public-by-design) |
| `DiagnosticsApi` | 12 | diagnostics / health | 🟠 maybe internal-only | owner: lock **or** network-restrict (don't expose) |
| `UserApi` | 1 | user (register? admin?) | 🟡 | verify which action |
| `FunctionApi` | 1 | permissions metadata | 🟡 | likely ADD-AUTH |
| `RetailJobApi` | 2 | retail batch job | 🟢 internal | ADD-AUTH (retail perm) |
| `RetailExchangeApi` | 1 | retail exchange | 🟢 internal | ADD-AUTH |
| `RetailOrderApi` | 1 | retail order | 🟢 internal | ADD-AUTH |

🔴 = likely public/webhook, locking breaks prod · 🟠 = should be auth'd but confirm callers · 🟢 = clearly internal, add auth · 🟡 = verify purpose.

## Path (per-Api, owner-driven)
1. **Public-by-design** (VerificationCode, confirmed payment webhooks) → add to `AUTH_WHITELIST` in `scripts/mh_scan/scanners.py` (documents intent + clears the BLOCK).
2. **Protected** → add `[RequireAuth(Functions.FunctionNames.<X>, Functions.Actions.<CanY>)]` in a BE worktree, correct permission, **test**, PR.
3. Re-scan: `python scripts/mh_scan --root worktrees/<slug>/be --only auth_coverage --fail-on block` → **0 BLOCK**.

Start with the 🟢 group (RetailJob/Exchange/Order — clearly internal, lowest risk), then the 🟠, and treat 🔴 with the most care (verify the gateway contract before touching).
