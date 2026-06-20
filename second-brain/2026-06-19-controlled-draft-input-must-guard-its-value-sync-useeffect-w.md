---
title: "Controlled draft-input must guard its value-sync useEffect with isFocused, or RHF round-trip clobbers the value mid-type"
date: "2026-06-19"
status: provisional
source: conversation
scope: frontend
confidence: high
owner_confirmed: false
proposed_target: engine/rules/frontend.md
tags: []
applies_tasks: []
applies_globs: []
applies_keywords: []
expires: ""
---

# What

Custom controlled inputs that keep an internal useState 'draft' (text being typed) + commit to the parent later (on blur or on complete) MUST guard their 'sync draft from value prop' useEffect so it does NOT run while the field is focused. Pattern that's CORRECT: CurrencyInput (useEffect { if(!isFocused) setLocalValue(value) }) + DecimalNumberInput (prevExternalRef identity check) + DatePicker (isFocused ref). Pattern that's BUGGY (causes 'type then the value disappears'): input-autosuggest.tsx:193 (useEffect setInputValue(value) with NO focus guard) and time-input-24.tsx:63 (useEffect setDraft(normalize(value)) with NO focus guard). Mechanism: in a react-hook-form, typing fires onChange -> RHF updates field value -> parent re-renders -> the unguarded useEffect runs setDraft/setInputValue(value) mid-type and overwrites what the user just typed (or resets to '' / last-committed). Because InputAutoSuggest backs every ComboBox, this clobbers ComboBox fields app-wide. A second trigger: a sibling useEffect calling form.setValue(thisField, ...) (e.g. ShiftId change -> setValue(StartTimeOverride)) changes the value prop mid-edit and clobbers the draft.

# Evidence

- Vital-signs `Nhiệt độ`/`Cân nặng` (2026-06-19): used a controlled `<input type="number">` that re-derived
  its value via `parseFloat`/`Math.trunc(parsed*10)/10` on EVERY keystroke. Typing `36.` → `parseFloat("36.")=36`
  → React reset the box to `"36"`, stripping the `.` → decimals were untypeable (agent-browser got `367`). Same
  class as the no-focus-guard bug: the controlled value round-trips and clobbers the in-progress draft.
  Fix = reuse the focus-guarded `DecimalNumberInput` (`…/bed-day-config/decimal-number-input.tsx`: local-draft +
  `prevExternalRef` identity check + commit-on-blur), extended with a `maxDecimalPlaces` (truncate-on-blur) prop.
  `docs/audit/2026-06-19/vital-signs-tab-spec-gap.round-1.md` §6 G9.

# Why It Matters

Fix = add an isFocused guard to the value-sync useEffect (input-autosuggest: 'if(!isFocused) setInputValue(value)' + add isFocused to deps; time-input-24: add an isFocused ref + onFocus/onBlur + guard). When building/reviewing any custom controlled input with a draft state, REQUIRE the focus-guard on the value->draft sync effect. CurrencyInput/DecimalNumberInput/DatePicker are the correct reference patterns. NOTE: ComboBox 'clear typed text on blur when no option selected' is by-design (must select); DatePicker reverting an INCOMPLETE date on blur is by-design; relatives-grid prepend() shifting field.id keys remounts a DatePicker mid-edit (separate remount bug — use append or stable keys).

# How To Apply

_See # What above._

# Boundaries

_No specific boundaries noted._

# Promotion Recommendation

Promote to: engine/rules/frontend.md
Reason: (fill in before promoting)
