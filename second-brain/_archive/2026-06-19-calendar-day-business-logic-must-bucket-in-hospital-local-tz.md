---
title: "Calendar-day business logic must bucket in hospital-local TZ, not raw UTC .Date"
date: "2026-06-19"
status: provisional
source: harness-review
scope: backend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/backend
tags: []
applies_tasks: [fix, implement, review]
applies_globs: [worktrees/*/be/**, myhospital-be/**]
applies_keywords: [timezone utc date dayofweek bed-day schedule local vietnam]
expires: ""
---

# What

Slicing/comparing on .Date or DayOfWeek of a UTC-valued DateTime mis-attributes calendar days/weekdays for a UTC+7 hospital (a local-midnight-crossing event lands on the wrong day). Convert to hospital-local (DateTimeHelper.ToVietnam / a single ToHospitalLocal point) BEFORE .Date/.DayOfWeek; durations are tz-invariant so only day-bucketing changes. Mirror the ward-map convention (EndTimeOfDay(local).ToUniversalTime()).

# Evidence

- BedDayCalculationService UTC .Date slicing (F-007); recurring ExpandDates/MatchesMask UTC weekday (F-013); ward-map already used EndTimeOfDay().ToUniversalTime()

# Why It Matters

Prevents bed-day overcount/undercount and 'recurring schedule only creates today' (weekday bit mismatch) — billing + scheduling correctness.

# How To Apply

_See # What above._

# Boundaries

Calendar-day/weekday logic on UTC timestamps; not needed for pure elapsed-duration math.

# Promotion Recommendation

Promote to: engine/rules/backend
Reason: (fill in before promoting)
