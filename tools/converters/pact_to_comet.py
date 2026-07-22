#!/usr/bin/env python3
"""Convert a PACT v3 JSON payload into COMET JSON-LD.

Non-destructive enrichment by default: original PACT fields are preserved,
COMET @context and mapped properties are injected alongside them.  Use
``--strip-pact`` to emit pure COMET output.

Usage:
    python pact_to_comet.py input.json
    python pact_to_comet.py input.json --output enriched.json
    python pact_to_comet.py input.json --strip-pact

As a library:
    from pact_to_comet import convert_pact_to_comet
    documents = convert_pact_to_comet("pact_payload.json")
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# ── Context URIs ─────────────────────────────────────────────────────
PACT_CONTEXT = "https://wbcsd.github.io/pact/v3/context.json"
COMET_CONTEXT = "https://comet.carbon/v1/jsonld/context.json"
COMET_TYPE = "comet-pcf:ProductCarbonFootprint"

# ── PACT v3 → COMET field mapping (44 fields from spec §B2 / data-exchange §2a)
#
# Each entry is (pact_dotpath, comet_target).
# comet_target uses dot-notation: "organization.orgName" means
# doc["organization"]["orgName"].
# A target of None means the field is PACT-only (not mapped to COMET).
#
FIELD_MAP: list[tuple[str, str | None]] = [
    # identity / metadata
    ("id",                                      "pcfId"),
    ("specVersion",                             None),
    ("version",                                 None),
    ("created",                                 None),
    ("updated",                                 None),
    ("status",                                  None),
    ("validityPeriodStart",                     "referencePeriod.startDate"),
    ("validityPeriodEnd",                       "referencePeriod.endDate"),
    # organisation
    ("companyName",                             "organization.orgName"),
    ("companyIds",                              "organization.orgId"),
    # product / material
    ("productDescription",                      "material.materialName"),
    ("productIds",                              "material.materialId"),
    ("productCategoryCpc",                      "material.cpcCode"),
    ("productNameCompany",                      "material.tradeName"),
    # pcf core
    ("pcf.declaredUnit",                        "declaredUnit"),
    ("pcf.unitaryProductAmount",                "unitaryProductAmount"),
    ("pcf.pCfExcludingBiogenic",                "fossilGWP"),
    ("pcf.pCfIncludingBiogenic",                "totalGWP"),
    ("pcf.fossilGhgEmissions",                  "fossilEmissions"),
    ("pcf.biogenicCarbonContent",               "biogenicCarbonContent"),
    ("pcf.dLucGhgEmissions",                    "landUseChange"),
    ("pcf.biogenicCarbonWithdrawal",            "biogenicUptake"),
    ("pcf.aircraftGhgEmissions",                "aircraftEmissions"),
    ("pcf.characterizationFactors",             "ipccAR"),
    ("pcf.crossSectoralStandardsUsed",          "standardRef"),
    ("pcf.productOrSectorSpecificRules",        "pcrName"),  # extract [0].name
    ("pcf.boundaryProcessesDescription",        "boundaryDescription"),
    ("pcf.allocationRulesDescription",          "allocationDescription"),
    ("pcf.referencePeriodStart",                "referencePeriod.startDate"),
    ("pcf.referencePeriodEnd",                  "referencePeriod.endDate"),
    ("pcf.geographyCountry",                    "site.siteCountry"),
    ("pcf.geographyRegionOrSubregion",          "site.region"),
    ("pcf.exemptedEmissionsPercent",            "exemptedPercent"),
    ("pcf.primaryDataShare",                    "primaryDataShare"),
    ("pcf.packagingGhgEmissions",               "packagingEmissions"),
    # dqi
    ("pcf.dqi.coveragePercent",                 "dqi.coveragePercent"),
    ("pcf.dqi.technologicalDQR",                "dqi.technologyDQI"),
    ("pcf.dqi.temporalDQR",                     "dqi.temporalityDQI"),
    ("pcf.dqi.geographicalDQR",                 "dqi.geographyDQI"),
    ("pcf.dqi.completenessDQR",                 "dqi.reliabilityDQI"),
    # assurance → verification
    ("pcf.assurance.assurance",                 "verification.hasAssurance"),
    ("pcf.assurance.level",                     "verification.levelType"),
    ("pcf.assurance.providerName",              "verification.verifierName"),
    ("pcf.assurance.completedAt",               "verification.verificationDate"),
    ("pcf.assurance.standardName",              "verification.standardRef"),
]

# Fields that are PACT-only (no COMET mapping) — used for --strip-pact
_PACT_ONLY_FIELDS: set[str] = {
    "specVersion", "version", "created", "updated", "status",
    "validityPeriodStart", "validityPeriodEnd",
    "companyName", "companyIds",
    "productDescription", "productIds", "productCategoryCpc", "productNameCompany",
    "pcf", "comment", "precedingPfIds",
}


def _get_nested(obj: dict[str, Any], dotpath: str) -> Any:
    """Retrieve a value from *obj* by dot-separated path.  Returns _MISSING on miss."""
    parts = dotpath.split(".")
    cur: Any = obj
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return _MISSING
    return cur


class _MissingSentinel:
    """Sentinel for missing values (distinct from None)."""
    def __bool__(self) -> bool:
        return False
    def __repr__(self) -> str:
        return "<MISSING>"

_MISSING = _MissingSentinel()


def _set_nested(doc: dict[str, Any], dotpath: str, value: Any) -> None:
    """Set a value in *doc* at a dot-separated path, creating intermediates."""
    parts = dotpath.split(".")
    cur = doc
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value


def _collect_all_pact_keys(obj: dict[str, Any], prefix: str = "") -> set[str]:
    """Recursively collect all dot-paths present in a PACT object."""
    keys: set[str] = set()
    for k, v in obj.items():
        full = f"{prefix}.{k}" if prefix else k
        keys.add(full)
        if isinstance(v, dict):
            keys.update(_collect_all_pact_keys(v, full))
    return keys


def _convert_one(pact: dict[str, Any], *, strip_pact: bool = False) -> dict[str, Any]:
    """Convert a single PACT v3 ProductFootprint dict to COMET JSON-LD."""

    # Start with the COMET shell
    comet: dict[str, Any] = {}

    # Map fields
    mapped_paths: set[str] = set()
    for pact_path, comet_target in FIELD_MAP:
        val = _get_nested(pact, pact_path)
        if val is _MISSING:
            continue
        mapped_paths.add(pact_path)
        if comet_target is None:
            continue  # PACT-only metadata

        # Special handling for productOrSectorSpecificRules → pcrName
        if pact_path == "pcf.productOrSectorSpecificRules":
            if isinstance(val, list) and val:
                names = [r.get("name", r.get("operator", "")) for r in val if isinstance(r, dict)]
                val = "; ".join(n for n in names if n) or None
                if val is None:
                    continue
            elif isinstance(val, str):
                pass  # keep as-is
            else:
                continue

        _set_nested(comet, comet_target, val)

    # Upgrade PACT's lossy edition tag to a specific COMET value set.
    # PACT's characterizationFactors names only an edition; map it to that
    # edition's conventional value set and record that the basis was DECLARED
    # by the source. The variant is the PACT/GHG-Protocol default for the
    # edition (AR6 -> fossil methane; AR5 -> no climate-carbon feedback);
    # ipccAR is kept verbatim for round-trip fidelity.
    edition = comet.get("ipccAR")
    _EDITION_TO_VALUE_SET = {"AR6": "ipcc:AR6-fossilCH4", "AR5": "ipcc:AR5-noFeedback"}
    if edition in _EDITION_TO_VALUE_SET:
        comet.setdefault("gwpValueSet", _EDITION_TO_VALUE_SET[edition])
        comet.setdefault("arBasis", "declared")
        comet.setdefault("gwpHorizon", "GWP100")

    # Report unmapped fields
    all_pact_keys = _collect_all_pact_keys(pact)
    # Mapped paths and their parents
    mapped_or_parent: set[str] = set()
    for mp in mapped_paths:
        parts = mp.split(".")
        for i in range(len(parts)):
            mapped_or_parent.add(".".join(parts[: i + 1]))
    unmapped = sorted(all_pact_keys - mapped_or_parent - {"@context", "@type"})
    for u in unmapped:
        print(f"Warning: unmapped PACT field: {u}", file=sys.stderr)

    # Build final document
    if strip_pact:
        # Pure COMET output
        doc: dict[str, Any] = {
            "@context": COMET_CONTEXT,
            "@type": COMET_TYPE,
        }
        doc.update(comet)
    else:
        # Non-destructive: keep original PACT payload, inject COMET context + type + mapped fields
        doc = dict(pact)
        # Set context array
        existing_ctx = doc.get("@context")
        if existing_ctx is None:
            doc["@context"] = [PACT_CONTEXT, COMET_CONTEXT]
        elif isinstance(existing_ctx, str):
            if COMET_CONTEXT not in existing_ctx:
                doc["@context"] = [existing_ctx, COMET_CONTEXT]
        elif isinstance(existing_ctx, list):
            if COMET_CONTEXT not in existing_ctx:
                doc["@context"] = existing_ctx + [COMET_CONTEXT]
        doc["@type"] = COMET_TYPE

        # Merge COMET mapped fields into doc (nested objects get merged)
        for key, val in comet.items():
            if isinstance(val, dict) and isinstance(doc.get(key), dict):
                doc[key].update(val)
            else:
                doc[key] = val

    return doc


# ── Public API ───────────────────────────────────────────────────────

def convert_pact_to_comet(
    json_path: str | Path,
    *,
    strip_pact: bool = False,
) -> list[dict[str, Any]]:
    """Read a PACT v3 JSON file and return COMET JSON-LD documents.

    Parameters
    ----------
    json_path : path to the PACT v3 JSON file
    strip_pact : if True, produce pure COMET (remove PACT-only fields)

    Returns
    -------
    list of COMET JSON-LD dicts
    """
    json_path = Path(json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    with json_path.open(encoding="utf-8") as fh:
        data = json.load(fh)

    # Handle single object or array
    if isinstance(data, dict):
        # Could be a single ProductFootprint or a wrapper with "data" array
        if "data" in data and isinstance(data["data"], list):
            items = data["data"]
        else:
            items = [data]
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError("Expected a JSON object or array of ProductFootprints")

    return [_convert_one(item, strip_pact=strip_pact) for item in items]


# ── CLI bridge ────────────────────────────────────────────────────────

def convert(input_path: str) -> list[dict[str, Any]]:
    """Bridge for comet_cli.py: convert an input file to COMET JSON-LD."""
    return convert_pact_to_comet(input_path)


# ── CLI ──────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert PACT v3 JSON to COMET JSON-LD.",
        epilog=(
            "Examples:\n"
            "  python pact_to_comet.py pact_payload.json\n"
            "  python pact_to_comet.py pact_payload.json --output enriched.json\n"
            "  python pact_to_comet.py pact_payload.json --strip-pact\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="Path to the PACT v3 JSON file")
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "--strip-pact",
        action="store_true",
        help="Output pure COMET JSON-LD without PACT-specific fields",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        docs = convert_pact_to_comet(args.input, strip_pact=args.strip_pact)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output = docs if len(docs) > 1 else docs[0]
    text = json.dumps(output, indent=2, ensure_ascii=False) + "\n"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
