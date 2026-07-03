#!/usr/bin/env python3
"""Stage 3 — assemble subagent outputs into the two canonical artifacts.

Inputs:  data/descriptions/desc_*.json   ({curie: plainDescription})
         data/matches/match_*.json       ([{a,b,relation,confidence,...}])
         data/terms.json                 (coverage check)
Outputs: descriptions.json               (curie -> plain-English, all terms)
         term-matches.json               (proposed matches, human-gated)
         term-matches.ttl                (same as reviewable RDF proposals)

Matches are PROPOSALS, not asserted axioms: they are recorded as
comet-match:MatchProposal records (status "proposed") so a human can review
before any skos:exactMatch is committed to the graph.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
TERMS = DATA / "terms.json"
DESC_OUT = HERE / "descriptions.json"
MATCH_JSON = HERE / "term-matches.json"
MATCH_TTL = HERE / "term-matches.ttl"

NS_BASES = {
    "comet": "https://comet.carbon/v1/core#",
    "comet-ef": "https://comet.carbon/v1/emfactor#",
    "comet-sc": "https://comet.carbon/v1/supplychain#",
    "comet-pcf": "https://comet.carbon/v1/pcf#",
    "comet-eac": "https://comet.carbon/v1/eac#",
    "comet-ver": "https://comet.carbon/v1/ver#",
    "comet-mkt": "https://comet.carbon/v1/market#",
    "comet-rs": "https://comet.carbon/ext/responsiblesteel#",
    "comet-cn": "https://comet.carbon/ext/iso14068#",
    "comet-pj": "https://comet.carbon/ext/pcr-japan#",
    "comet-pcr": "https://comet.carbon/ext/pcr#",
    "comet-asi": "https://comet.carbon/ext/aluminium-asi#",
    "comet-tfs": "https://comet.carbon/ext/tfs-pcf#",
    "cadtrust": "https://cadtrust.org/dd#",
    "cadpick": "https://cadtrust.org/dd/pick#",
}
KEEP = {"exactMatch", "closeMatch", "broadMatch", "narrowMatch", "relatedMatch"}


def iri(curie: str) -> str:
    from urllib.parse import quote
    p, _, local = curie.partition(":")
    base = NS_BASES.get(p)
    if not base:
        return curie
    # percent-encode chars that are invalid in an IRI path/fragment (spaces etc.)
    return base + quote(local, safe="._-/:")


def assemble_descriptions() -> dict[str, str]:
    merged: dict[str, str] = {}
    for f in sorted((DATA / "descriptions").glob("desc_*.json")):
        merged.update(json.loads(f.read_text()))
    DESC_OUT.write_text(json.dumps(merged, indent=1, ensure_ascii=False) + "\n")
    return merged


def assemble_matches() -> list[dict]:
    rows: list[dict] = []
    for f in sorted((DATA / "matches").glob("match_*.json")):
        rows.extend(json.loads(f.read_text()))
    kept = [r for r in rows if r.get("relation") in KEEP]
    kept.sort(key=lambda r: -float(r.get("confidence", 0)))
    MATCH_JSON.write_text(json.dumps(
        {"generated_by": "tools/term_intelligence", "status": "proposed",
         "count": len(kept), "proposals": kept}, indent=1) + "\n")
    return kept


def esc(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace('"', '\\"')


def write_ttl(matches: list[dict]) -> None:
    L = [
        "@prefix comet-match: <https://comet.carbon/meta/match#> .",
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
        "@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "",
        "# Proposed cross-namespace term matches (status: proposed / human-gated).",
        "# Each is a reviewable proposal, NOT an asserted skos:exactMatch axiom.",
        "",
    ]
    for i, m in enumerate(matches):
        L.append(f"comet-match:proposal-{i:03d} a comet-match:MatchProposal ;")
        L.append(f"    comet-match:subjectTerm <{iri(m['a'])}> ;")
        L.append(f"    comet-match:objectTerm <{iri(m['b'])}> ;")
        L.append(f'    comet-match:relation "{m["relation"]}" ;')
        L.append(f'    comet-match:confidence "{m.get("confidence",0)}"^^xsd:decimal ;')
        L.append(f'    comet-match:confidenceLow "{m.get("confidenceLow",m.get("confidence",0))}"^^xsd:decimal ;')
        L.append(f'    comet-match:confidenceHigh "{m.get("confidenceHigh",m.get("confidence",0))}"^^xsd:decimal ;')
        if m.get("canonical"):
            L.append(f"    comet-match:canonicalTerm <{iri(m['canonical'])}> ;")
        L.append(f'    skos:note "{esc(m.get("rationale",""))}"@en ;')
        L.append('    comet-match:status "proposed" .')
        L.append("")
    MATCH_TTL.write_text("\n".join(L))


def main() -> int:
    terms = json.loads(TERMS.read_text())
    all_curies = {t["curie"] for t in terms}

    desc = assemble_descriptions()
    missing = sorted(all_curies - set(desc))
    extra = sorted(set(desc) - all_curies)

    matches = assemble_matches()
    write_ttl(matches)

    from collections import Counter
    rels = Counter(m["relation"] for m in matches)
    print(f"descriptions: {len(desc)}/{len(all_curies)} terms covered")
    if missing:
        print(f"  MISSING {len(missing)}: {missing[:12]}{' …' if len(missing) > 12 else ''}")
    if extra:
        print(f"  UNKNOWN curies in descriptions: {len(extra)}: {extra[:6]}")
    print(f"match proposals kept: {len(matches)}  {dict(rels)}")
    print(f"wrote {DESC_OUT.name}, {MATCH_JSON.name}, {MATCH_TTL.name}")
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
