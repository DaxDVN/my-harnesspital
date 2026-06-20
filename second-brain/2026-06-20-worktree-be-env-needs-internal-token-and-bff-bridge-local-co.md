---
title: "worktree-be-env-needs-internal-token-and-bff-bridge-local-config"
date: "2026-06-20"
status: provisional
source: implementation-discovery
scope: backend
confidence: high
owner_confirmed: false
proposed_target: reject
tags: [backend, worktree, env, startup]
applies_tasks: [fix, implement, test]
applies_globs: [worktrees/**/be/.env]
applies_keywords: [worktree, env, startup, make-server, migrate-data, InternalTokenSecret, BffBridge]
expires: ""
---

# What

Local BE worktree .env files may be missing InternalTokenSecret and Bff__BridgeUrl/Bff__BridgeSecret after worktree setup or migrate-data. Build still passes, but make server fails at startup: first InternalTokenSecret config missing, then BffBridgeClient DI cannot resolve BffBridgeOptions.

# Evidence

- worktrees/vital-signs/be and worktrees/ipd-consultation/be failed make server until .env copied main local InternalTokenSecret plus Bff__BridgeUrl=http://localhost:5000 and Bff__BridgeSecret=dev-only-dummy.

# Why It Matters

Prevents false confidence after dotnet build and avoids startup failures when preparing slots for FE login/manual testing.

# How To Apply

_See # What above._

# Boundaries

Local dev worktree setup only; production/BFF secrets must use real matching values.

# Promotion Recommendation

Promote to: reject
Reason: (fill in before promoting)
