# Phase Plan - IPD Consultation

## Recommended Worktree

Suggested slug: `ipd-treatment-consultation`.

This worktree can run in parallel with `ipd-vital-signs-tab` if generated DTO/client changes are coordinated.

## Phase HC0 - Documentation And Boundary Decisions

Goal: finalize requirement/design/API docs for treatment-progress foundation and consultation.

Decisions:

- Is `Tờ điều trị` in scope before consultation? Recommended: yes.
- What status is eligible for latest treatment sheet prefill: latest saved draft, latest signed, or latest not-cancelled?
- Is signature integration real in this phase or only status modeling?
- Are consultation participants structured or free text in phase 1?
- What is the exact boundary with specialty examination?

Exit criteria:

- Final domain split:
  - treatment progress,
  - clinical-progress consultation minutes,
  - drug consultation minutes,
  - consultation invitations.
- API spec and data model draft reviewed.

## Phase HC1 - Treatment Progress Foundation

Goal: create canonical `Tờ điều trị / Diễn biến người bệnh` source.

Candidate deliverables:

- BE entities/API/read model for treatment notes.
- FE treatment note list and create/edit form.
- Latest treatment note endpoint for consultation prefill.
- Minimal status/lock model.

Not required yet:

- Full order cards.
- Full prescription/CLS/VTYT/blood flows.
- Full signature infrastructure if unavailable.

## Phase HC2 - Clinical-Progress Consultation Minutes

Goal: implement basic consultation minutes in inpatient detail.

Candidate deliverables:

- List consultation minutes for current visit.
- Create/edit draft.
- Prefill patient snapshot and diagnosis/progress from latest treatment note.
- Save draft.
- Send/sign status if final phase includes it.
- Read-only locked view.

## Phase HC3 - Signature Workflow

Goal: implement legal workflow details.

Candidate deliverables:

- Pending signature status.
- Chair/secretary signature actions.
- Lock after signed.
- Optional waiting-for-signature list if product confirms a separate dashboard.

## Phase HC4 - Consultation Invitation

Goal: implement `Giấy mời hội chẩn`.

Candidate deliverables:

- Draft/send invitation.
- Recipient logic by consultation scope.
- Confirm/decline attendance.
- Attachments.
- Lock recipient set and files after send.

## Phase HC5 - Drug Consultation And Medication Integration

Goal: implement drug consultation and prescription validation.

Candidate deliverables:

- Drug consultation minute with proposed drug list.
- Medication warning when a drug requires consultation.
- Link from medication order to create drug consultation minute.
- Signing/sending medication order validates consultation-required drugs.

Risk:

- This phase touches medication, pharmacy, order signing, and potentially insurance/billing. It should not be folded into HC1/HC2.

## Validation Seeds

BE:

- Treatment note create/list/latest tests.
- Consultation minute create/update/status tests.
- Authorization and tenant/hospital scope tests.
- Recipient permission tests for invitation confirm/decline.

FE:

- Form validation for required fields.
- Status-based read-only/edit mode.
- Prefill from latest treatment note.
- Inpatient detail tab smoke.

