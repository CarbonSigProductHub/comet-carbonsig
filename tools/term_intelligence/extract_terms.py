#!/usr/bin/env python3
"""Stage 1 — extract every COMET term into a flat, self-contained record and
split into batches for the description subagents.

Input:  docs/ontology-data.json  (the gold-master term table)
Output: data/terms.json          (all terms, enriched context)
        data/batches/batch_NN.json  (chunks for parallel description agents)

Each record carries everything an agent needs to write a plain-English gloss
without extra lookups: curie, label, kind, namespace/layer, existing definition,
source, and domain/range.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ONTOLOGY = ROOT / "docs" / "ontology-data.json"
TERMS_OUT = HERE / "data" / "terms.json"
BATCH_DIR = HERE / "data" / "batches"
BATCH_SIZE = 140

NS_HUMAN = {
    "comet": "COMET Core (L1 — organisations, sites, processes, materials, units)",
    "comet-ef": "Emission Factor (L2)",
    "comet-sc": "Supply Chain & Activity Data (L3)",
    "comet-pcf": "Product Carbon Footprint (L4)",
    "comet-eac": "Environmental Attribute Certificate (L5)",
    "comet-ver": "Verification & Assurance (L6)",
    "comet-mkt": "Market Signals (L7)",
    "comet-rs": "Responsible Steel extension",
    "comet-cn": "ISO 14068 Carbon Neutrality extension",
    "comet-pj": "PCR Japan / SuMPO EcoLeaf extension",
    "comet-pcr": "Product Category Rules (PCR) method extension",
    "comet-asi": "Aluminium Stewardship Initiative (ASI) extension",
    "comet-tfs": "Together for Sustainability (TfS) PCF Data Model extension",
    "cadtrust": "CAD Trust carbon-registry data dictionary (incorporated)",
    "cadpick": "CAD Trust picklist / enumeration value (incorporated)",
}


def record(t: dict) -> dict:
    return {
        "curie": t["curie"],
        "label": t.get("label") or t.get("local"),
        "kind": t.get("kind", ""),
        "prefix": t.get("prefix", ""),
        "namespace": NS_HUMAN.get(t.get("prefix", ""), t.get("namespace", "")),
        "layer": t.get("layer", ""),
        "datatype": t.get("datatype", ""),
        "definition": (t.get("definition") or "").strip(),
        "source": t.get("source", ""),
        "subClassOf": t.get("subClassOf", []),
        "domain": t.get("domain", []),
        "range": t.get("range", []),
    }


def main() -> int:
    data = json.loads(ONTOLOGY.read_text())
    terms = [record(t) for t in data["terms"]]
    terms.sort(key=lambda r: (r["prefix"], r["curie"]))
    TERMS_OUT.write_text(json.dumps(terms, indent=1) + "\n")

    # clear + rewrite batches
    for f in BATCH_DIR.glob("batch_*.json"):
        f.unlink()
    n = 0
    for i in range(0, len(terms), BATCH_SIZE):
        chunk = terms[i:i + BATCH_SIZE]
        (BATCH_DIR / f"batch_{n:02d}.json").write_text(json.dumps(chunk, indent=1) + "\n")
        n += 1

    print(f"extracted {len(terms)} terms -> {TERMS_OUT.relative_to(ROOT)}")
    print(f"wrote {n} batches of up to {BATCH_SIZE} into {BATCH_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
