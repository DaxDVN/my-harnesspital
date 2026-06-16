// mh-review — power-mode audit engine (OPTIONAL · needs the Workflow tool / explicit opt-in).
// Deterministic version of SKILL.md Steps 2–5: partitioned fan-out → adversarial verify → dedup
// → bounded loop-until-dry completeness. Returns structured findings; the CALLER writes the
// findings .md per engine/review/findings-schema.md (workflows can't write files).
//
// Invoke with args = { module: "<name>", base: "<branch/sha>", scope: ["file", ...] }.
// If scope is omitted a scout agent computes it (git diff against base).

export const meta = {
  name: 'mh-review-audit',
  description: 'Partitioned exhaustive code audit: one reviewer per dimension (D1–D10), adversarial verify of BLOCK/HIGH, bounded loop-until-dry on coverage. Returns findings + ledger for the caller to write the audit .md.',
  phases: [
    { title: 'Scope' },
    { title: 'Audit' },
    { title: 'Verify' },
    { title: 'Completeness' },
  ],
}

const COVER = { type: 'object', required: ['file', 'status'], properties: {
  file: { type: 'string' },
  status: { type: 'string', enum: ['FINDING', 'CLEAN', 'N/A', 'UNATTESTED'] },
} }
const FINDING = { type: 'object', required: ['severity', 'location', 'title', 'evidence'], properties: {
  severity: { type: 'string', enum: ['BLOCK', 'HIGH', 'MED', 'LOW', 'NIT'] },
  location: { type: 'string' }, title: { type: 'string' }, evidence: { type: 'string' },
  root_cause: { type: 'string' }, fix: { type: 'string' },
} }
const REVIEW_SCHEMA = { type: 'object', required: ['dimension', 'coverage', 'findings'], properties: {
  dimension: { type: 'string' },
  coverage: { type: 'array', items: COVER },
  findings: { type: 'array', items: FINDING },
  notes: { type: 'string' },
} }
const CRITIC_SCHEMA = { type: 'object', required: ['refuted'], properties: {
  refuted: { type: 'boolean' }, reason: { type: 'string' },
} }
const SCOPE_SCHEMA = { type: 'object', required: ['files'], properties: {
  module: { type: 'string' }, files: { type: 'array', items: { type: 'string' } },
} }

// 10 dimensions — see engine/review/checklist.md. Reviewer self-marks N/A when not applicable.
const DIMENSIONS = [
  { key: 'D1', name: 'business-logic', tier: 'opus' },
  { key: 'D2', name: 'be-conventions', tier: 'sonnet' },
  { key: 'D3', name: 'fe-conventions', tier: 'sonnet' },
  { key: 'D4', name: 'correctness', tier: 'sonnet' },
  { key: 'D5', name: 'data-access', tier: 'sonnet' },
  { key: 'D6', name: 'security-pii', tier: 'sonnet' },
  { key: 'D7', name: 'contract-dto', tier: 'haiku' },
  { key: 'D8', name: 'tests-traceability', tier: 'sonnet' },
  { key: 'D9', name: 'migration-schema', tier: 'sonnet' },
  { key: 'D10', name: 'component-reuse-state', tier: 'haiku' },
]

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

// --- Steps 2–3: per-dimension review, then verify BLOCK/HIGH as soon as that dimension lands (pipeline, no barrier) ---
const reviewed = await pipeline(
  DIMENSIONS,
  (d) => agent(
    `You are the ${d.key} (${d.name}) reviewer. Read your dimension's entry in engine/review/checklist.md and review ONLY these files through that single lens:
${fileList}
Module spec dir: specs/${module}/. Enumerate before ranking. Attest coverage for EVERY file (FINDING/CLEAN/N/A). Cite live evidence for BLOCK/HIGH (rule-hit/spec/exemplar); doc-only → cap at MED. Output per engine/review/findings-schema.md.`,
    { label: `audit:${d.key}`, phase: 'Audit', agentType: 'mh-reviewer', model: d.tier, schema: REVIEW_SCHEMA },
  ),
  (review, d) => {
    if (!review || !(review.findings || []).length) return review
    const hi = review.findings.filter((f) => f.severity === 'BLOCK' || f.severity === 'HIGH')
    if (!hi.length) return review
    return parallel(hi.map((f) => () =>
      agent(
        `Adversarially REFUTE this ${d.key} finding using the live code. Default refuted=true if evidence is weak, doc-only, or you cannot confirm it. Be a skeptic.
Title: ${f.title}
Location: ${f.location}
Evidence: ${f.evidence}
Root cause: ${f.root_cause || '(none given)'}`,
        { label: `verify:${f.location}`, phase: 'Verify', model: 'sonnet', schema: CRITIC_SCHEMA },
      ).then((v) => ({ k: fkey(f), refuted: !!(v && v.refuted) })),
    )).then((verds) => {
      const refute = new Map(verds.filter(Boolean).map((v) => [v.k, v.refuted]))
      review.findings = review.findings.map((f) =>
        refute.get(fkey(f)) ? { ...f, status: 'REJECTED' } : f)
      return review
    })
  },
)

// --- Step 4: dedup (pipeline already joined all dimensions) ---
const all = reviewed.filter(Boolean)
const seen = new Set()
const findings = []
for (const r of all) for (const f of (r.findings || [])) {
  if (f.status === 'REJECTED') continue
  if (seen.has(fkey(f))) continue
  seen.add(fkey(f)); findings.push({ ...f, status: f.status || 'OPEN', dimension: r.dimension })
}
const ledger = all.map((r) => ({ dimension: r.dimension, coverage: r.coverage || [] }))

// --- Step 5: bounded loop-until-dry on UNATTESTED cells (max 2 mini-waves; never re-audit whole scope) ---
phase('Completeness')
for (let k = 0; k < 2; k++) {
  const gaps = []
  for (const r of ledger) for (const c of (r.coverage || []))
    if (c.status === 'UNATTESTED') gaps.push({ dim: r.dimension, file: c.file })
  if (!gaps.length) break
  log(`Completeness wave ${k + 1}: ${gaps.length} unattested cells`)
  const fills = await parallel(gaps.slice(0, 16).map((c) => () =>
    agent(
      `Re-review ONLY file "${c.file}" for dimension ${c.dim}. Attest coverage + report any findings. Same schema/rules.`,
      { label: `fill:${c.dim}:${c.file}`, phase: 'Completeness', agentType: 'mh-reviewer', model: 'sonnet', schema: REVIEW_SCHEMA },
    )))
  for (const r of fills.filter(Boolean)) {
    for (const f of (r.findings || [])) {
      if (f.status === 'REJECTED' || seen.has(fkey(f))) continue
      seen.add(fkey(f)); findings.push({ ...f, status: 'OPEN', dimension: r.dimension })
    }
    // mark filled cells attested
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
  note: 'Caller: write docs/audit/<module>-review-v<round>-<date>.md per findings-schema.md (stamp today\'s date) and report the summary.',
}
