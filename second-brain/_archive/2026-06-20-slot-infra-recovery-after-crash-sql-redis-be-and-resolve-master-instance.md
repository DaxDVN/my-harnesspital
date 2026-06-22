---
title: "Worktree slot recovery after a host crash: start SQL + Redis BEFORE BE; 'resolve master instance' timeout = Redis down"
date: "2026-06-20"
status: provisional
source: harness-session
scope: infra
confidence: high
owner_confirmed: false
proposed_target: docs/guides/worktree-zellij-manual or engine/rules
tags: [infra, worktree, docker, sql, redis, backend, login, recovery]
applies_tasks: [test, fix, e2e, run]
applies_globs: []
applies_keywords: [crash, refused, ERR_CONNECTION_REFUSED, resolve master instance, RetryTimeout, redis, mssql, slot, login, "5001", "3001", "1434", "6379"]
expires: ""
---

# What

When a host/process crash takes a worktree slot down, the FE/BE AND their Docker deps all stop. Recovery order matters — start data deps before BE, or BE aborts (exit 134/SIGABRT) on startup.

Slot SQL containers: `mssql-hospital-wt1`=:1434 (slot1), wt2=:1435, wt3=:1436, wt4=:1437, `mssql-hospital-main`=:1433. Redis: `redis-hospital`=:6379. All exit together on a crash.

Recovery sequence (slot 1 / vital-signs example):
1. `docker start mssql-hospital-wt1` — wait until `ss -ltn | grep :1434` listens + `docker logs --tail mssql-hospital-wt1` shows "Recovery is complete" (~10-30s; container "Up" ≠ SQL ready).
2. `docker start redis-hospital` — verify `:6379` listening.
3. FE: `cd worktrees/<slug>/fe && npm run dev` (port from `.env` `VITE_DEV_PORT`). BE: `just wt-run-be <slug>` (loads `.env`, binds :500X). Use the harness `run_in_background` WITHOUT a trailing `&` — a double-background (`&` + run_in_background) lets the parent shell exit and SIGABRTs dotnet.

# Evidence

- BE crash log: `Microsoft.Data.SqlClient.SqlException ... server was not found` → SQL slot container was down. Started `mssql-hospital-wt1` → BE then started clean.
- **Login failed with BE `TimeoutException: "Could not resolve master instance within 10000ms RetryTimeout"` (statusCode 500) — this specific error means REDIS (`redis-hospital` :6379) is down**, not SQL. `redis-hospital` had `Exited`. Starting it fixed login. (The auth/tenant "master instance" resolution uses Redis.)

# Why It Matters

Saves a long misdiagnosis: a refused FE/BE (`ERR_CONNECTION_REFUSED`, HTTP 000) after a crash is usually the whole stack down, and a login that hangs/500s with "resolve master instance" is REDIS, not the app. BE won't start at all if its slot SQL is unreachable.

# How To Apply

After any "page won't load / login 500" on a slot: `docker ps -a | grep -E 'mssql|redis'` → start the exited slot SQL + redis (+ main 1433 if tenant-registry needed) → wait for SQL "Recovery is complete" + redis :6379 → then start BE + FE. Verify ports 200 before driving the browser.
