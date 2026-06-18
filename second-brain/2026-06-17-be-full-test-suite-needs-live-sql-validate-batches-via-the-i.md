---
title: "BE full test suite needs live SQL — validate batches via the InMemory my-area subset"
date: "2026-06-17"
status: provisional
source: harness-review
scope: backend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/backend
tags: [testing, dotnet-test, sql-server, infra, baseline]
applies_tasks: [test, fix, review]
applies_globs: [worktrees/*/be/MyHospital.Tests/**]
applies_keywords: [dotnet test, full-suite, SQL Server, OneTimeSetUp, InMemory, proc_CodeGenerator, baseline-failures]
expires: ""
---

# What

Running the FULL MyHospital.Tests suite without a live slot SQL Server yields ~76 ENVIRONMENTAL failures (OneTimeSetUp SQL-connect, SQLite, proc_CodeGenerator on EF-InMemory, ServiceStackHost already set, SS free-quota) — pre-existing baseline noise, NOT caused by a bed/reception/shift code change (code-isolation). Validate such a batch via the InMemory-runnable my-area subset (dotnet test --filter FullyQualifiedName~<Class/Method>), and attribute failures by error-signature, not by the full-suite red count.

# Evidence

- dotnet test MyHospital.Tests full = 712 tests, 77 fail: 25x OneTimeSetUp 'Khong ket noi duoc SQL Server local (HospitalDB) localhost,143x', 21x SQLite errors, proc_CodeGenerator-on-InMemory, ServiceStackHost-already-set, ServiceStack free-quota; all my-area InMemory tests pass

# Why It Matters

Prevents mis-attributing a large pre-existing full-suite failure count to your batch and wasting time bisecting; the prior session's '101 pass' was exactly this InMemory subset.

# How To Apply

_See # What above._

# Boundaries

Tests that genuinely need SQL/proc_CodeGenerator (CreateAdmission/ConfirmAdmission code-gen, warehouse import, pricing) require the live slot DB to verify — bring SQL up (worktree.py run-be / docker mssql-hospital-wt3) to validate those.

# Promotion Recommendation

Promote to: engine/rules/backend
Reason: (fill in before promoting)
