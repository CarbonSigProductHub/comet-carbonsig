# Term Intelligence

A reproducible pipeline that enriches every COMET term with a **plain-English
description** and proposes **cross-namespace term matches** (de-duplication) with
a **confidence interval**, human-gated before any merge.

## Why

COMET now spans 15 namespaces (core + 8 extensions + the incorporated CAD Trust
dictionary). 37% of native terms lacked a definition, and the same concept
(chain-of-custody, verification opinion, production route, retirement date, data
quality share…) is defined independently across several extensions. This layer
makes every term legible to non-specialists and surfaces the duplication so it
can be reconciled.

## Pipeline

| Stage | Script | Output |
| --- | --- | --- |
| 1. Extract | `extract_terms.py` | `data/terms.json` + `data/batches/batch_*.json` |
| 2. Candidates | `gen_candidates.py` | `data/candidates/*` — recall-oriented pairs (concept-token overlap + acronym expansion; at least one COMET-native side; trivial audit fields excluded) |
| 3a. Describe | subagents → `data/descriptions/desc_*.json` | one plain-English gloss per term |
| 3b. Adjudicate | subagents → `data/matches/match_*.json` | SKOS relation + confidence + interval + canonical + rationale per candidate |
| 4. Assemble | `assemble.py` | `descriptions.json`, `term-matches.json`, `term-matches.ttl` |
| 5. Enrich | `enrich_ontology_data.py` | injects `plainDescription`, per-term `similarTerms`, and a `termMatches` block into `docs/ontology-data.json(.js)` |

The LLM stages (3a/3b) are run by subagents that read a batch file and write
their output to disk. To re-run reproducibly with an API instead, point a script
at the same batch files with the prompts in this README's git history.

## The match model (human-gated)

Matches are **proposals, not axioms.** `term-matches.ttl` records each as a
`comet-match:MatchProposal` with `status "proposed"` — a reviewer promotes a
proposal to an asserted `skos:exactMatch` (and optional deprecation of the
non-canonical term) only after sign-off. Relations: `exactMatch`, `closeMatch`,
`broadMatch`, `narrowMatch`, `relatedMatch`. Each carries `confidence` plus a
`confidenceLow`/`confidenceHigh` interval reflecting the adjudicator's
uncertainty, and (for exact/close) a `canonicalTerm` — the term to keep, chosen
by namespace seniority (core > published layers > extensions > CAD Trust).

## Run

```bash
python tools/term_intelligence/extract_terms.py
python tools/term_intelligence/gen_candidates.py
# 3a/3b: dispatch description + adjudication subagents over the batch files
python tools/term_intelligence/assemble.py
python tools/term_intelligence/enrich_ontology_data.py   # after build-ontology-map.py
```

## Current run

1113/1113 terms described. 72 match proposals (3 exact · 23 close · 12 narrow ·
4 broad · 30 related); 22 exact/close carry a canonical pick — the actionable
de-duplication backlog.
