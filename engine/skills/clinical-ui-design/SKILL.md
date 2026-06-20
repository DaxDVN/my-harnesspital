---
name: clinical-ui-design
description: clinical/enterprise HIS UI design — calm, dense, high-craft, keyboard-first, color-has-meaning; the clinical counterpart to frontend-design. Use when designing/improving HIS screens, forms, data tables, dashboards, board/map views. Give it a URL — it drives agent-browser to log in (harness credential; STOPS if login fails) and capture the live screen, researches the real user + the domain object's natural metaphor, AUDITS what data/capabilities the system actually has (CodeGraph + rg) so each direction is feasible-now or flagged needs-new-data with upgrade suggestions, then in PREVIEW MODE emits a standalone before + multiple after-* HTML mocks (one per design METAPHOR, not per effort level, never beauty-ranked — taste is the owner's) to docs/ui-mocks/ (no source edits) so the owner picks a direction before any React change.
---

# Clinical UI Design (the clinical counterpart to `frontend-design`)

Anthropic's `frontend-design` skill is tuned for **marketing/brand** work: a distinctive identity,
"one real aesthetic risk", characterful display type, "spend your boldness". That *direction* is wrong for a
hospital information system. But the common over-correction is also wrong: **clinical ≠ bland.** A bed-map
that looks like a default Tailwind admin template is a FAILURE even if it is "calm and semantic".

> **The enemy is GENERIC, not beautiful. Take zero decoration — and maximal craft.**

The best dense operational software (Linear, Stripe dashboard, modern EMR ops boards, OR/bed boards,
air-traffic & NOC control rooms) is **dense AND beautiful**: precise spacing, real type hierarchy, restrained
but considered color, meaningful depth, micro-affordances, a layout that *matches the shape of the work*.
That is the bar. "Calm" means *no noise*, not *no quality*. This skill exists to hit clinical correctness
**and** craft — not to produce austere, forgettable forms.

The user is a nurse entering vitals at 3am, or a charge nurse scanning 20 inpatients for the one abnormal
value. They are experts under time pressure who will use this screen thousands of times. They do not want to
be *delighted by decoration* — they want a **well-made instrument**: fast, certain, never misleading, and
good enough to look at all day without fatigue. A distinctive *look* is a liability; **craft is not.**

This skill is **consistent with — and never overrides** `engine/rules/frontend.md` (the live FE convention
canon: React 19 + shadcn/ui + Tailwind 4 + React Query via module adapter + `useMasterData` + id-only,
generated DTOs read-only). Read it for the *implementation contract*; read this for the *design direction*.

---

## Two modes — pick by what the owner asked

- **PREVIEW mode (default when unsure, and whenever the owner says "mock", "show me first", "đừng apply",
  "xem trước", "thử", "preview", or has NOT explicitly approved a code change):** research + capture +
  produce standalone static mocks. **Do not touch any source code.** See "Preview mode" below.
- **APPLY mode (only when the owner explicitly approves a direction from a prior preview):** implement in the
  real React codebase per "How to apply" Step 4, in a worktree.

When in doubt, PREVIEW. Never edit source in preview mode.

---

# PHASE 1 — UNDERSTAND before you design (the part most "generic" output skips)

Most mediocre clinical UI comes from skipping straight to "make cards look nicer". Do NOT. Generic output is
the symptom of shallow understanding. Spend real effort here first — and **write your findings into the
README** so the owner sees the reasoning, not just the pixels.

### 1a. WHAT is this screen? — the artifact's genre (decide this FIRST, before user or data)

The screen's name and nature already tell you what KIND of artifact it is, and **the genre dictates the
form.** Designing a map as a dashboard is the root cause of "it doesn't look like what it is". Name the genre
out loud and honor it:

- **Sơ đồ / map / floor-plan** → must be **SPATIAL**: the user reads layout and pattern, not a list of rows.
  A "Sơ đồ khoa phòng" must *look like the ward* — rooms as regions, beds in position.
- **Bảng / board** → a status grid. **Danh sách / register** → a list/table. **Biểu đồ / timeline** → a
  visualization. Match the word to the form.

If the screen is a **Sơ đồ**, the answer is a real **MAP** — not a dashboard, board, table, or queue. Two
consequences that earlier versions kept getting wrong:

- **Schematic ≥ geographic.** You do NOT need exact coordinates to make a map. A *schematic* layout (rooms
  arranged as a floor plan; beds positioned within each room) reads and works as a map and is **buildable
  today** — like a subway map: spatial without being to-scale. "No `bed.positionRow/Col`" is **not** an excuse
  to fall back to a card grid — it only means schematic, not geographic. Tag the to-scale version
  NEEDS-NEW-DATA, but still deliver a genuine schematic map now.
- **Overview ≠ list.** A map/overview conveys understanding through spatial **pattern** (position, color,
  shape) — NOT by rendering every item's full text at once. Listing every bed with full labels is itself "too
  much on screen"; that's a register, not a map. **Aggregate at the overview; reveal per-bed detail on
  focus/hover/click.** Density of *information* is fine; density of *text* on an overview is clutter.

### 1b. The user & the decisions (not a one-liner — actually reason about it)

Answer concretely, from the captured screen + the domain, not from a template:

- **Who** uses this, in what role? (charge nurse, ward clerk, doctor on rounds, pharmacist, billing clerk…)
- **Where & under what pressure?** (mid-round on a phone? at a busy station mid-shift? at 3am, one-handed?)
- **What decisions do they make here, in ≤2 seconds?** List them. ("Which bed is free for this new
  admission?" "Which patient is deteriorating?" "Is this room full?") The screen exists to make THESE
  decisions instant. Everything that doesn't serve a top decision is noise.
- **How often, and what's the cost of a misread?** (a wrong bed assignment, a missed allergy → clinical
  incident). High-frequency + high-cost = the case for both density AND craft.
- **What is the user's existing mental model?** They already think about the ward a certain way (a floor of
  rooms; a list of my patients; a timeline of the shift). The UI should match that model, not impose a new one.

### 1c. The domain object & its NATURAL metaphor (this is what kills "generic card grid")

Ask: **what shape is this data, really?** Most clinical data is not "a list of cards" — it has an inherent
structure the UI should embody:

| The data is really… | Natural UI metaphor | Generic-trap to avoid |
|---|---|---|
| a **physical space** (beds, rooms, ward, OR) | **floor-plan / board / map** — position carries meaning | a flat card grid that throws away spatial layout |
| a **timeline** (shift, schedule, LOS, vitals over time) | **timeline / track / trend chart** | a table of timestamps |
| a **pipeline / status flow** (admission → discharge, order states) | **kanban / status lanes** | unrelated rows |
| a **hierarchy** (dept → ward → room → bed → patient) | **nested / tree / drill-down** | one flat list |
| a **dense record** (a patient chart, a form) | **structured panel, grouped, scannable** | a long single column |
| a **comparison** (this patient vs reference ranges) | **aligned table with deviation highlighted** | sparse cards |

**A ward bed-map is a SPATIAL object** → it should read like the ward (rooms as regions, beds in position,
status as fill), not like a generic dashboard of cards. Identify the true shape first; let it drive the
layout. If your design ignores the data's natural shape, it will look generic no matter how clean it is.

### 1d. Reference distribution — design TOWARD excellence, not just AWAY from slop

Rules that only say "avoid decoration" produce austere-but-generic UIs, because there's nothing to aim at.
Anchor to **best-in-class dense operational UI** and reason about *why they work*, then apply the principle
(not the look) to this screen:

- **Linear / Height** — dense lists that stay calm: tight type scale, hairline separators, restraint, fast.
- **Stripe / Vercel dashboards** — data-dense with real hierarchy and craft, almost no decoration.
- **Modern EMR ops boards, OR boards, bed-management boards** — status-at-a-glance, color = state, spatial.
- **NOC / air-traffic / trading terminals** — maximum information density that a trained eye reads instantly;
  position, color, and weight do the work.

Name the 1–2 references you're drawing from in the README, and *what specifically* you're borrowing
(e.g. "Linear's hairline row rhythm", "OR-board status-by-fill"). This is the single biggest fix for
"it looks industrial/generic".

---

# PHASE 2 — GROUND every direction in what the system ACTUALLY has

A beautiful direction that needs data the system doesn't have is a fantasy, not a proposal. Before designing,
**audit the real capabilities** so each direction is either *buildable today* or *honestly flagged as
needing new data/features* — and turn the gaps into **suggestions**, not silent assumptions. (This is the
fix for "you proposed a floor-plan but the system has no bed coordinates".)

### 2a. What data does this screen actually have?

- From the **capture/DOM**: list the fields the live screen really shows (bed code, patient name, age, sex,
  diagnosis, LOS/ngày nằm, status, alerts/allergy/isolation, room, capacity…).
- From the **code** (use CodeGraph first, then bounded `rg`): inspect the real DTO / API response / FE
  component feeding this screen — what fields exist beyond what's displayed? Look at the generated DTO, the
  module adapter, the query hook. Cite `file:line`.
- **Do not invent fields.** If a direction needs a field, it must either exist or be listed as a gap.

### 2b. Capability check per metaphor (the part the owner asked for)

For each metaphor you're considering, classify it against real data:

| Verdict | Meaning | What to do |
|---|---|---|
| **FEASIBLE NOW** | every field/relation it needs already exists | propose it; build the mock with real-shaped data |
| **NEEDS NEW DATA** | needs a field/endpoint the system lacks (e.g. bed X/Y coordinates, room layout, real-time vitals) | you MAY still mock it to show the value, but **clearly label what new data/BE work it requires** and present it as a *suggestion*, not a ready direction |
| **INFEASIBLE / not worth it** | needs data that doesn't exist and isn't reasonable to add | drop it; say why |

Concrete example: a **true positional floor-plan** (each bed at its physical location) needs bed coordinates
/ a room layout map. If the BE has no such field → mark it **NEEDS NEW DATA**, and instead default to a
**room-grouped occupancy board** (position = order within room), which is feasible with the existing
room→bed→status data and still reads spatially. Don't silently ship a "floor-plan" that's really a card grid.

### 2c. Surface improvement suggestions (proactively)

While auditing, note where a small data/feature addition would unlock a much better UI, and put these in the
README as **"Gợi ý nâng cấp hệ thống"**: e.g. "add `bed.positionRow/positionCol` → enables a true ward
floor-plan", "expose `admittedAt` → enables LOS sorting", "add `isolationType` → enables an isolation lane".
The owner decides whether to invest; your job is to make the option visible, grounded in what's missing.

### 2d. Honor the harness during the audit

Read-only. CodeGraph + bounded `rg`/`fd` per `engine/rules/source-discovery.md`; never broad-scan and dump.
Do not edit code in preview. Indexes are per code repo / active worktree (the captured screen names its
worktree, e.g. `worktrees/<slug>/{be,fe}`).

---

## Design thesis — commit to this BEFORE writing any UI code

Write it down (one paragraph) and check every later decision against it:

> **Calm, dense-but-rhythmic, high-contrast, predictable, keyboard-first, color-has-meaning — and CRAFTED.**
> The screen is a precision instrument, well-made: an instrument panel, not a poster, and not a bland form.
> Nothing decorative competes with data, yet every detail is considered — spacing is optical, type has a real
> hierarchy, depth and color are used sparingly but deliberately. Color appears only when it *means*
> something. The abnormal value is the most visible thing on the screen. The layout matches the true shape of
> the data, so the eye learns it once and never re-learns it. The fastest path through the primary task is the
> keyboard.

If a choice does not serve **speed, certainty, or safety** for the primary task — cut it. If a choice is
merely *adequate* where it could be *crafted* — push it. Austere is not the goal; **noise-free excellence** is.

> **Do not be timid.** Every rule in this skill is a FLOOR, not a ceiling. The failure mode of a heavily-
> ruled design brief is safe, convergent, wireframe-y output — boxes everywhere, repeated labels, no real
> organization. That is *worse* than a flawed-but-considered design. Constraints keep you correct; **craft and
> a little invention** make it good. Aim for what a senior product designer would be proud to ship for a
> hospital: dense AND unmistakably clear AND quietly beautiful. Density is welcome — what's not welcome is
> density that isn't **organized** so the eye reads it instantly.

---

## Clinical UI principles

1. **Visual hierarchy = clinical priority.** The eye must land on what matters clinically first:
   abnormal/critical values, patient identity, the primary action/decision number. Make the *abnormal* loud
   (weight, semantic color, icon, a left status bar); keep the *normal* quiet. The number the user came to
   find (e.g. **free beds**) is the loudest thing on the screen. Chrome never outranks data.

2. **Density with rhythm — dense is correct, cramped is not, sparse is also wrong.** Clinicians want many
   fields/rows on screen. Achieve density through a strict **4 / 8 / 16 px spacing scale**, consistent
   row/tile height, and tight-but-even gutters — never by shrinking text below legibility. A huge void with
   two big cards is as wrong as an illegible cram. Pack the real data; remove the void.

3. **Match the data's shape (Phase 1b).** A spatial object gets a spatial layout; a timeline gets a timeline.
   Don't default to a card grid. This is what separates a designed screen from a generic one.

4. **Alignment & grid discipline.** Everything on a shared grid. Labels align, field edges align, **numeric
   columns right-aligned** (digits line up for fast scanning), units consistently placed. One ragged column
   destroys the scan.

5. **Spacing rhythm is the structure.** Same gap between peers, one larger consistent gap between sections,
   never one-off margins. Inconsistent spacing is the #1 reason a screen "feels bad but I don't know why".

6. **Color discipline — semantic only, but considered.** Color carries *meaning*, never decoration:
   red = danger/critical/abnormal-high/destructive · amber = warning/borderline · green = normal/confirmed
   (sparingly — most normal data should be neutral, not green) · blue/neutral = informational/interactive.
   Reserve saturated color for what must be noticed. But "semantic only" ≠ "ugly default grays": choose a
   **refined neutral palette** (a considered gray ramp, not raw `gray-200` borders everywhere), correct
   border weights, and intentional surface tints. Map status to `StatusBadge` + `STATUS_REGISTRY` (see
   frontend.md), never inline ad-hoc colored badges. Never use a color (e.g. purple) that carries no clinical
   meaning. Status must survive colorblindness (pair color with text/icon/position).

7. **Contrast is a safety feature.** Meet **WCAG AA** (≥4.5:1 body, ≥3:1 large/UI). No low-contrast
   pastel-on-white, no light-gray placeholder masquerading as a value. A misread value is a clinical incident.

8. **Craft floor — the polish that prevents "generic" (do not skip).** Beyond correctness, every screen must
   clear a craft bar:
   - **Type hierarchy is real:** a deliberate scale (e.g. label / value / heading), weight + size + color
     doing distinct jobs — not everything at one size. One neutral, highly legible sans stack; tabular/lining
     numerals for data.
   - **Optical spacing & alignment**, not just nominal — things that should line up actually do.
   - **Depth & separation used meaningfully:** hairline dividers or subtle elevation to group, not heavy
     boxes-in-boxes. Prefer separators/whitespace over nested borders.
   - **Micro-affordances:** clear hover/focus/active/selected states, sensible cursors, hit targets ≥ comfortable.
   - **Considered empty/loading states** (below) treated as design, not afterthought.
   - **Consistency:** one corner radius, one shadow scale, one icon set, one density.

9. **Affordance + mandatory states.** Interactive things look interactive; disabled things look disabled and
   explain why if they gate a clinical action. **Every data surface designs all four states:** loading
   (skeleton matching the real layout, not a layout-shifting spinner), **empty** (an instruction in the
   interface's voice — "No vitals recorded. Record the first reading.", not a blank void), **error** (what
   went wrong + how to recover — route through `handleApiError`, never a raw thrown string), and **populated**.

10. **Keyboard-first + accessibility (VERIFY, never assume).** Primary entry flow completable without a mouse:
    logical tab order, Enter to advance/submit, visible focus rings always, focus trap + restore in
    `Sheet`/`Dialog`. Board/grid/map views follow the **WAI-ARIA APG grid/treegrid pattern** (arrow-key
    navigation, roles) — confirm the live component's a11y rather than assuming. Critical fields reachable
    early in tab order, never buried. **A11y claims must be verified** (keyboard walk-through, axe/contrast
    check, `agent-browser` snapshot) — never asserted from reading code.

11. **Critical fields are never buried.** Patient banner (name, code, DOB, allergies/alerts), the abnormal
    value, the required field, the primary action stay high in priority. No mandatory clinical field behind an
    accordion, secondary tab, or "show more".

---

## Legible density — the positive techniques (how dense becomes CLEAR, not cluttered)

Hospitals accept high data density — but only if it's **organized** so the eye reads it instantly. Density
that isn't organized is the "wireframe with boxes everywhere" failure. These are the concrete moves that make
dense clinical data *tường minh* (lucid). Apply them; don't just avoid clutter — actively organize.

1. **Encode the MAJORITY state implicitly; spend explicit marks only on exceptions & actions.** This is the
   single biggest clarity lever. If most beds are occupied, do NOT stamp "Đang dùng" on every one — that's
   noise that buries the signal. The patient's name already says "occupied". Reserve a colored badge/dot/text
   for the things that are *different and actionable*: free beds, reserved-about-to-fill, cleaning,
   maintenance, isolation, locked. **The exception should be the only loud thing.**
2. **Figure/ground: let the answer pop and the rest recede.** The user came to find free beds → free beds are
   the brightest/highest-contrast element; occupied beds are calm and low-contrast. Don't give every item
   equal visual weight. A screen where everything is bordered and labelled equally has no hierarchy.
3. **Group with whitespace + alignment, not borders.** Prefer hairline separators and generous-but-rhythmic
   whitespace over a box around every element. Boxes-in-boxes (a bordered tile inside a bordered room inside a
   bordered section) reads as a wireframe. One level of grouping, done with space and a shared grid, reads as
   designed.
4. **One organizing principle per screen.** Pick the dominant structure (a color-coded occupancy field, or a
   sorted register, or a spatial board) and commit. Don't half-do three. The eye should learn the rule once.
5. **Reduce per-item chrome.** Each repeated unit (bed, row, tile) should carry the minimum that distinguishes
   it: code, the person (or "free"), and the exception marker. Move secondary detail to hover/click/inspector.
   Repetition × chrome = clutter; repetition × restraint = rhythm.
6. **Color does heavy lifting so text doesn't have to.** A consistent status-by-fill/accent lets the user read
   state by color across the whole screen without reading words — then text confirms for the colorblind.
7. **Tabular numerals + right-aligned numbers + consistent units** so dense numeric data scans as columns.
8. **Make the common action a one-glance affordance** (e.g. a free bed clearly reads "admit here") instead of
   a generic button repeated everywhere.

If a dense layout still feels cluttered after this, the problem is almost always (1) and (3): too many
explicit labels on the majority state, and too many borders. Strip them.

---

## Diagnosis — the 6-axis checklist + the craft & domain gates

For an existing screen that "feels bad but I don't know why", score, then prescribe.

**6 axes (score each 1–5; lowest two = the prescription):**

| # | Axis | 1 (broken) | 5 (excellent) |
|---|---|---|---|
| 1 | **Visual hierarchy** | flat — everything equal, or chrome louder than data | abnormal + identity + the decision-number pop instantly; normal data calm |
| 2 | **Density vs breathing** | cramped & illegible, OR wastefully sparse / endless scroll | dense yet legible; groups separated; nothing shrunk below readable |
| 3 | **Alignment / grid** | ragged labels/fields, mixed numeric alignment | shared grid; numbers right-aligned; units consistent |
| 4 | **Spacing rhythm** | one-off margins, uneven peer/section gaps | strict 4/8/16; same gap for peers, one larger for sections |
| 5 | **Color discipline** | decorative/off-palette color; everything colorful; red as accent | color only where it means something; refined neutrals; colorblind-safe |
| 6 | **Affordance / state** | missing empty/loading/error; unclear clickable/disabled | all 4 states designed; clear affordances; focus visible; keyboard works |

**Then two gates that the 6 axes don't catch (a screen can pass all 6 and still be generic/wrong):**

- **Domain-fit gate:** does the layout match the data's natural shape (Phase 1b)? A spatial object shown as a
  card grid FAILS this even with perfect spacing. Score pass/fail + the right metaphor.
- **Craft / generic smell test:** ask bluntly — *"does this look like every other Tailwind admin dashboard?"*
  If yes, it failed. Check the Craft floor (principle 8): real type hierarchy? refined neutrals (not default
  borders everywhere)? meaningful depth not boxes-in-boxes? considered states? If it's merely "clean and
  semantic" but anonymous, name what's missing and fix it.

Output: a score table + the metaphor verdict + the craft verdict + a concrete 3–5 item prescription
("BP column is left-aligned → right-align numerics with tabular figures and a unit suffix"), never vague
("improve hierarchy").

---

## Anti-patterns to AVOID

**Generic / craftless (the #1 failure mode for this skill):**
- **The default Tailwind admin dashboard** — flat cards, `gray-200` borders on everything, one type size,
  no real hierarchy, boxes-in-boxes. Clean but anonymous = failed.
- **Ignoring the data's natural shape** — a card grid for something that is spatial / temporal / a pipeline.
- **A plain register/list as the headline for spatial or status-at-a-glance data** — "it's just a list of
  beds". A table is sometimes a useful option, never the lead for data the eye should read by position/color.
- **Fantasy directions** — proposing a layout that needs data the system doesn't have (e.g. bed coordinates)
  without tagging it NEEDS-NEW-DATA and grounding it in Phase 2.
- **Ranking by your own taste** — calling a direction "the prettiest". Owner owns aesthetics.
- **Adequate where it could be crafted** — settling for "fine" spacing/type/states.

**Marketing slop (the `frontend-design` instincts that are wrong here):**
- Gradient hero cards / banner sections — clinical screens open with data or the patient banner, no hero.
- Decorative/ambient motion, scroll reveals, hover flourishes — motion only for *functional* feedback;
  respect `prefers-reduced-motion`.
- Low-contrast pastel palettes — a legibility and safety failure.
- 3-card-grid "feature" filler / dashboards of pretty empty cards — show real data densely instead.
- Characterful display typefaces / big expressive type — one neutral, highly legible functional stack.
- Off-palette decorative color (e.g. purple "in use" badge) / rainbow tag systems / color that doesn't encode
  status; ad-hoc inline status colors instead of `StatusBadge` + `STATUS_REGISTRY`.
- Burying critical fields behind tabs/accordions/"show more" for a clean look.
- "One real aesthetic risk" / a signature element / distinctiveness for its own sake.

> Reconcile the two lists: **zero decoration, zero distinctiveness — but maximal craft.** Predictability is
> the behavior; craft is the finish. Don't confuse "no boldness" with "no quality".

---

## Preview mode (mock-first — show the direction before any React change)

Goal: let the owner SEE improvement directions **before** porting into real components, with zero codebase
risk. Emit self-contained static mocks they open in a browser.

### Capturing the screen (when the owner gives a URL)

The owner will usually just give a **URL**. Capture it yourself — do not ask for a screenshot:

1. Drive **agent-browser** to navigate to the URL.
2. **Login gate:** the URL sits behind a login page. Log in with the harness smoke-test credential
   (customer code `bvtest3`, username `lynkhanh9822@gmail.com`, password in AGENTS.md / session memory —
   do NOT print the password). **If login fails for any reason (wrong page, captcha, credential rejected,
   redirect loop, timeout) → STOP immediately.** Report that login failed and do nothing else — no mock, no
   guessing the screen from memory. Never fabricate the current UI.
3. After login, navigate to the target URL, wait for the screen to finish loading, and **capture** it
   (screenshot → `capture.png` + DOM/accessibility snapshot). The capture is the source of truth for
   `before.html` and for scoring — do not score from imagination.
4. Recreate the captured state honestly as `before.html`.

If agent-browser is unavailable, ask the owner for a screenshot — but never invent the screen.

### Folder layout (one variant per DESIGN METAPHOR, not per effort level)

**Where:** `docs/ui-mocks/<screen-slug>/` (gitignored working space — never the workspace root, never the
real FE source). One folder per screen.

```
docs/ui-mocks/<screen-slug>/
  README.md        # Phase-1 research + 6-axis + craft/domain gates + the directions, what each changes
  capture.png      # the agent-browser screenshot of the live screen (baseline evidence)
  before.html      # current state recreated from the capture (the baseline)
  after-a.html     # direction A — a distinct METAPHOR/mental-model (e.g. refined list)
  after-b.html     # direction B — a different metaphor (e.g. dense board)
  after-c.html     # direction C — a different metaphor (e.g. true floor-plan map)
  styles.css       # shared, crafted base styles the after-* variants link
  data.js          # fake but realistic clinical data, shared by all variants
  shot-after-*.png # rendered screenshot of each variant (render them and look)
```

**Variant strategy — this changed and matters:** the variants must differ by **metaphor / mental-model**
(how the data is structured for the eye), NOT by effort level ("minimal vs full"). Effort-tiered variants all
converge on the same generic card grid — that's why earlier output felt same-y. Instead derive 2–3 genuinely
different *shapes* from Phase 1b (e.g. for a bed-map: refined room-list · dense status board · true
floor-plan map), and **push every variant to the full craft bar** — none is allowed to be the "lazy" one.
Label each with its metaphor in the README so the owner can say "go with the floor-plan".

- **A variant is a mutually-exclusive DESIGN APPROACH to the SAME complete screen — NOT a different feature.**
  The owner must be able to pick ONE variant and have a whole, finished screen for the same job. The earlier
  mistake was offering "a board" + "an assign tool" + "a work queue" as three variants — those are
  **complementary PARTS of one product**, so they belong INSIDE one variant, not as alternatives. **Test: if
  two "variants" would sensibly ship together, they are one variant.** Complementary pieces (an overview + an
  inspector + a queue panel) compose into a single design; they are not three choices.
- **Diverge by VISUAL TREATMENT / organizing principle of the one whole screen — within its genre.** Once 1a
  fixes the genre (e.g. a map), the variants are different ways to *draw that same map*: e.g. a schematic
  floor-plan map · a compact color-field/heatmap of the same ward · a map-with-side-inspector. Same scope,
  same genre, same job — different look. The owner is choosing the aesthetic/structure, not the feature set.
  Three takes that all read as "rooms containing bed cards" is still a failure; genuinely different *visual
  treatments of the same artifact* is the goal.
- **A crafted table/register IS allowed as a variant** — the earlier mistake was *ranking* it best, not its
  existence. A well-organized dense register (Linear-style, hairline rhythm, exception-only badges) can be
  excellent. What's banned is a *bare list with no organization* ("just a list of beds") presented as the
  headline for spatial/status data. If you include a register, make it genuinely crafted, and pair it with a
  more visual/spatial alternative.
- **Each variant carries a feasibility tag (Phase 2b):** FEASIBLE NOW / NEEDS NEW DATA (list it) / —. Don't
  present a direction whose data doesn't exist as if it's ready; show it as a grounded suggestion.
- **Apply the legible-density techniques to EVERY variant** — especially "encode the majority state
  implicitly" and "group with whitespace, not borders". A variant drowning in repeated labels and boxes has
  failed regardless of its metaphor.
- **Do NOT rank the directions by your own taste / call one "the prettiest".** Aesthetic preference is the
  OWNER's. Describe each direction's *trade-offs* (what it's best at, what it costs, what data it needs) —
  neutrally — and let the owner judge beauty. Different people will pick differently; that's expected.

**Rules for the mock:**
- **Standalone, no build.** Plain HTML + CSS + a little JS. Use **Tailwind via CDN**
  (`<script src="https://cdn.tailwindcss.com"></script>`) to APPROXIMATE the shadcn/Tailwind look — this is a
  *direction* preview, not a pixel-perfect render of the real React components. Say so in the README.
- **Hit the craft floor even in the mock** — real type hierarchy, refined neutrals, optical spacing, hover/
  focus/selected states, hairline separators over heavy boxes. A sloppy mock reads as a generic result and
  defeats the purpose. Put shared, crafted tokens in `styles.css`.
- **Each variant must clear its own domain-fit + craft + generic smell test** before you ship it. If a
  variant looks like a default admin panel, redo it — do not present it.
- **before vs every after must be comparable** — same `data.js`, same viewport; the difference is the design,
  not the content. Keep `before.html` honest to the captured screen.
- **Realistic fake data** (real-looking names, vitals, units, abnormal values, allergies) so
  hierarchy/color/density read truthfully. No real patient data.
- Show focus/selected states; if the screen is keyboard-first, reflect it. The mock imitates shadcn
  primitives (cards, table, badges, sheet) with plain markup — do not claim it uses the real
  `EnhancedDataGrid`/`StatusBadge`.
- **Render each variant and LOOK at it with fresh eyes** (capture `shot-after-*.png`), then run the
  **timid-wireframe critique** before handing off — ask honestly of each render:
  1. Is the majority state encoded implicitly, or is the same label repeated on every item? (repeated label = fix)
  2. Is there a border around everything (boxes-in-boxes), or grouping by whitespace + hairlines? (boxes = fix)
  3. Does the answer the user wants (e.g. free beds) POP, or is everything equal weight? (flat = fix)
  4. Does it look like a considered design a senior would ship, or a constrained wireframe? (wireframe = fix)
  5. **Does it look like its GENRE (1a)?** If the screen is a "sơ đồ", does this read as a MAP — or did it
     drift into a dashboard/board/table/queue? (genre mismatch = redo)
  6. **Overview vs list:** on an overview/map, is understanding carried by spatial pattern, or by listing
     every item's full text? (everything listed = too much; aggregate, detail-on-focus)
  7. Are the 2–3 variants different *visual treatments of the SAME whole screen* (owner picks one), or were
     they sliced into complementary sub-tools that really belong together? (complementary = merge into one)
  If any answer is the failure side, **revise the mock before handing off** — do not ship a wireframe-y,
  genre-mismatched, or decomposed set just because it obeys the rules. Rules are the floor; this critique is
  the bar.

**README.md contents:** the Phase-1 findings (user + decisions + domain shape + references) · the **Phase-2
capability audit** (what data the screen/code actually has, cited `file:line`) · the 6-axis score table
(before) · the domain-fit + craft verdicts · one labelled paragraph per `after-*` direction (its metaphor +
**feasibility tag** + which axes/gates it fixes + what's crafted, trade-offs stated neutrally) · a **"Gợi ý
nâng cấp hệ thống"** section listing any data/feature additions that would unlock a better UI · "How to view:
open each `after-*.html`; compare with `before.html`" · the note that this is an approximate direction preview
(not final React output) and APPLY happens only after approval.

**Hand-off:** end by telling the owner the paths + a one-line *trade-off* summary per direction (not a beauty
ranking), surface the upgrade suggestions, and ask which direction to proceed to APPLY. Do not auto-apply, do
not pick the direction for them, and do not declare one "the prettiest" — taste is theirs.

---

## How to apply

**Step 0 — UNDERSTAND.** Run Phase 1 — **genre FIRST** (1a: what artifact IS this? a sơ đồ = a map, honor
it), then user & decisions · domain metaphor · references. Write findings down. Do not skip to pixels, and do
not turn a map into a dashboard.

**Step 0.5 — GROUND.** Run Phase 2 (audit real data/capabilities via CodeGraph + bounded `rg`; tag each
candidate metaphor FEASIBLE/NEEDS-NEW-DATA; collect upgrade suggestions). No fantasy directions.

**Step 1 — capture & diagnose.** Capture the live screen (or use the owner's screenshot). Score the 6 axes,
apply the domain-fit + craft gates, identify the lowest axes and the right metaphor.

**Step 2 — produce 2–3 directions by metaphor.** Each is a different mental-model shape from Phase 1b, each
pushed to the full craft bar, each carrying its Phase-2 feasibility tag. Lead with the most visual/at-a-glance
shape (a plain register is at most one option, never the headline, for spatial/status data). Compare in prose
+ a quick ASCII wireframe; **critique each against the anti-pattern + generic gates before coding** — if any
reads like marketing polish or a default admin panel, fix it or drop it. **Do not rank by beauty** — state
trade-offs; the owner picks.

**Step 3 — (PREVIEW) emit the mocks** per Preview mode, render and self-critique them, hand off for the owner
to pick a direction.

**Step 4 — (APPLY, only after approval) implement, consistent with `engine/rules/frontend.md`.** Use shadcn
`src/components/ui/*` and the warehouse GOOD-parts patterns; lists/boards use `EnhancedDataGrid` where it
fits; forms use `Sheet` + RHF + `zodResolver`; status via `StatusBadge`/`STATUS_REGISTRY`; data via the
module adapter + `useMasterData` (id-only, no name-compare); errors via `handleApiError`. **Do not invent
component props**, do not hand-edit generated DTO/client/`Constants.ts`, and make all real code changes in a
worktree (never `myhospital-fe/` directly). If a needed DTO/constant/permission is missing, stop and report a
contract blocker.

**Step 5 — verify the quality floor (don't assert it).** Keyboard-complete the primary flow; check focus
order + visible focus + focus trap/restore in overlays; check WCAG AA contrast on values and status; confirm
empty/loading/error states render; confirm color isn't the only status signal. Verify in the browser /
`agent-browser` — never claim a11y from code-reading alone.

---

## Relationship to `frontend-design`

| Concept | `frontend-design` (marketing) | `clinical-ui-design` (this) |
|---|---|---|
| Goal | distinctive, memorable identity | calm, predictable, fast, safe — **and crafted** |
| KEPT: commit to a direction first | aesthetic thesis | **clinical thesis** + the data's natural metaphor |
| KEPT: reference distribution | brand/aesthetic exemplars | **best-in-class dense operational UI** (Linear, EMR/OR boards…) |
| KEPT: two-pass plan → critique | yes | yes — against anti-patterns + the generic smell test |
| KEPT: quality floor (a11y, focus, reduced-motion) | yes | yes — **mandatory + verified** |
| KEPT: **craft / polish** | yes | **yes — craft is non-negotiable; only decoration is removed** |
| KEPT: intentional copy / states | yes | yes — empty/error are clinical instructions |
| INVERTED: decoration & aesthetic risk | "take one real risk" | **zero** — noise-free; predictability is the behavior |
| INVERTED: typography | characterful display faces | one neutral legible stack, but a *real* hierarchy |
| INVERTED: motion | deliberate, atmospheric | functional-only; mostly none |
| INVERTED: hero / signature | a memorable signature element | data/patient-banner first; no hero |
| INVERTED: color | gradients & expressive accents | semantic-only, but a *refined* neutral palette |
| INVERTED: density | airy, expressive whitespace | dense-but-rhythmic instrument panel |

Same rigor, same craft, opposite *direction*: zero decoration, maximal craft, layout that matches the work.
Use **this** for any HIS screen, form, data table, board, or map; use stock `frontend-design` only for
marketing/brand surfaces.
