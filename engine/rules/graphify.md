# Graphify Policy

This file is lazy-loaded for docs/specs design-intent graph questions or graphify maintenance.

## Scope

Graphify covers `docs/` and `specs/` design intent only. It is never source-code discovery.

For source code, use CodeGraph first and `engine/rules/source-discovery.md`.

## Trust Model

The graph may be absent, stale, cross-machine, or present but untrusted. Run:

```bash
python scripts/harness_doctor.py
```

If doctor reports graphify trust warnings, prefer source docs/specs and treat graph output as advisory.

## Usage

Use graphify only when it is faster than reading source docs:

```bash
graphify query "<question>"
graphify explain "<node>"
graphify path "<A>" "<B>"
graphify affected "<node>"
```

Treat inferred edges as unverified.

## Rebuild

After material docs/specs changes, the graph needs a Linux rebuild when fresh graph answers are needed. The freshness hook flags staleness; it does not rebuild.
