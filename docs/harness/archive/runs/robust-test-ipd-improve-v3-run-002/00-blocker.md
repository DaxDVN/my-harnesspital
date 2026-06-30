# ENVIRONMENT BLOCKER — run-002 halted at env gate

**Discovered at:** 2026-06-26 ~05:01 (after FE startup, before first bug test)
**Blocker class:** infrastructure (Redis container stopped → BE master-instance resolver times out)
**Scope:** blocks ALL 40 bugs in this run
**Owner decision required:** **NO** (env fixed by owner instruction "set up để container đó luôn chạy đi")
**Status:** ✅ **RESOLVED** — Redis up + auto-restart policy set + secondary config mismatch worked around

## Resolution Trace

```text
2026-06-26T05:01:28Z  BE auth fails (TimeoutException, master instance resolver)
2026-06-26T05:08      Owner: "set up để cái container đó luôn chạy đi"
2026-06-26T05:08      docker start redis-hospital  → container up
2026-06-26T05:08      docker update --restart unless-stopped redis-hospital  → persistent
2026-06-26T05:08      docker exec redis-hospital redis-cli ping  → PONG
2026-06-26T05:09      curl POST /json/reply/Authenticate  → 200 SUCCESS (UserId 176)
2026-06-26T05:10      FE login still failing → root cause #2: `.env.test` points to :5005
2026-06-26T05:11      Restart FE with `VITE_BACKEND_URL=http://localhost:5003` env override
2026-06-26T05:12      agent-browser login with bvtest3  → redirected to /home
2026-06-26T05:12      Master data calls (Hospital, Department, EntityHospitalShare, …) all 200
```

## Secondary Issue (separate root cause, same symptom)

`worktrees/ipd-improve-v3/fe/.env.test` has `VITE_BACKEND_URL=http://localhost:5005` (wrong port).
Slot 3 BE is on :5003 per `engine/rules/session-boot-details.md` and `scripts/worktree.py list`.
This made every FE call go to an empty :5005 — the Redis-fix alone would not have unblocked the UI.

**Workaround (no file edit):** FE was restarted with the env override inline:
```bash
cd worktrees/ipd-improve-v3/fe
VITE_BACKEND_URL=http://localhost:5003 npm run dev:test
```

**Owner follow-up (when convenient, not blocking this run):** decide between
(a) patching `.env.test` to 5003,
(b) keeping the env override at startup, or
(c) re-running `python scripts/worktree.py` to regenerate slot env files.

## Root Cause (definitive)

The `.NET` BE on slot 3 uses ServiceStack's `RedisManagerPool` for cache + session
(`worktrees/ipd-improve-v3/be/MyHospital/Configure.Redis.cs`). The connection string comes
from `appsettings.Development.json` and the BE process env var:

```text
ConnectionStrings__RedisConnection = redis://localhost:6379
```

There is **no Redis process listening on `localhost:6379`** because the container that
provides it was **stopped by hand 3 hours ago**:

```text
$ docker ps -a --filter name=redis
CONTAINER ID   IMAGE            STATUS                   PORTS     NAMES
b64fc49717fb   redis:7-alpine   Exited (0) 3 hours ago             redis-hospital
```

The container logs show a clean `SIGTERM` / "User requested shutdown" at 2026-06-26 02:03:30,
exit code 0, RestartCount 0. So someone (or a script, or a Docker housekeeping job) ran
`docker stop redis-hospital` and nothing restarted it.

When the FE calls `POST /json/reply/Authenticate`, ServiceStack's `RedisManagerPool` tries to
resolve a Redis master node. The TCP connect to `localhost:6379` fails (nothing listening).
After 10 seconds, ServiceStack throws the TimeoutException the BE returns. The auth request
never reaches `MyHospitalCredentialsAuthProvider.TryAuthenticateAsync`.

This is why the same error fires for **every** login attempt, not just `bvtest3` — the Redis
layer is upstream of the credentials provider.

## Symptom (raw)

```json
{
  "ResponseStatus": {
    "ErrorCode": "TimeoutException",
    "Message": "Could not resolve master instance within 10000ms RetryTimeout",
    "StackTrace": "[Authenticate: 6/26/2026 5:01:28 AM]:\n[REQUEST: {provider:credentials,...}]"
  }
}
```

## Environment Status at Halt

| Component | State | Note |
|---|---|---|
| FE vite dev (started for this run) | killed | pid 73434/73447; clean shutdown |
| BE slot 3 (worktree `ipd-improve-v3`) | running but degraded | pid 59745; login broken |
| BE slot 1, 2, 4 | DOWN | not running on :5001, :5002, :5004 |
| SQL slot 3 (`localhost,1436/MyHospital`) | not verified | login never reached DB query |
| Login (bvtest3) | ❌ BLOCKED | master instance timeout |
| agent-browser session | closed | no leaked state |

## Verified Manually

```bash
# Direct curl to slot 3 BE auth endpoint
curl -s -X POST http://localhost:5003/json/reply/Authenticate \
  -H "Content-Type: application/json" \
  -d '{"provider":"credentials","UserName":"lynkhanh9822@gmail.com",
       "Password":"12.[s7HXZQ;NfAoF","Meta":{"code":"bvtest3"}}'
# → TimeoutException master instance
```

This is NOT a frontend bug. The request never reaches the application code.

## Why Not a Single-Bug Blocker

If 1 of the 40 bugs needed a specific master role or write path, that could be a single blocked
folder. But **login itself is broken on slot 3**, so no authenticated flow can be tested at all
(reception, schedule, bed, examination all require login).

## Options for Owner

1. **Start the Redis container** (one command, low risk — keeps the run scoped to `ipd-improve-v3`):
   ```bash
   docker start redis-hospital
   ```
   Then say "retry" and I will pick up the run at the env gate and triage all 40 bugs.
   Risk: someone stopped this Redis 3h ago for a reason (deploy? maintenance?). Worth a
   quick check first; if you're sure, just say the word.
2. **Switch worktree to a working slot** (slot 1/2/4 BE are down; would need those started first):
   - requires owner instruction to switch worktree
3. **Cancel the run** and re-schedule once env is healthy.

## What I Did Before Stopping

- Started `npm run dev:test` for FE slot 3 (was down) — verified `200 OK` on `/auth/signin`
- Loaded login form, filled bvtest3 credentials — submit hit the BE master-instance timeout
- Captured the TimeoutException response (above)
- Closed agent-browser session, killed FE vite process, did NOT touch source code
- Wrote 00-robust-test-state.md, 01-test-map.md, 02-bug-index.md, and empty BUG-001..BUG-040 folders
- All 40 bugs remain in `CANDIDATE` state, but the run is effectively BLOCKED at env gate

## Not Done

- Did not open any bug dossier beyond the env blocker
- Did not modify any source code, generated DTO, FE module, or BE controller
- Did not run any DB migration or data change
- Did not capture screenshots (per triage rule — no screenshot by default)
