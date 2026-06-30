# BUG-ENV-001 — Slot 3 BE master-instance timeout on Authenticate

## Metadata

- status: BLOCKED
- severity: BLOCK
- bug_class: missing-master-instance-resolver
- scanner_candidate: yes
- scanner_candidate_tier: mh_scan
- flow: env gate (login)
- actor: bvtest3 (lynkhanh9822@gmail.com — TenantId=6, HospitalId=7)
- route/url: POST http://localhost:5003/json/reply/Authenticate
- worktree: ipd-improve-v3 (slot 3)
- observed_at: 2026-06-26T05:01:28Z
- blocks: all 40 BUG-001..BUG-040 in this run

## 00 Observation

Expected:
- After FE submits credentials, BE returns 200 with `AuthenticateResponse` containing
  `UserId`, `SessionId`, `BearerToken` (or sets `ss-id` HttpOnly cookie), and the FE redirects
  to `/home`.

Actual:
- BE returns 200 HTTP status but body has `ResponseStatus.ErrorCode = "TimeoutException"`
  with message `"Could not resolve master instance within 10000ms RetryTimeout"`.
- FE stays on `/auth/signin` and shows no toast / no error in the UI (toast disabled in
  `useAuthenticate` with `disableErrorToast: true` in `auth-provider.tsx`).
- Repeated fetch calls in the FE console show the same error.

Evidence:
```text
$ curl -s -X POST http://localhost:5003/json/reply/Authenticate \
    -H "Content-Type: application/json" \
    -d '{"provider":"credentials","UserName":"lynkhanh9822@gmail.com",
         "Password":"12.[s7HXZQ;NfAoF","Meta":{"code":"bvtest3"}}'

{"UserId":null,...,
 "ResponseStatus":{
   "ErrorCode":"TimeoutException",
   "Message":"Could not resolve master instance within 10000ms RetryTimeout",
   "StackTrace":"[Authenticate: 6/26/2026 5:01:28 AM]:\n[REQUEST: {provider:credentials,...}]"
 }}
```

Agent-browser console (truncated, last 5 lines):
```text
[warning] [2026-06-26T05:00:23.663Z] [WARN] execute() caught non-ApiError: {"message":"fetch error","type":"TypeError"}
[error]   [2026-06-26T05:00:23.649Z] [ERROR] [IDB] Failed to open database: {}
[error]   [IDB Storage] Error getting entities from MultiLanguage: {}
[error]   [IDB Storage] Error getting item: {}
[error]   [IDB Storage] Error getting entities from MultiLanguage: {}
```

The "fetch error TypeError" entries are a downstream symptom — the JsonServiceClient wraps
the BE's 200-with-error-body and rejects the promise with a TypeError, which is then
re-thrown by `useMutation` and caught by the auth provider (which logs but does not surface
to UI because `disableErrorToast: true`).

## 01 Reproduction

Preconditions:
- BE process running on `:5003` (pid 59745, named `MyHospital`).
- DB primary for slot 3 expected on `localhost,1436` (not verified at this point because
  login never reached DB).

Steps:
1. Start FE: `cd worktrees/ipd-improve-v3/fe && npm run dev:test` (port 3003).
2. Open `http://localhost:3003/auth/signin` in agent-browser.
3. Fill Mã khách hàng = `bvtest3`, Tên đăng nhập = `lynkhanh9822@gmail.com`,
   Mật khẩu = `12.[s7HXZQ;NfAoF`.
4. Click "Đăng nhập".
5. Observe: URL stays `/auth/signin`, no UI feedback, console shows
   `fetch error TypeError`.
6. Repeat with `curl` directly against the BE → same `TimeoutException` body.

Result: login fails 100% of attempts with the same `TimeoutException - Could not resolve
master instance within 10000ms RetryTimeout`.

Repro reliability: 100% (every request fails the same way; not flaky).

## 02 Triage

False-positive checks:

- Required fields filled: ✅ (Mã khách hàng, Tên đăng nhập, Mật khẩu all present)
- Correct actor/permission: ✅ (bvtest3 is the mandated test credential per
  `engine/rules/session-boot-details.md`)
- API replay or validation checked: ✅ (direct curl against the BE endpoint reproduces
  the failure, no FE in the loop)
- Live code gate checked: N/A (login never reached application code)
- Test data/state verified: ✅ (slot 3 is the worktree's own slot; no cross-slot test)
- Network/browser artifact captured: ✅ (curl response + agent-browser console)
- Same issue reproduced or disproved outside the first observation: ✅ (reproduced via
  direct curl outside the browser)

Verdict: **NOT a product bug** in any of the 40 tested features. It is an infrastructure
issue inside the slot-3 BE process: the master-instance resolver cannot elect a master
within 10s. Likely causes:
- Redis / service-bus primary unreachable
- DB primary for `localhost,1436` unreachable from BE host
- A misconfigured cluster resolver inside the .NET host

This is **not** a UI bug, not a logic bug, not a data bug. The reported tester bugs
cannot be reached because login itself does not complete.

## 03 RCA (infrastructure, not product)

Root cause: **the Redis container `redis-hospital` is stopped**, so the BE's
ServiceStack `RedisManagerPool` cannot reach `localhost:6379` and times out at the
master-instance resolver.

Chain of causation (verified):

1. BE uses ServiceStack.Redis via `ConfigureRedis` →
   `worktrees/ipd-improve-v3/be/MyHospital/Configure.Redis.cs:18` registers
   `RedisManagerPool(MyHospitalSettings.RedisConfig)`.
2. `MyHospitalSettings.RedisConfig` →
   `worktrees/ipd-improve-v3/be/MyHospital.Utilities/MyHospitalSettings.cs` reads
   `ConnectionStrings:RedisConnection` → `redis://localhost:6379` (confirmed via
   `appsettings.Development.json` and the live BE process env
   `ConnectionStrings__RedisConnection=redis://localhost:6379`).
3. `docker ps -a --filter name=redis` →
   `b64fc49717fb redis:7-alpine Exited (0) 3 hours ago redis-hospital`.
   `docker inspect redis-hospital` shows:
   - `StartedAt: 2026-06-22T09:31:41`
   - `FinishedAt: 2026-06-26T02:03:30`
   - `ExitCode: 0`
   - `RestartCount: 0`
   - `Error: ""`
   - Container logs: `signal-handler Received SIGTERM scheduling shutdown... User requested shutdown... Saving the final RDB snapshot before exiting... Redis is now ready to exit, bye bye...`
4. No other Redis is listening on `localhost:6379`
   (`ss -tlnp | grep 6379` returns nothing, no `redis-server` process).
5. Every `POST /json/reply/Authenticate` therefore waits 10s for the Redis client
   to elect a master, fails, and ServiceStack returns the TimeoutException. The
   request never reaches `MyHospitalCredentialsAuthProvider.TryAuthenticateAsync`.

Evidence files in `evidence/`:
- `auth-curl-response.json` — raw BE response
- `agent-browser-console.txt` — FE console at login time
- `be-process.txt` — `ps -p 59745` shows the BE still up 36 min
- `ports.txt` — only :5003 (BE) and SQL listening; nothing on :6379
- `docker-inspect-redis.txt` (added after this RCA update)
- `docker-logs-redis.txt` (added after this RCA update)

Blast radius: every login to slot 3 fails. The fix is a one-line `docker start redis-hospital`.
Other slots (1/2/4) are also down, so they are not a usable fallback without starting them first.

## 04 Fix Plan

(Out of scope for `robust-test` — the workflow does not edit infrastructure / BE / DB.
This folder is the canonical handoff to the owner for ops. Concrete fix paths for owner
to choose from are in `00-blocker.md`.)

Root cause boundary: slot-3 BE process master-instance resolver.
Reuse evidence: N/A.
Regression map: N/A.
Proposed fix: see `00-blocker.md` Options 1/2/3.
Files likely touched: BE infrastructure only (no FE/BE code change).
Files explicitly not touched: `worktrees/ipd-improve-v3/fe/**`, `worktrees/ipd-improve-v3/be/**`,
`specs/**`, generated DTOs, DB data.
Alternative considered: switch to slot 1/2/4 — blocked because those BEs are not running.
Why not bigger fix: this is a triage-time env gate, not a code-fix cycle. A bigger
investigation is owner-approved.
Risk: env-level; no code regression risk.
Validation needed: re-run `curl POST /json/reply/Authenticate` and confirm
`UserId` is non-null + a `ss-id` cookie is set; then re-run this `robust-test` run.
Owner approval needed: yes (decide Option 1/2/3 in `00-blocker.md`).

## 05 Fix Attempts

Fix reference: not started (out of scope for `robust-test`).
Changed files: none.
Notes: FE was started and cleanly killed for this run; no source edit; no DB mutation;
no DTO regen; no generated-client regen.

## 06 Retest

Retest steps: deferred until env gate passes.
Result: N/A.
Remaining risk: 40 bugs unverified.

## 07 Review Brief

Question for high-reasoning reviewer: N/A (this is an env halt, not a code fix).
Is the fix approach reasonable, minimal, and low-regression? N/A.
Should `bug_class` be promoted to a deterministic scanner/rule? Yes — candidate rule:
add a smoke gate in `mh_scan` or `engine/scripts/slot_health.py` that does
`POST /json/reply/Authenticate` with the bvtest3 credential and fails the run if the
response is not a `AuthenticateResponse` with non-null `UserId`. This would catch
slot-infra issues before a tester burns an hour on FE/BE work. Suggest filing as a
follow-up after the env is healed.
Fix reasonableness: N/A.
Regression risk: N/A.
Adjudication needed: no.

Reviewer should inspect:
- the curl response in `evidence/`
- the agent-browser console in `evidence/`
- the BE process status (`ps -p 59745` + `ss -tlnp | grep 5003`)
- `00-blocker.md` for owner decision options
