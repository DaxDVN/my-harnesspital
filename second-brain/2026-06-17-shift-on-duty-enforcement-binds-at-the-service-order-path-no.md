---
title: "Shift-on-duty enforcement binds at the service-order path, not at inpatient admission-receive"
date: "2026-06-17"
status: provisional
source: bug-fix
scope: backend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/backend
tags: [backend, shift, schedule, reception, admission, enforcement]
applies_tasks: [fix, implement]
applies_globs: [myhospital-be/**, worktrees/**]
applies_keywords: [shift, ShiftAssignment, UseShiftAssignment, reception, admission, service order, enforcement, ca trực]
expires: ""
---

# What

The 'doctor must be on an Approved shift for the room' rule can only be enforced where doctor+room+shift bind — the OPD/service-order path (VisitServiceOrderService, per service line). Inpatient admission-receive binds department+bed only (no room dimension), so a shift gate cannot live there. Bypass fix: in EnsureRequiredShiftAssignment treat global UseShiftAssignment as a FLOOR (item-level false cannot disable it) and require the shiftAssignmentId FK first; the FE must re-validate the FK via hasApprovedAssignmentToday on any doctor/room change (never trust a stale truthy FK).

# Evidence

- InpatientAdmissionOrderService.ReceiveAsync has no RoomId/ShiftAssignment; MedicalVisit has no RoomId column; gate lives in VisitServiceOrderService.ValidateShiftAssignment per service line

# Why It Matters

Prevents wiring a non-functional shift gate at admission-receive and prevents the item-override-false + stale-FE-FK bypass that let an off-shift doctor be received.

# How To Apply

_See # What above._

# Boundaries

If MedicalVisit later gains a RoomId / a dedicated inpatient room-assign step appears, revisit. Depends on schedule-approval yielding Approved slots, else over-blocks.

# Promotion Recommendation

Promote to: engine/rules/backend
Reason: (fill in before promoting)
