---
title: "Expected query errors (latest-X 404 on empty) must opt out of the global error toast"
date: "2026-06-21"
status: provisional
source: bug-fix
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: reject
tags: [fe, react-query, error-toast, not-found, empty-state, query-provider, meta]
applies_tasks: [fe, bug-fix, implement]
applies_globs: [**/*.tsx]
applies_keywords: [toast, error, 404, not-found, empty, latest, query, meta, suppressGlobalError]
expires: ""
---

# What

FE has a GLOBAL queryCache.onError (src/providers/query-provider.tsx) that toasts all query errors. For EXPECTED errors a component handles itself (e.g. a latest-X 404 on an empty collection rendered as an empty state), the query must opt out: pass meta:{ suppressGlobalError:true } in the hook options; the global onError(error, query) returns early when query.meta?.suppressGlobalError, AND the BE-recovery poller must exclude such queries (q.state.status==='error' && !q.meta?.suppressGlobalError) so it does not re-invalidate/re-toast every 10s. Also fix the per-query retry guard to match the ACTUAL error code (e.responseStatus?.errorCode), not a guessed '404'. Generated query hooks forward options (incl meta) into useQuery via ...options, so meta passes through.

# Evidence

- Empty inpatient visit threw a visible error every page load: BE GetLatestVitalSigns returns 404 VITAL_SIGNS.NOT_FOUND, and the global queryCache.onError in query-provider.tsx toasts EVERY query error (except 403). Worse, the BE-recovery poller treated the permanently-errored 404 query as BE-down, pinging every 10s and re-invalidating → re-toasting forever. The latest-block retry guard checked errorCode==='404' but the real code is 'VITAL_SIGNS.NOT_FOUND', so it also retried.

# Why It Matters

A normal empty state surfaced as a blocking error toast on every load (and looping every 10s) is a real UX defect; treating 'no rows yet' as an error is wrong.

# How To Apply

_See # What above._

# Boundaries

FE. Alternative (BE) fix: return an empty/null result instead of 404 for latest-of-empty; but the FE meta opt-out is reusable for ALL expected-error queries.

# Promotion Recommendation

Promote to: reject
Reason: (fill in before promoting)
