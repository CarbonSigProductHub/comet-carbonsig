"""COMET → PACT v3 converter.

Export a COMET ProductCarbonFootprint JSON-LD file as a PACT v3-compliant
JSON payload suitable for any Pathfinder API consumer.

Usage:
    python comet_to_pact.py input.comet.json
    python comet_to_pact.py input.comet.json --output out.json
    python comet_to_pact.py input.comet.json --pact-only

The reverse field mapping covers all 44 PACT v3 fields documented in
docs/data-exchange.html Section 2a.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# PACT v3 required fields (used for validation)
# ---------------------------------------------------------------------------

PACT_REQUIRED_FIELDS: list[str] = [
    "id",
    "specVersion",
    "version",
    "created",
    "status",
    "companyName",
    "companyIds",
    "productDescription",
    "productIds",
    "productCategoryCpc",
    "pcf",
]

PACT_PCF_REQUIRED_FIELDS: list[str] = [
    "declaredUnit",
    "unitaryProductAmount",
    "pCfExcludingBiogenic",
    "fossilGhgEmissions",
    "characterizationFactors",
    "crossSectoralStandardsUsed",
    "boundaryProcessesDescription",
    "referencePeriodStart",
    "referencePeriodEnd",
    "geographyCountry",
]

# ---------------------------------------------------------------------------
# COMET declared-unit enum → PACT declared-unit enum
# The COMET spec uses the same string values as PACT for the core set;
# we explicitly map in case the COMET schema uses slightly different forms.
# ---------------------------------------------------------------------------

_UNIT_TO_PACT: dict[str, str] = {
    "kilogram": "kilogram",
    "litre": "liter",
    "liter": "liter",
    "cubic meter": "cubic meter",
    "cubicMetre": "cubic meter",
    "kilowatt hour": "kilowatt hour",
    "kilowattHour": "kilowatt hour",
    "megajoule": "megajoule",
    "tonne kilometre": "tonne kilometre",
    "tonneKilometre": "tonne kilometre",
    "square meter": "square meter",
    "squareMetre": "square meter",
}

# ---------------------------------------------------------------------------
# GWP value set -> PACT edition collapse.
# PACT's characterizationFactors enum names only an edition. A COMET value set
# that no edition label can represent (SAR, AR4) is non-exportable to PACT.
# Mirrors ipcc:pactExportable / ipcc:pactEnumValue in extensions/ipcc-gwp.ttl.
# ---------------------------------------------------------------------------

_VALUE_SET_TO_PACT_EDITION: dict[str, Optional[str]] = {
    "ipcc:AR6-fossilCH4": "AR6",
    "ipcc:AR6-biogenicCH4": "AR6",
    "ipcc:AR5-noFeedback": "AR5",
    "ipcc:AR5-withFeedback": "AR5",
    "ipcc:AR5-UNFCCC": "AR5",
    "ipcc:AR4": None,   # not expressible in PACT's enum
    "ipcc:SAR": None,   # not expressible in PACT's enum
}


def _pact_characterization_factors(comet: dict[str, Any]) -> Optional[str]:
    """Return the PACT characterizationFactors edition, or None if the factor
    is non-exportable to PACT (SAR, AR4, or indeterminate basis)."""
    value_set = _get(comet, "gwpValueSet")
    ar_basis = _get(comet, "arBasis")

    if ar_basis == "indeterminate" or (value_set is None and ar_basis == "indeterminate"):
        print("WARNING: factor has an indeterminate GWP basis — non-declarable "
              "into PACT; omitting characterizationFactors.", file=sys.stderr)
        return None

    if value_set is not None:
        if value_set not in _VALUE_SET_TO_PACT_EDITION:
            print(f"WARNING: unknown gwpValueSet {value_set!r}; omitting "
                  "characterizationFactors.", file=sys.stderr)
            return None
        edition = _VALUE_SET_TO_PACT_EDITION[value_set]
        if edition is None:
            print(f"WARNING: gwpValueSet {value_set} is not expressible in PACT's "
                  "characterizationFactors enum — factor is non-conformant to PACT "
                  "v3; omitting the field rather than asserting a false edition.",
                  file=sys.stderr)
            return None
        return edition

    # No value set: fall back to the legacy edition-only field.
    return _get(comet, "ipccAR", "characterizationFactors", default="AR6")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Walk nested dicts/keys and return the first non-None value found."""
    for key in keys:
        parts = key.split(".")
        obj: Any = data
        for part in parts:
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                obj = None
                break
        if obj is not None:
            return obj
    return default


def _strip_comet_extensions(pact: dict[str, Any]) -> dict[str, Any]:
    """Remove any top-level keys that are COMET namespace extensions."""
    comet_prefixes = ("comet:", "comet-pcf:", "comet-eac:", "comet-ver:",
                      "comet-mkt:", "comet-sc:", "comet-ef:")
    return {
        k: v for k, v in pact.items()
        if not any(k.startswith(p) for p in comet_prefixes)
    }


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------


def comet_to_pact(
    comet: dict[str, Any],
    *,
    pact_only: bool = False,
) -> dict[str, Any]:
    """Convert a COMET PCF JSON-LD dict to a PACT v3 dict.

    Parameters
    ----------
    comet : dict
        Parsed COMET JSON-LD document.
    pact_only : bool
        If True, strip all COMET extension fields from the output.

    Returns
    -------
    dict
        PACT v3-shaped dictionary.
    """

    # --- Top-level identity fields -------------------------------------------
    pact_id = _get(comet, "pcfId", "id")
    if pact_id is None:
        pact_id = str(uuid.uuid4())
    # Ensure URN prefix
    if not pact_id.startswith("urn:uuid:"):
        try:
            uuid.UUID(pact_id)
            pact_id = f"urn:uuid:{pact_id}"
        except ValueError:
            pass  # keep as-is if not a bare UUID

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    pact: dict[str, Any] = {
        "id": pact_id,
        "specVersion": "3.0.0",
        "version": _get(comet, "version", "dcterms:version", default=1),
        "created": _get(comet, "created", "dcterms:created", default=now_iso),
        "updated": _get(comet, "updated", "dcterms:modified"),
        "status": _get(comet, "status", default="Active"),
    }

    # --- Validity period -----------------------------------------------------
    validity_start = _get(
        comet,
        "validityPeriodStart",
        "referencePeriod.startDate",
        "reportingPeriod.startDate",
    )
    validity_end = _get(
        comet,
        "validityPeriodEnd",
        "referencePeriod.endDate",
        "reportingPeriod.endDate",
    )
    if validity_start:
        pact["validityPeriodStart"] = validity_start
    if validity_end:
        pact["validityPeriodEnd"] = validity_end

    # --- Organisation --------------------------------------------------------
    org = comet.get("organization", {})
    pact["companyName"] = _get(comet, "organization.orgName", default="")
    org_ids = _get(comet, "organization.orgId")
    if isinstance(org_ids, str):
        org_ids = [org_ids]
    pact["companyIds"] = org_ids or []

    # --- Product / material --------------------------------------------------
    mat = comet.get("material", {})
    pact["productDescription"] = _get(
        comet, "material.materialName", "productDescription", default=""
    )
    mat_ids = _get(comet, "material.materialId", "productIds")
    if isinstance(mat_ids, str):
        mat_ids = [mat_ids]
    pact["productIds"] = mat_ids or []
    pact["productCategoryCpc"] = _get(
        comet, "material.cpcCode", "productCategoryCpc", default=""
    )
    trade_name = _get(comet, "material.tradeName", "productNameCompany")
    if trade_name:
        pact["productNameCompany"] = trade_name

    # --- PCF block -----------------------------------------------------------
    pcf: dict[str, Any] = {}

    # Declared unit
    raw_unit = _get(comet, "declaredUnit", default="kilogram")
    pcf["declaredUnit"] = _UNIT_TO_PACT.get(raw_unit, raw_unit)

    pcf["unitaryProductAmount"] = _get(
        comet, "unitaryProductAmount", default=1
    )
    pcf["pCfExcludingBiogenic"] = _get(comet, "fossilGWP", default=0)
    pcf["pCfIncludingBiogenic"] = _get(comet, "totalGWP")
    pcf["fossilGhgEmissions"] = _get(
        comet, "fossilEmissions", "fossilGWP", default=0
    )

    # Biogenic / land use
    pcf["biogenicCarbonContent"] = _get(
        comet, "biogenicCarbonContent", "biogenicCarbon.biogenicCarbonContent",
        default=0,
    )
    pcf["dLucGhgEmissions"] = _get(
        comet, "landUseChange", "biogenicCarbon.landUseChange", default=0,
    )
    pcf["biogenicCarbonWithdrawal"] = _get(
        comet, "biogenicUptake", "biogenicCarbon.biogenicUptake", default=0,
    )

    # Transport / packaging
    pcf["aircraftGhgEmissions"] = _get(comet, "aircraftEmissions", default=0)
    pcf["packagingGhgEmissions"] = _get(comet, "packagingEmissions", default=0)

    # IPCC AR / GWP value set.
    # COMET's gwpValueSet (edition + variant) is the source of truth; PACT's
    # characterizationFactors enum accepts only an edition label. Collapse the
    # value set to its PACT edition where one exists; where it does not (SAR,
    # AR4, or an indeterminate factor) the factor is legitimately NON-EXPORTABLE
    # to PACT — we omit the field and warn rather than assert a false edition.
    cf = _pact_characterization_factors(comet)
    if cf is not None:
        pcf["characterizationFactors"] = cf

    # Standards
    std_ref = _get(comet, "standardRef", "standardName")
    if isinstance(std_ref, str):
        std_ref = [std_ref]
    pcf["crossSectoralStandardsUsed"] = std_ref or []

    # PCR
    pcr_name = _get(comet, "pcrName")
    if pcr_name:
        pcf["productOrSectorSpecificRules"] = [
            {"operator": "Other", "ruleNames": [pcr_name]}
        ]

    # Allocation
    alloc_desc = _get(comet, "allocationDescription")
    if alloc_desc:
        pcf["allocationRulesDescription"] = alloc_desc

    # Boundary
    pcf["boundaryProcessesDescription"] = _get(
        comet, "boundaryDescription", default=""
    )

    # Reference period
    pcf["referencePeriodStart"] = _get(
        comet,
        "referencePeriod.startDate",
        "reportingPeriod.startDate",
        default="",
    )
    pcf["referencePeriodEnd"] = _get(
        comet,
        "referencePeriod.endDate",
        "reportingPeriod.endDate",
        default="",
    )

    # Geography
    pcf["geographyCountry"] = _get(
        comet, "site.siteCountry", "organization.country", default=""
    )
    region = _get(comet, "site.region")
    if region:
        pcf["geographyRegionOrSubregion"] = region

    # Exempted
    exempted = _get(comet, "exemptedPercent")
    if exempted is not None:
        pcf["exemptedEmissionsPercent"] = exempted

    # Primary data share
    pds = _get(comet, "primaryDataShare")
    if pds is not None:
        pcf["primaryDataShare"] = pds

    # --- DQI -----------------------------------------------------------------
    dqi_src = comet.get("dqi", comet.get("dataQuality", {}))
    if dqi_src:
        dqi: dict[str, Any] = {}
        cov = _get(dqi_src, "coveragePercent", "coverageDQI")
        if cov is not None:
            dqi["coveragePercent"] = cov
        tech = _get(dqi_src, "technologyDQI", "technologicalDQR")
        if tech is not None:
            dqi["technologicalDQR"] = tech
        temp = _get(dqi_src, "temporalityDQI", "temporalDQR")
        if temp is not None:
            dqi["temporalDQR"] = temp
        geo = _get(dqi_src, "geographyDQI", "geographicalDQR")
        if geo is not None:
            dqi["geographicalDQR"] = geo
        rel = _get(dqi_src, "reliabilityDQI", "completenessDQR")
        if rel is not None:
            dqi["completenessDQR"] = rel
        if dqi:
            pcf["dqi"] = dqi

    # --- Assurance / verification --------------------------------------------
    ver_src = comet.get("verification", comet.get("assurance", {}))
    if ver_src:
        assurance: dict[str, Any] = {}
        has = _get(ver_src, "hasAssurance")
        if has is not None:
            assurance["assurance"] = has
        level = _get(ver_src, "levelType", "level")
        if level:
            assurance["level"] = level
        provider = _get(ver_src, "verifierName", "providerName")
        if provider:
            assurance["providerName"] = provider
        completed = _get(ver_src, "verificationDate", "completedAt")
        if completed:
            assurance["completedAt"] = completed
        std_name = _get(ver_src, "standardRef", "standardName")
        if std_name:
            assurance["standardName"] = std_name
        if assurance:
            pcf["assurance"] = assurance

    # Remove None values from pcf
    pcf = {k: v for k, v in pcf.items() if v is not None}

    pact["pcf"] = pcf

    # Remove None values from top level
    pact = {k: v for k, v in pact.items() if v is not None}

    # --- Strip COMET extensions if requested ---------------------------------
    if pact_only:
        pact = _strip_comet_extensions(pact)

    return pact


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_pact_output(pact: dict[str, Any]) -> list[str]:
    """Check that a PACT v3 dict has all required fields.

    Returns a list of human-readable error strings (empty if valid).
    """
    errors: list[str] = []

    for field in PACT_REQUIRED_FIELDS:
        if field not in pact:
            errors.append(f"Missing required top-level field: {field}")
        elif field in ("companyName", "productDescription", "productCategoryCpc"):
            if not pact[field]:
                errors.append(f"Empty required top-level field: {field}")

    pcf = pact.get("pcf", {})
    for field in PACT_PCF_REQUIRED_FIELDS:
        if field not in pcf:
            errors.append(f"Missing required pcf field: pcf.{field}")
        elif field in ("boundaryProcessesDescription",):
            if not pcf[field]:
                errors.append(f"Empty required pcf field: pcf.{field}")

    return errors


# ---------------------------------------------------------------------------
# File-level I/O
# ---------------------------------------------------------------------------


def convert_file(
    input_path: Path,
    *,
    pact_only: bool = False,
) -> str:
    """Read a COMET JSON-LD file and return PACT v3 JSON string.

    Parameters
    ----------
    input_path : Path
        Path to the COMET JSON-LD file.
    pact_only : bool
        Strip COMET extension fields from output.

    Returns
    -------
    str
        Pretty-printed PACT v3 JSON.
    """
    with open(input_path, "r", encoding="utf-8") as fh:
        comet = json.load(fh)

    # Handle array input — convert each element
    if isinstance(comet, list):
        results = [comet_to_pact(item, pact_only=pact_only) for item in comet]
        return json.dumps(results, indent=2, ensure_ascii=False)

    pact = comet_to_pact(comet, pact_only=pact_only)
    return json.dumps(pact, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI bridge
# ---------------------------------------------------------------------------


def export(input_path: str) -> str:
    """Bridge for comet_cli.py: export a COMET file to PACT v3 JSON."""
    return convert_file(Path(input_path))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point.

    Returns
    -------
    int
        Exit code: 0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(
        prog="comet_to_pact",
        description="Convert a COMET PCF JSON-LD file to PACT v3 JSON.",
        epilog="Example: python comet_to_pact.py steel-pcf.comet.json --output pact.json",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to a COMET JSON-LD file (.comet.json)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--pact-only",
        action="store_true",
        default=False,
        help="Strip all COMET extension fields from output",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        default=False,
        help="Validate output against PACT v3 required fields",
    )

    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        return 1

    try:
        result_json = convert_file(args.input, pact_only=args.pact_only)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in {args.input}: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error converting {args.input}: {exc}", file=sys.stderr)
        return 1

    # Optional validation
    if args.validate:
        pact_data = json.loads(result_json)
        items = pact_data if isinstance(pact_data, list) else [pact_data]
        all_errors: list[str] = []
        for idx, item in enumerate(items):
            errors = validate_pact_output(item)
            for err in errors:
                prefix = f"[{idx}] " if len(items) > 1 else ""
                all_errors.append(f"{prefix}{err}")
        if all_errors:
            print("Validation warnings:", file=sys.stderr)
            for err in all_errors:
                print(f"  - {err}", file=sys.stderr)

    # Output
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result_json, encoding="utf-8")
        print(f"Wrote PACT v3 JSON to {args.output}", file=sys.stderr)
    else:
        print(result_json)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
