#!/usr/bin/env python3
"""Stage 2 — generate candidate match pairs (recall-oriented, dependency-light).

The LLM adjudicates precision, so this only needs good recall. It scores every
pair of terms by concept-token overlap (label + definition, camelCase-split,
acronym-expanded, stop-word filtered) plus a local-name similarity boost, and
keeps pairs above a threshold — capped per term so no single term floods the
candidate set.

Output: data/candidates/candidates.json    (all candidate pairs, scored)
        data/candidates/cand_batch_NN.json (chunks for adjudication agents)
"""
from __future__ import annotations

import json
import re
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TERMS = HERE / "data" / "terms.json"
CAND_DIR = HERE / "data" / "candidates"

LEX_THRESHOLD = 0.34   # min blended score to be a candidate
PER_TERM_CAP = 6       # keep at most N best candidates per term
CAND_BATCH = 40

ACRONYMS = {
    "coc": "chain of custody", "pcf": "product carbon footprint",
    "pcr": "product category rules", "dqr": "data quality rating",
    "dqi": "data quality indicator", "gwp": "global warming potential",
    "ef": "emission factor", "lca": "life cycle assessment",
    "lcia": "life cycle impact assessment", "epd": "environmental product declaration",
    "ghg": "greenhouse gas", "ccu": "carbon capture utilisation",
    "ccs": "carbon capture storage", "rsl": "reference service life",
    "cbam": "carbon border adjustment", "asi": "aluminium stewardship",
    "tfs": "together for sustainability", "eac": "environmental attribute certificate",
    "svhc": "substance of very high concern", "uom": "unit of measure",
    "wip": "work in process", "dpl": "decarbonisation progress level",
    "spl": "sourcing progress level", "iso": "", "en": "",
}
STOP = {"the", "a", "an", "of", "for", "to", "and", "or", "in", "on", "by", "with",
        "type", "value", "data", "id", "code", "comet", "record", "per", "unit",
        "this", "that", "is", "as", "from", "at",
        # audit / structural tokens — not meaningful for concept matching
        "created", "updated", "staged", "uid", "timestamp", "time", "date",
        "name", "status", "count", "url", "field", "table", "key", "ref"}

# Trivial audit/structural field local-names: obviously the same column reused
# across tables; excluded from candidate matching (no dedup value).
TRIVIAL_LOCALS = {
    "createdat", "updatedat", "timestaged", "id", "orguid", "warehouseprojectid",
    "warehouseunitid", "orgname", "registryof", "projectid", "unitcount",
    "serialnumberblock", "serialnumberpattern",
}


def tokens(text: str) -> set[str]:
    # split camelCase / PascalCase and non-alnum
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    raw = re.findall(r"[a-zA-Z0-9]+", text.lower())
    out: set[str] = set()
    for w in raw:
        w = ACRONYMS.get(w, w)
        for part in w.split():
            if len(part) > 1 and part not in STOP:
                out.add(part)
    return out


def local_of(curie: str) -> str:
    return curie.split(":", 1)[1] if ":" in curie else curie


def is_trivial(curie: str) -> bool:
    """True for audit/structural fields not worth matching (post-dot leaf name)."""
    leaf = local_of(curie).split(".")[-1].lower()
    return leaf in TRIVIAL_LOCALS


def name_sim(a: str, b: str) -> float:
    la, lb = local_of(a).lower(), local_of(b).lower()
    if la == lb:
        return 1.0
    if la in lb or lb in la:
        return 0.6
    return 0.0


def main() -> int:
    terms = json.loads(TERMS.read_text())
    toks = {}
    for t in terms:
        text = f"{t['label']} {t.get('definition','')}"
        toks[t["curie"]] = tokens(text)

    scored: list[dict] = []
    def native(pfx: str) -> bool:
        return pfx.startswith("comet") and pfx not in ("cadtrust", "cadpick")

    for a, b in combinations(terms, 2):
        ca, cb = a["curie"], b["curie"]
        # Dedup targets COMET terms: at least one side must be COMET-native. This
        # keeps native<>native and native<>CAD-Trust conceptual crosswalks but
        # drops the incorporated dictionary's by-design internal repetition.
        if not (native(a["prefix"]) or native(b["prefix"])):
            continue
        if is_trivial(ca) or is_trivial(cb):
            continue
        ta, tb = toks[ca], toks[cb]
        if not ta or not tb:
            continue
        inter = ta & tb
        if not inter:
            continue
        jac = len(inter) / len(ta | tb)
        ns = name_sim(ca, cb)
        blended = max(jac, 0.5 * jac + 0.5 * ns)
        # de-prioritise same-namespace unless very close (cross-ns dedup is the goal)
        if a["prefix"] == b["prefix"] and blended < 0.7:
            continue
        if blended >= LEX_THRESHOLD:
            scored.append({
                "a": ca, "b": cb,
                "a_label": a["label"], "b_label": b["label"],
                "a_ns": a["prefix"], "b_ns": b["prefix"],
                "a_kind": a["kind"], "b_kind": b["kind"],
                "a_def": a.get("definition", ""), "b_def": b.get("definition", ""),
                "lexScore": round(blended, 3),
                "sharedConcepts": sorted(inter)[:8],
            })

    # cap per term to avoid flooding
    from collections import defaultdict
    seen = defaultdict(int)
    scored.sort(key=lambda p: -p["lexScore"])
    kept = []
    for p in scored:
        if seen[p["a"]] < PER_TERM_CAP and seen[p["b"]] < PER_TERM_CAP:
            kept.append(p)
            seen[p["a"]] += 1
            seen[p["b"]] += 1

    (CAND_DIR / "candidates.json").write_text(json.dumps(kept, indent=1) + "\n")
    for f in CAND_DIR.glob("cand_batch_*.json"):
        f.unlink()
    n = 0
    for i in range(0, len(kept), CAND_BATCH):
        (CAND_DIR / f"cand_batch_{n:02d}.json").write_text(
            json.dumps(kept[i:i + CAND_BATCH], indent=1) + "\n")
        n += 1

    print(f"scored candidates kept: {len(kept)} (from {len(scored)} above threshold)")
    print(f"wrote {n} adjudication batches of up to {CAND_BATCH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
