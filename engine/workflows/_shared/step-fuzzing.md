# Step-level behavioral fuzzing — non-determinism WITHIN a step, determinism IN the flow

The contract for how agent-browser tests (super-test harvest, progressive-test) vary behavior. Real users do
NOT replay one fixed procedure; a single top-to-bottom fill misses order-dependent bugs. Add controlled
randomness **inside a step**, while the **flow stays fixed**.

## The distinction (load-bearing — do not blur)
- **FLOW = the sequence of steps** (navigate → open form → fill → submit → verify). **FIXED / deterministic** —
  never reorder or skip steps for randomness. The flow is the test's spine.
- **STEP = one action** like "fill + submit the create-room form". **WITHIN a step, randomize the behavior**:
  field-fill ORDER, field VALUES, optional-field toggles. Do NOT replay one identical fill every time.

Example — a 10-field form whose step 10 is "submit": real fill order isn't always `1 2 3 … 10`; it can be
`1 7 6 5 2 9 3 8 4 10`. Test **2–3** such orders, then submit each. The FLOW (open→fill→submit) is unchanged;
the IN-STEP fill is what varies.

## Why
Order-dependent bugs hide behind the happy linear fill: a field's validation that only fires if an upstream
field was filled first; a computed/derived field that goes stale when you edit upstream after downstream; an
enable/disable race; a "required" that only triggers in some orders. Linear fill never reaches them.

## How — bounded + dependency-aware (the agent EVALUATES; it does NOT brute-force)
For a form / multi-input step:
1. **Evaluate the form first.** List fields + **DEPENDENCIES** (B enabled only after A; C's options depend on A;
   required vs optional; cross-field validation). This bounds the LEGAL fill space — never pick an order that
   violates a hard dependency (that's a setup error, not a finding).
2. **Generate 2–3 DISTINCT scenarios** (NOT full combinatorial — most forms have far too many permutations):
   each scenario = a valid fill ORDER (independent fields shuffled; a dependent field always after its
   prerequisite) + a VALUE choice. Keep values valid for a happy-path scenario; an edge/invalid-value scenario
   is a SEPARATE, clearly-labeled scenario — never silently mix invalid values into a "should-pass" run.
3. **Submit after each scenario** and observe. super-test: log any bug + WHICH scenario surfaced it.
   progressive-test: pass/fail per scenario.

## Cross-round no-repeat (bounded randomness, not amnesia)
Record every tried scenario (the exact order + values) in the step's **fuzz ledger**
(super-test: `<run-dir>/fuzz-ledger.md`; progressive-test: read prior `round-*` bug-packets). Before choosing,
read the ledger (incl. prior runs/rounds) and pick scenarios **NOT yet tried** — cover new combinations first.
Only when the legal space is exhausted, fall back to a prior scenario (prefer the one that last FAILED / is most
informative). So a later round ≠ an earlier round unless nothing new remains.

## Boundaries
- FLOW order is FIXED — only in-step behavior is fuzzed.
- Respect field dependencies — never an illegal order just to be "random".
- **2–3 scenarios per step** (bounded — token/time aware), not exhaustive.
- **Repro-determinism:** when a bug is found, record the EXACT scenario (order + values) so it reproduces
  byte-for-byte. Randomness is for DISCOVERY; a found bug must be deterministic to replay.
- The agent decides scenario count + which orders are meaningful (a 2-field form needs 1–2; a 10-field form
  with dependencies needs the agent to pick the 2–3 most behavior-distinct orders).
