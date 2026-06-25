// mh-review — maximum-recall audit engine (OPTIONAL · needs the Workflow tool / explicit opt-in).
// Deterministic version of SKILL.md Steps 2–6: multi-pass partitioned fan-out → self-adversarial
// pre-filter → adversarial verify → dedup → bounded loop-until-dry completeness.
// Returns structured findings; the CALLER writes the findings .md per
// engine/workflows/deep-review/findings-schema.md (workflows can't write files).
//
// Invoke with args = { module: "<name>", base: "<branch/sha>", scope: ["file", ...] }.
// If scope is omitted a scout agent computes it (git diff against base).
//
// Quality-first design: multi-pass convergence, exemplar anchors, self-adversarial filtering,
// deterministic pre-scan injection, confidence scoring. Token cost is secondary.

export const meta = {
  name: 'mh-review-audit',
  description: 'Maximum-recall partitioned audit: multi-pass per dimension (P1–P5), exemplar anchors, self-adversarial pre-filter, adversarial verify of surviving BLOCK/HIGH, dedup, bounded loop-until-dry completeness. Returns findings + ledger for the caller to write the audit .md.',
  phases: [
    { title: 'Scope' },
    { title: 'Audit' },
    { title: 'Self-Adversarial' },
    { title: 'Verify' },
    { title: 'Completeness' },
  ],
}

// --- Schemas ---
const SCOPE_SCHEMA = { type: 'object', required: ['files'], properties: {
  module: { type: 'string' },
  files: { type: 'array', items: { type: 'string' } },
} }
const COVER = { type: 'object', required: ['file', 'status'], properties: {
  file: { type: 'string' },
  status: { type: 'string', enum: ['FINDING', 'CLEAN', 'N/A', 'UNATTESTED'] },
} }
const FINDING = { type: 'object', required: ['severity', 'location', 'title', 'evidence'], properties: {
  severity: { type: 'string', enum: ['BLOCK', 'HIGH', 'MED', 'LOW', 'NIT'] },
  location: { type: 'string' }, title: { type: 'string' }, evidence: { type: 'string' },
  root_cause: { type: 'string' }, fix: { type: 'string' },
  bug_class: { type: 'string' }, scanner_candidate: { type: 'string', enum: ['yes', 'no'] },
} }
const REVIEW_SCHEMA = { type: 'object', required: ['dimension', 'coverage', 'findings'], properties: {
  dimension: { type: 'string' },
  coverage: { type: 'array', items: COVER },
  findings: { type: 'array', items: FINDING },
  notes: { type: 'string' },
  missed_patterns: { type: 'array', items: { type: 'string' } },
} }
const SELF_ADV_SCHEMA = { type: 'object', required: ['verdict', 'reasoning'], properties: {
  verdict: { type: 'string', enum: ['KEEP', 'DOWNGRADE', 'DROP'] },
  confidence: { type: 'string', enum: ['LOW', 'MEDIUM', 'HIGH'] },
  reasoning: { type: 'string' },
} }
const CRITIC_SCHEMA = { type: 'object', required: ['refuted'], properties: {
  refuted: { type: 'boolean' }, reason: { type: 'string' },
} }

// 7 dimensions — see engine/workflows/deep-review/checklist.md
const DIMENSIONS = [
  { key: 'D1', name: 'business-logic', tier: 'opus' },
  { key: 'D2', name: 'be-conventions', tier: 'sonnet' },
  { key: 'D3', name: 'fe-conventions', tier: 'sonnet' },
  { key: 'D4', name: 'correctness', tier: 'sonnet' },
  { key: 'D5', name: 'data-access', tier: 'sonnet' },
  { key: 'D6', name: 'security-pii', tier: 'sonnet' },
  { key: 'D7', name: 'reuse', tier: 'sonnet' },
]

// Multi-pass configuration per dimension
const PASSES = {
  D1: ['P1', 'P2', 'P3', 'P4'],
  D2: ['P1', 'P2', 'P3'],
  D3: ['P1', 'P2', 'P3', 'P5'],
  D4: ['P1', 'P2', 'P3'],
  D5: ['P1', 'P2', 'P3'],
  D6: ['P1', 'P2', 'P3'],
  D7: ['P1', 'P2', 'P3', 'P5'],
}
const PASS_DESC = {
  P1: 'Direct rule/convention violations — read the dimension checklist and check every rule against the code.',
  P2: 'Regression/caller/cross-file breakage — trace callers, check if changes break downstream, verify invariants hold across file boundaries.',
  P3: 'Reuse/edge-case/null/state gaps — check null safety, empty arrays, boundary values, missing error handling, state machine gaps, components that should be reused but aren\'t.',
  P4: 'Business/spec contradiction — compare code behavior against specs/Tài liệu Nội trú.md. Any code behavior not matching the BA document is a finding.',
  P5: 'Reuse matrix — for every component/service/helper, search CodeGraph for existing implementations that should be reused. For FE: visible elements, widgets, patterns. For BE: service methods, helpers, base class patterns. Flag any hand-rolled implementation that duplicates existing code.',
}

const sev = (s) => ({ BLOCK: 0, HIGH: 1, MED: 2, LOW: 3, NIT: 4 }[s] ?? 9)
const fkey = (f) => `${f.location}|${f.severity}|${(f.title || '').slice(0, 40)}`

// --- Step 1: scope freeze ---
phase('Scope')
const base = (args && args.base) || 'main'
let module = (args && args.module) || 'unknown'
let scope = (args && args.scope) || []
if (!scope.length) {
  const s = await agent(
    `Scope-freeze for mh-review (read-only). Base: ${base}. Module: ${module}.
Run \`git -C <active repo/worktree> diff --name-only ${base}\`. If empty, list source files under specs/${module}/ or the module dir.
Return the frozen file list (and module name if you can infer it).`,
    { label: 'scope-freeze', phase: 'Scope', schema: SCOPE_SCHEMA },
  )
  scope = (s && s.files) || []
  if (s && s.module) module = s.module
}
log(`Scope frozen: ${scope.length} files · module=${module}`)
if (!scope.length) return { module, findings: [], ledger: [], note: 'Empty scope — nothing to audit.' }

const fileList = scope.map((f) => ` - ${f}`).join('\n')

// --- Step 2: multi-pass per-dimension audit (maximum recall) ---
phase('Audit')
const dimensionResults = await parallel(
  DIMENSIONS.map((d) => async () => {
    const passes = PASSES[d.key] || ['P1', 'P2', 'P3']
    log(`Starting ${d.key} (${d.name}) with ${passes.length} passes`)

    const passResults = await parallel(
      passes.map((p) => () => agent(
        `You are the ${d.key} (${d.name}) reviewer — PASS ${p}: ${PASS_DESC[p]}

READ FIRST: engine/workflows/deep-review/checklist.md — your dimension's entry (Sources, Check list, Known bug-classes).

SCOPE (review every file):
${fileList}

EXEMPLAR SEARCH: Before reviewing, search the codebase for 1-2 existing CORRECT patterns that match your dimension (e.g., a well-implemented service for D2, a proper React Query adapter for D3). Use these as anchors — "does this code match the exemplar pattern?"

${p === 'P4' ? 'FOCUS: Compare code against specs/Tài liệu Nội trú.md (.docx). Any code behavior not matching the BA document is a finding. This is the ONLY spec source — do NOT use specs/<module>/ as business rule source.' : ''}
${p === 'P5' ? 'FOCUS: For every component/service/helper in scope, search CodeGraph for existing reusable implementations. Build a reuse matrix. For FE: visible elements, widgets, shared components. For BE: service methods, helpers, base class patterns. Flag any hand-rolled code that duplicates existing functionality.' : ''}

INSTRUCTIONS:
1. ENUMERATE every in-scope file your dimension applies to. Review EACH file.
2. For each file, output FINDING (with full evidence) or CLEAN.
3. For BLOCK/HIGH: provide CITE-LIVE evidence (rule-hit, exemplar:file:line, ba-source:page/section). Doc-only → cap at MED.
4. Known bug-classes from checklist: check if ANY match the code. Flag as candidate with bug_class key.
5. After findings, list MISSED_PATTERNS: patterns you checked but didn't find (proves you looked).

${d.key === 'D1' ? 'CRITICAL: D1 findings MUST cite specific page/section in specs/Tài liệu Nội trú.md. Generic "doesn\'t match spec" without citation → cap at MED.' : ''}
${d.key === 'D3' || d.key === 'D7' ? 'REUSE ATTESTATION: For every component/service/helper/widget in scope, include: element → semantic role → existing exemplar (file:line) → actual impl (file:line) → CLEAN/FINDING.' : ''}

Output per engine/workflows/deep-review/findings-schema.md (minus status/review_status — parent manages those).`,
        {
          label: `audit:${d.key}:${p}`,
          phase: 'Audit',
          agentType: 'mh-reviewer',
          model: d.tier,
          schema: REVIEW_SCHEMA,
        },
      )),
    )

    // Union findings across passes (merge, dedup by fkey)
    const seenKeys = new Set()
    const mergedFindings = []
    const mergedCoverage = []
    const allMissed = []
    const covRank = { FINDING: 0, CLEAN: 1, 'N/A': 2, UNATTESTED: 3 }

    passResults.forEach((result, idx) => {
      if (!result) return
      const passId = passes[idx]
      for (const f of (result.findings || [])) {
        const k = fkey(f)
        if (!seenKeys.has(k)) {
          seenKeys.add(k)
          mergedFindings.push({ ...f, pass: passId })
        }
      }
      if (result.coverage) {
        for (const c of result.coverage) {
          const existing = mergedCoverage.find((x) => x.file === c.file)
          if (!existing) mergedCoverage.push({ ...c })
          else if ((covRank[c.status] ?? 3) < (covRank[existing.status] ?? 3)) existing.status = c.status
        }
      }
      if (result.missed_patterns) allMissed.push(...result.missed_patterns)
    })

    log(`${d.key}: ${mergedFindings.length} findings from ${passes.length} passes`)
    return {
      dimension: `${d.key} ${d.name}`,
      coverage: mergedCoverage,
      findings: mergedFindings,
      notes: passResults.filter(Boolean).map((r) => r.notes).filter(Boolean).join('; '),
      missed_patterns: allMissed,
    }
  }),
)

// --- Step 3: self-adversarial pre-filter (reduce false positives before expensive verify) ---
phase('Self-Adversarial')
const allFindings = []
for (const r of dimensionResults.filter(Boolean)) {
  for (const f of (r.findings || [])) {
    allFindings.push({ ...f, dimension: r.dimension })
  }
}

const highFindings = allFindings.filter((f) => f.severity === 'BLOCK' || f.severity === 'HIGH')
if (highFindings.length) {
  log(`Self-adversarial: challenging ${highFindings.length} BLOCK/HIGH findings`)
  const selfAdvResults = await parallel(
    highFindings.map((f) => () => agent(
      `You are a SKEPTIC reviewing a code audit finding. Your job is to CHALLENGE it.

FINDING:
- Title: ${f.title}
- Severity: ${f.severity}
- Location: ${f.location}
- Evidence: ${f.evidence}
- Root cause: ${f.root_cause || '(none)'}

YOUR TASK:
1. Read the ACTUAL code at the cited location
2. Verify the evidence is REAL and ACCURATE (not hallucinated or misinterpreted)
3. Check if the cited rule/convention actually applies to this code pattern
4. Search for counter-evidence: is there a reason this code is intentionally written this way?
5. Is the severity justified? Would MED be more appropriate?

DECISION:
- KEEP: evidence is strong and verifiable in live code. Assign confidence HIGH/MEDIUM/LOW.
- DOWNGRADE: real issue but severity too high (e.g., BLOCK→MED). State new severity.
- DROP: false positive — evidence is weak, misinterpreted, or code is actually correct.

Default to KEEP if you're unsure — downstream verify will catch remaining false positives.
But if evidence is ONLY from docs (not live code), default to DOWNGRADE to MED.`,
      {
        label: `self-adv:${f.location}`,
        phase: 'Self-Adversarial',
        model: 'sonnet',
        schema: SELF_ADV_SCHEMA,
      },
    )),
  )

  // Apply self-adversarial results
  for (let i = 0; i < highFindings.length; i++) {
    const result = selfAdvResults[i]
    if (!result) continue
    if (result.verdict === 'DROP') {
      highFindings[i].status = 'REJECTED'
      highFindings[i].rejection_reason = `Self-adv: ${result.reasoning}`
    } else if (result.verdict === 'DOWNGRADE') {
      highFindings[i].severity = 'MED'
      highFindings[i].confidence = result.confidence || 'MEDIUM'
    } else {
      highFindings[i].confidence = result.confidence || 'MEDIUM'
    }
  }
  const dropped = selfAdvResults.filter((r) => r && r.verdict === 'DROP').length
  log(`Self-adversarial: dropped ${dropped} false positives from ${highFindings.length} BLOCK/HIGH`)
}

// --- Step 4: adversarial verify (stronger model on surviving BLOCK/HIGH) ---
phase('Verify')
const survivors = allFindings.filter((f) => (f.severity === 'BLOCK' || f.severity === 'HIGH') && f.status !== 'REJECTED')
if (survivors.length) {
  const BATCH = 8
  for (let i = 0; i < survivors.length; i += BATCH) {
    const batch = survivors.slice(i, i + BATCH)
    const verdicts = await parallel(batch.map((f) => () =>
      agent(
        `Adversarially REFUTE this ${f.dimension} finding using the live code AND specs/Tài liệu Nội trú.md. Default refuted=true if evidence is weak, doc-only, or you cannot confirm it. Be a skeptic.
Title: ${f.title}
Location: ${f.location}
Evidence: ${f.evidence}
Root cause: ${f.root_cause || '(none given)'}`,
        { label: `verify:${f.location}`, phase: 'Verify', model: 'sonnet', schema: CRITIC_SCHEMA },
      ).then((v) => ({ k: fkey(f), refuted: !!(v && v.refuted) })),
    ))
    const refute = new Map(verdicts.filter(Boolean).map((v) => [v.k, v.refuted]))
    for (const f of batch) {
      if (refute.get(fkey(f))) f.status = 'REJECTED'
      else if (f.confidence !== 'HIGH') f.confidence = 'HIGH'
    }
  }
}

// --- Step 5: dedup ---
const seen = new Set()
const findings = []
for (const f of allFindings) {
  if (f.status === 'REJECTED') continue
  if (seen.has(fkey(f))) continue
  seen.add(fkey(f)); findings.push({ ...f, status: f.status || 'OPEN' })
}
const ledger = dimensionResults.filter(Boolean).map((r) => ({ dimension: r.dimension, coverage: r.coverage || [] }))

// --- Step 6: bounded loop-until-dry on UNATTESTED cells ---
phase('Completeness')
for (let k = 0; k < 2; k++) {
  const gaps = []
  for (const r of ledger) for (const c of (r.coverage || []))
    if (c.status === 'UNATTESTED') gaps.push({ dim: r.dimension, file: c.file })
  if (!gaps.length) break
  log(`Completeness wave ${k + 1}: ${gaps.length} unattested cells`)
  const fills = await parallel(gaps.slice(0, 16).map((c) => () =>
    agent(
      `Re-review ONLY file "${c.file}" for dimension ${c.dim}. Read the checklist entry first. Attest coverage + report any findings. Same schema/rules. Include exemplar search.`,
      { label: `fill:${c.dim}:${c.file}`, phase: 'Completeness', agentType: 'mh-reviewer', model: 'sonnet', schema: REVIEW_SCHEMA },
    )))
  for (const r of fills.filter(Boolean)) {
    for (const f of (r.findings || [])) {
      if (f.status === 'REJECTED' || seen.has(fkey(f))) continue
      seen.add(fkey(f)); findings.push({ ...f, status: 'OPEN', dimension: r.dimension })
    }
    for (const c of (r.coverage || [])) {
      const row = ledger.find((x) => x.dimension === r.dimension)
      if (row) { const cell = row.coverage.find((x) => x.file === c.file); if (cell) cell.status = c.status }
    }
  }
}

findings.sort((a, b) => sev(a.severity) - sev(b.severity))
const counts = findings.reduce((m, f) => ((m[f.severity] = (m[f.severity] || 0) + 1), m), {})
log(`Done: ${findings.length} findings — ${JSON.stringify(counts)}`)

return {
  module,
  scope_files: scope.length,
  counts,
  verdict: (counts.BLOCK || counts.HIGH) ? 'CHƯA ĐÓNG' : 'ĐÓNG',
  findings,
  ledger,
  note: 'Caller: write docs/audit/<YYYY-MM-DD>/<base>.round-<N>.md per findings-schema.md and report the summary.',
}
