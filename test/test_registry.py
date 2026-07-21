#!/usr/bin/env python3
"""Plain-assert test suite for the shared registry, extension TTL, and validator.
Run: python test/test_registry.py   (exit 0 = pass)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from validate_curies import load_registry, validate_curies, class_base  # noqa: E402

FAILS: list[str] = []


def check(name: str, cond: bool) -> None:
    print(("PASS" if cond else "FAIL") + f"  {name}")
    if not cond:
        FAILS.append(name)


def main() -> int:
    reg_path = ROOT / "registry" / "comet-curies.json"
    check("registry file exists", reg_path.exists())
    reg = json.loads(reg_path.read_text())

    allow = load_registry(reg_path)
    check("registry non-trivial (>200 CURIEs)", len(allow) > 200)
    # total must equal the sum of all known parts (published + all *_pending lists)
    pending_total = sum(
        v for k, v in reg["counts"].items()
        if k.endswith("_pending") and isinstance(v, int)
    )
    check("counts internally consistent",
          reg["counts"]["total"] == reg["counts"]["comet_published"] + pending_total)

    # Every pending comet-pcr CURIE must actually be defined in the TTL.
    ttl = (ROOT / "extensions" / "comet-pcr.ttl").read_text()
    for curie in reg["comet_pcr_pending"]:
        check(f"comet-pcr term defined in TTL: {curie}", f"{curie} " in ttl or f"{curie}\n" in ttl)

    # Every pending comet-pj CURIE must be defined in the ext/pcr-japan TTL.
    pj_ttl = (ROOT / "ext" / "pcr-japan" / "comet-ext-pcr-japan.ttl").read_text()
    for curie in reg.get("comet_pj_pending", []):
        check(f"comet-pj term defined in TTL: {curie}", f"{curie} " in pj_ttl or f"{curie}\n" in pj_ttl)

    # Keystone + headline terms present.
    for must in ["comet-pcr:PCRDocument", "comet-pcr:governedByPCR",
                 "comet-pcr:CutOffRule", "comet-pcr:DeclaredModule"]:
        check(f"registry contains {must}", must in allow)

    # GWP value-set vocabulary: the 7 value sets + 4 provenance properties.
    for must in ["ipcc:SAR", "ipcc:AR4", "ipcc:AR5-noFeedback",
                 "ipcc:AR5-withFeedback", "ipcc:AR5-UNFCCC",
                 "ipcc:AR6-fossilCH4", "ipcc:AR6-biogenicCH4",
                 "comet-pcr:gwpValueSet", "comet-pcr:arBasis",
                 "comet-pcr:arConfidence", "comet-pcr:gwpHorizon"]:
        check(f"registry contains {must}", must in allow)

    # Every pending ipcc CURIE must actually be defined in the TTL.
    ipcc_ttl = (ROOT / "extensions" / "ipcc-gwp.ttl").read_text()
    for curie in reg.get("ipcc_pending", []):
        check(f"ipcc term defined in TTL: {curie}",
              f"{curie} " in ipcc_ttl or f"{curie}\n" in ipcc_ttl)

    # The export layer must refuse to assert a false PACT edition for a value
    # set PACT cannot express (SAR, AR4) — the BLOCK condition.
    sys.path.insert(0, str(ROOT / "tools" / "converters"))
    from comet_to_pact import _pact_characterization_factors  # noqa: E402
    check("AR6 value set exports to PACT AR6",
          _pact_characterization_factors({"gwpValueSet": "ipcc:AR6-fossilCH4"}) == "AR6")
    check("AR5 variant exports to PACT AR5",
          _pact_characterization_factors({"gwpValueSet": "ipcc:AR5-UNFCCC"}) == "AR5")
    check("AR4 is non-exportable to PACT (BLOCK)",
          _pact_characterization_factors({"gwpValueSet": "ipcc:AR4"}) is None)
    check("SAR is non-exportable to PACT (BLOCK)",
          _pact_characterization_factors({"gwpValueSet": "ipcc:SAR"}) is None)
    check("indeterminate basis is non-exportable to PACT (BLOCK)",
          _pact_characterization_factors({"arBasis": "indeterminate"}) is None)
    check("legacy ipccAR still exports when no value set present",
          _pact_characterization_factors({"ipccAR": "AR5"}) == "AR5")

    # Validator: good terms pass.
    good = validate_curies(["comet:Process", "comet-pcf:FunctionalUnit",
                            "comet-pcr:PCRDocument", "comet-ef:EmissionFactor.efValue"], allow)
    check("known-good CURIEs all valid", good["invalid"] == [])

    # Validator catches the three real pcrbase bugs.
    bugs = validate_curies(["comet-core:GeographyScope", "comet:FunctionalUnit",
                            "comet-pcf:biogenicCarbon"], allow)
    check("pcrbase bug comet-core:GeographyScope flagged", "comet-core:GeographyScope" in bugs["invalid"])
    check("pcrbase bug comet:FunctionalUnit flagged", "comet:FunctionalUnit" in bugs["invalid"])
    check("pcrbase bug comet-pcf:biogenicCarbon flagged", "comet-pcf:biogenicCarbon" in bugs["invalid"])

    # The corrected forms are valid.
    fixed = validate_curies(["comet-ef:GeographyScope", "comet-pcf:FunctionalUnit",
                             "comet-pcf:BiogenicCarbon"], allow)
    check("corrected CURIEs all valid", fixed["invalid"] == [])

    # property-base leniency
    check("class_base strips property", class_base("comet-pcf:FunctionalUnit.referenceFlow") == "comet-pcf:FunctionalUnit")

    # None ignored.
    check("None entries ignored", validate_curies([None, "comet:Process"], allow)["valid"] == ["comet:Process"])

    print(f"\n{'ALL PASS' if not FAILS else str(len(FAILS)) + ' FAILED: ' + ', '.join(FAILS)}")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    raise SystemExit(main())
