---
title: "Audit 'parallelize sequential EF queries with Task.WhenAll' is UNSAFE on a shared DbContext"
date: "2026-06-19"
status: provisional
source: harness-review
scope: backend
confidence: high
owner_confirmed: false
proposed_target: deep-review/checklist
tags: []
applies_tasks: [review, fix]
applies_globs: [myhospital-be/**, worktrees/**/be/**]
applies_keywords: [Task.WhenAll, DbContext, EF, parallel, sequential queries, thread-safe]
expires: ""
---

# What

When an audit flags 'N sequential independent DB queries, parallelize with Task.WhenAll', REJECT that fix if the queries run on ONE shared EF Core DbContext (the BaseService injected Db, via GetAllByTenantAndHospital<T>()). EF Core DbContext is NOT thread-safe; concurrent ops throw InvalidOperationException 'A second operation was started on this context before a previous operation completed'. Safe parallelism needs separate contexts (DbContextFactory) — usually overkill for bounded point-lookups.

# Evidence

- round-1 audit F-002 BuildPatientSummaryAsync ConsultationService.cs:838-890 proposed Task.WhenAll on 6 GetAllByTenantAndHospital queries sharing Db

# Why It Matters

Prevents shipping an audit-suggested 'perf fix' that crashes at runtime under the very concurrency it claims to add.

# How To Apply

_See # What above._

# Boundaries

Does NOT apply when each query uses its own DbContext/scope, or for in-memory CPU work. Sequential is correct for shared-context point-lookups.

# Promotion Recommendation

Promote to: deep-review/checklist
Reason: (fill in before promoting)
