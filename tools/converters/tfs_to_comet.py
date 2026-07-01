#!/usr/bin/env python3
"""Convert a TfS PCF Data Model v3.1 JSON payload into COMET JSON-LD.

The TfS PCF Data Model v3.1 (Together for Sustainability, September 2025) uses
technical field names (``specVersion``, ``partialFullPcf``, ``companyName``,
``productionStage.fossilGhgEmissions`` …).  This converter types one such
payload as a ``comet-tfs:TfSProductFootprint`` node whose properties use the
``comet-tfs:`` terms defined in ``ext/tfs-pcf/comet-ext-tfs-pcf.ttl``.

TfS fields that already have a COMET home (company + product identity, declared
unit, geography, reference period) are re-expressed on the core ``comet:`` /
``comet-pcf:`` terms named in Section A of the TTL (the MERGE targets); the
TfS-specific machinery (partial/full boundary flag, the A–H GWP position
decomposition per life-cycle stage, mass balancing, data-quality rating,
verification shares, carbon-content breakdown and Attestation of Conformance
array) is carried on ``comet-tfs:`` (the EXPAND classes, Section B).

Usage:
    python tfs_to_comet.py input.json
    python tfs_to_comet.py input.json --output comet.json

As a library:
    from tfs_to_comet import convert
    comet = convert(tfs_payload_dict)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# ── Context / type ───────────────────────────────────────────────────
# @context references the local COMET context document plus an inline binding
# for the comet-tfs extension namespace (the context file itself only ships the
# core layer prefixes).
COMET_CONTEXT_FILE = "comet-context.jsonld"
COMET_TFS_NS = "https://comet.carbon/ext/tfs-pcf#"
COMET_CONTEXT: list[Any] = [COMET_CONTEXT_FILE, {"comet-tfs": COMET_TFS_NS}]
COMET_TYPE = "comet-tfs:TfSProductFootprint"


# ── Enumeration value lists (TfS value → comet-tfs NamedIndividual CURIE) ──
_BOUNDARY: dict[str, str] = {
    "cradle-to-gate": "comet-tfs:CradleToGate",
    "cradle-to-grave": "comet-tfs:CradleToGrave",
}

_CHARACTERIZATION: dict[str, str] = {
    "AR1": "comet-tfs:AR1", "AR2": "comet-tfs:AR2", "AR3": "comet-tfs:AR3",
    "AR4": "comet-tfs:AR4", "AR5": "comet-tfs:AR5", "AR6": "comet-tfs:AR6",
    "unspecified": "comet-tfs:CF_Unspecified",
}

_CROSS_SECTORAL: dict[str, str] = {
    "ISO 14067": "comet-tfs:Std_ISO14067",
    "Pathfinder v1": "comet-tfs:Std_PathfinderV1",
    "Pathfinder v2": "comet-tfs:Std_PathfinderV2",
    "Pathfinder v3": "comet-tfs:Std_PathfinderV3",
    "GHG Protocol Product": "comet-tfs:Std_GHGProtocolProduct",
    "PAS 2050": "comet-tfs:Std_PAS2050",
    "ISO 14040-44": "comet-tfs:Std_ISO14040_44",
    "PEF": "comet-tfs:Std_PEF",
    "Other": "comet-tfs:Std_Other",
}

_SECTOR_RULE: dict[str, str] = {
    "TfS PCF Guideline V3.0": "comet-tfs:Rule_TfSGuidelineV3",
    "Catena-X Rulebook": "comet-tfs:Rule_CatenaX",
    "EN 50693": "comet-tfs:Rule_EN50693",
    "EN 15804": "comet-tfs:Rule_EN15804",
    "BPX 30-323": "comet-tfs:Rule_BPX30323",
    "Not specified": "comet-tfs:Rule_NotSpecified",
}

_MB_APPROACH: dict[str, str] = {
    "Conventional reference": "comet-tfs:MB_ConventionalReference",
    "Inventory": "comet-tfs:MB_Inventory",
    "both Conventional reference & Inventory": "comet-tfs:MB_Both",
}

_WI_ALLOCATION: dict[str, str] = {
    "cut-off": "comet-tfs:WI_CutOff",
    "reverse cut-off": "comet-tfs:WI_ReverseCutOff",
    "system expansion": "comet-tfs:WI_SystemExpansion",
    "not-applicable": "comet-tfs:WI_NotApplicable",
}

_RC_ALLOCATION: dict[str, str] = {
    "upstream system expansion": "comet-tfs:RC_UpstreamSystemExpansion",
    "cut-off": "comet-tfs:RC_CutOff",
}

_CCU_APPROACH: dict[str, str] = {
    "not-applicable": "comet-tfs:CCU_NotApplicable",
    "cut-off method": "comet-tfs:CCU_CutOffMethod",
    "credit method": "comet-tfs:CCU_CreditMethod",
}

_RECYCLED_CONTENT: dict[str, str] = {
    "post-industrial": "comet-tfs:PostIndustrial",
    "post-consumer": "comet-tfs:PostConsumer",
}

_ATTESTATION_TYPE: dict[str, str] = {
    "PCF Program Certification": "comet-tfs:AT_ProgramCertification",
    "PCF 3rd party verification": "comet-tfs:AT_ThirdParty",
    "PCF 2nd party verification": "comet-tfs:AT_SecondParty",
    "PCF 1st party verification": "comet-tfs:AT_FirstParty",
    "Mass balance certificate": "comet-tfs:AT_MassBalanceCertificate",
}

# TfS life-cycle-stage container key → comet-tfs:LifeCycleStage NamedIndividual
_STAGE_INDIVIDUAL: dict[str, str] = {
    "productionStage": "comet-tfs:ProductionStage",
    "packaging": "comet-tfs:PackagingStage",
    "distributionStage": "comet-tfs:DistributionStage",
}

# The A–H position + T1/T2 total datatype properties of a GWP breakdown.
# TfS technical field name → comet-tfs datatype property (skos:notation match).
_GWP_POSITIONS: dict[str, str] = {
    "pcfIncludingBiogenicUptake":          "comet-tfs:pcfIncludingBiogenicUptake",   # T1
    "pcfExcludingBiogenicUptake":          "comet-tfs:pcfExcludingBiogenicUptake",   # T2
    "fossilGhgEmissions":                  "comet-tfs:fossilGhgEmissions",           # A
    "technologicalCO2Removals":            "comet-tfs:technologicalCO2Removals",     # B
    "landManagementFossilGhgEmissions":    "comet-tfs:landManagementFossilGhgEmissions",  # A1
    "biogenicNonCO2Emissions":             "comet-tfs:biogenicNonCO2Emissions",      # C
    "biogenicCO2Uptake":                   "comet-tfs:biogenicCO2Uptake",            # D
    "landUseChangeGhgEmissions":           "comet-tfs:landUseChangeGhgEmissions",    # E
    "landManagementBiogenicCO2Emissions":  "comet-tfs:landManagementBiogenicCO2Emissions",  # F
    "landManagementBiogenicCO2Removals":   "comet-tfs:landManagementBiogenicCO2Removals",   # G
    "aircraftGhgEmissions":                "comet-tfs:aircraftGhgEmissions",         # H
}

# Carbon-content breakdown datatype properties (kg C per declared unit).
_CARBON_CONTENT: dict[str, str] = {
    "carbonContentTotal":            "comet-tfs:carbonContentTotal",
    "fossilCarbonContent":           "comet-tfs:fossilCarbonContent",
    "biogenicCarbonContent":         "comet-tfs:biogenicCarbonContent",
    "packagingBiogenicCarbonContent": "comet-tfs:packagingBiogenicCarbonContent",
    "recycledCarbonContent":         "comet-tfs:recycledCarbonContent",
    "ccuCarbonContent":              "comet-tfs:ccuCarbonContent",
}

# Data-quality-rating datatype properties (PDS + three DQR axes).
_DQR: dict[str, str] = {
    "primaryDataShare":              "comet-tfs:primaryDataShare",
    "secondaryEmissionFactorSources": "comet-tfs:secondaryEmissionFactorSources",
    "technologicalDQR":              "comet-tfs:technologicalDQR",
    "temporalDQR":                   "comet-tfs:temporalDQR",
    "geographicalDQR":               "comet-tfs:geographicalDQR",
}

# Verification-share datatype properties (PCS / 3PVS / 2PVS / 1PVS).
_VERIFICATION_SHARE: dict[str, str] = {
    "programCertificationShare":       "comet-tfs:programCertificationShare",
    "productVerificationShare3rdParty": "comet-tfs:productVerificationShare3rdParty",
    "productVerificationShare2ndParty": "comet-tfs:productVerificationShare2ndParty",
    "productVerificationShare1stParty": "comet-tfs:productVerificationShare1stParty",
}

# Attestation-of-conformance datatype fields (per array entry).
_ATTESTATION_FIELDS: dict[str, str] = {
    "standardName":                "comet-tfs:standardName",
    "attestationStandard":         "comet-tfs:attestationStandard",
    "attestationOfConformanceId":  "comet-tfs:attestationOfConformanceId",
    "attestationOfConformanceLink": "comet-tfs:attestationOfConformanceLink",
    "providerName":                "comet-tfs:providerName",
    "providerID":                  "comet-tfs:providerID",
    "completedAt":                 "comet-tfs:completedAt",
}

# Scalar datatype fields whose domain is comet-tfs:TfSProductFootprint directly.
_TOP_LEVEL_SCALARS: dict[str, str] = {
    "specVersion":                     "comet-tfs:specVersion",
    "productMassPerDeclaredUnit":      "comet-tfs:productMassPerDeclaredUnit",
    "boundaryProcessesDescription":    "comet-tfs:boundaryProcessesDescription",
    "ccuCo2Origin":                    "comet-tfs:ccuCo2Origin",
    "ccsTechnologicalCO2CaptureIncluded": "comet-tfs:ccsBeccsApplied",
    "ccuCreditCertificateScheme":      "comet-tfs:ccuCreditCertificateScheme",
    "ccsTechnologicalCO2Capture":      "comet-tfs:ccsTechnologicalCO2Capture",
    "useCredit":                       "comet-tfs:useCredit",
    "useCreditCertificateScheme":      "comet-tfs:useCreditCertificateScheme",
    "packagingEmissionsIncluded":      "comet-tfs:packagingEmissionsIncluded",
    "comment":                         "comet-tfs:comment",
    "pcfLegalStatement":               "comet-tfs:pcfLegalStatement",
}


# ── Helpers ──────────────────────────────────────────────────────────

class _MissingSentinel:
    """Sentinel for a missing value (distinct from a present ``None``)."""

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "<MISSING>"


_MISSING = _MissingSentinel()


def _get(obj: dict[str, Any], key: str) -> Any:
    """Return ``obj[key]`` if present and not None, else ``_MISSING``."""
    val = obj.get(key, _MISSING)
    return _MISSING if val is None else val


def _individual(mapping: dict[str, str], value: str) -> dict[str, str]:
    """Map an enum *value* to a ``{"@id": CURIE}`` node, or fall back to a label.

    Unknown values (open value lists / free text) are preserved as an unmapped
    literal under ``rdfs:label`` so nothing is silently dropped.
    """
    curie = mapping.get(value)
    if curie is not None:
        return {"@id": curie}
    return {"rdfs:label": value}


def _collect(source: dict[str, Any], mapping: dict[str, str],
             node_type: str) -> dict[str, Any] | None:
    """Build a typed node from *source* using a field→property *mapping*.

    Returns ``None`` if no mapped field is present.
    """
    node: dict[str, Any] = {}
    for field, prop in mapping.items():
        val = _get(source, field)
        if val is not _MISSING:
            node[prop] = val
    if not node:
        return None
    return {"@type": node_type, **node}


# ── Sub-object builders ──────────────────────────────────────────────

def _build_organization(tfs: dict[str, Any]) -> dict[str, Any] | None:
    """TfS companyName / companyIds → comet:Organization (Section A.2)."""
    org: dict[str, Any] = {}
    name = _get(tfs, "companyName")
    ids = _get(tfs, "companyIds")
    if name is not _MISSING:
        org["comet:legalName"] = name
    if ids is not _MISSING:
        org["comet:identifier"] = ids
    if not org:
        return None
    return {"@type": "comet:Organization", **org}


def _build_product(tfs: dict[str, Any]) -> dict[str, Any] | None:
    """TfS productNameCompany / productIds / … → comet:Product (Section A.3)."""
    prod: dict[str, Any] = {}
    for field, prop in (
        ("productNameCompany", "comet:productName"),
        ("productDescription", "comet:description"),
        ("productIds", "comet:identifier"),
        ("productClassifications", "comet:classification"),
    ):
        val = _get(tfs, field)
        if val is not _MISSING:
            prod[prop] = val
    if not prod:
        return None
    return {"@type": "comet:Product", **prod}


def _build_declared_unit(tfs: dict[str, Any]) -> dict[str, Any] | None:
    """TfS declaredUnitOfMeasurement / declaredUnitAmount → comet-pcf declared unit."""
    unit: dict[str, Any] = {}
    uom = _get(tfs, "declaredUnitOfMeasurement")
    amount = _get(tfs, "declaredUnitAmount")
    if uom is not _MISSING:
        unit["comet-pcf:unitOfMeasurement"] = uom
    if amount is not _MISSING:
        unit["comet-pcf:amount"] = amount
    if not unit:
        return None
    return {"@type": "comet-pcf:DeclaredUnit", **unit}


def _build_geography(tfs: dict[str, Any]) -> dict[str, Any] | None:
    """TfS geography* → comet:GeographicScope (Section A.5)."""
    geo: dict[str, Any] = {}
    for field, prop in (
        ("geographyCountry", "comet:country"),
        ("geographyCountrySubdivision", "comet:countrySubdivision"),
        ("geographyRegionOrSubregion", "comet:region"),
    ):
        val = _get(tfs, field)
        if val is not _MISSING:
            geo[prop] = val
    if not geo:
        return None
    return {"@type": "comet:GeographicScope", **geo}


def _build_reference_period(tfs: dict[str, Any]) -> dict[str, Any] | None:
    """TfS reference / validity period fields → comet-pcf:ReferencePeriod (Section A.6)."""
    rp: dict[str, Any] = {}
    for field, prop in (
        ("referencePeriodStart", "comet-pcf:startDate"),
        ("referencePeriodEnd", "comet-pcf:endDate"),
        ("validityPeriodStart", "comet-pcf:validityStart"),
        ("validityPeriodEnd", "comet-pcf:validityEnd"),
        ("created", "comet-pcf:created"),
    ):
        val = _get(tfs, field)
        if val is not _MISSING:
            rp[prop] = val
    if not rp:
        return None
    return {"@type": "comet-pcf:ReferencePeriod", **rp}


def _build_cut_off(tfs: dict[str, Any]) -> dict[str, Any] | None:
    """TfS exemptedEmissions* → comet-tfs:CutOffRule (Section B.4)."""
    node: dict[str, Any] = {}
    pct = _get(tfs, "exemptedEmissionsPercent")
    desc = _get(tfs, "exemptedEmissionsDescription")
    if pct is not _MISSING:
        node["comet-tfs:exemptedEmissionsPercent"] = pct
    if desc is not _MISSING:
        node["comet-tfs:exemptedEmissionsDescription"] = desc
    if not node:
        return None
    return {"@type": "comet-tfs:CutOffRule", **node}


def _build_allocation(tfs: dict[str, Any]) -> dict[str, Any] | None:
    """TfS allocation* → comet-tfs:AllocationApproach (Section B.7)."""
    node: dict[str, Any] = {}
    desc = _get(tfs, "allocationRulesDescription")
    if desc is not _MISSING:
        node["comet-tfs:allocationRulesDescription"] = desc
    wi = _get(tfs, "allocationWasteIncineration")
    if wi is not _MISSING:
        node["comet-tfs:allocationWasteIncineration"] = _individual(_WI_ALLOCATION, wi)
    rc = _get(tfs, "allocationRecycledCarbon")
    if rc is not _MISSING:
        node["comet-tfs:allocationRecycledCarbon"] = _individual(_RC_ALLOCATION, rc)
    ccu = _get(tfs, "ccuCalculationApproach")
    if ccu is not _MISSING:
        node["comet-tfs:ccuCalculationApproach"] = _individual(_CCU_APPROACH, ccu)
    if not node:
        return None
    return {"@type": "comet-tfs:AllocationApproach", **node}


def _build_mass_balancing(tfs: dict[str, Any]) -> dict[str, Any] | None:
    """TfS mass-balancing block → comet-tfs:MassBalancing (Section B.8)."""
    node: dict[str, Any] = {}
    used = _get(tfs, "massBalancingUsed")
    if used is not _MISSING:
        node["comet-tfs:massBalancingUsed"] = used
    free = _get(tfs, "freeAttributionInMassBalancing")
    if free is not _MISSING:
        node["comet-tfs:freeAttributionInMassBalancing"] = free
    approach = _get(tfs, "massBalancingCalculationApproach")
    if approach is not _MISSING:
        node["comet-tfs:massBalancingCalculationApproach"] = _individual(_MB_APPROACH, approach)
    scheme = _get(tfs, "massBalancingCertificateScheme")
    if scheme is not _MISSING:
        node["comet-tfs:massBalancingCertificateScheme"] = scheme
    if not node:
        return None
    return {"@type": "comet-tfs:MassBalancing", **node}


def _build_life_cycle_stage(key: str, stage: dict[str, Any]) -> dict[str, Any]:
    """Build a comet-tfs:LifeCycleStage node with a nested GWP position breakdown."""
    breakdown = _collect(stage, _GWP_POSITIONS, "comet-tfs:GWPPositionBreakdown")
    node: dict[str, Any] = {
        "@type": "comet-tfs:LifeCycleStage",
        "comet-tfs:stageType": {"@id": _STAGE_INDIVIDUAL[key]},
    }
    if breakdown is not None:
        node["comet-tfs:hasGWPBreakdown"] = breakdown
    return node


def _build_attestation(entry: dict[str, Any]) -> dict[str, Any]:
    """Build one comet-tfs:AttestationOfConformance node (Section B.11)."""
    node: dict[str, Any] = {"@type": "comet-tfs:AttestationOfConformance"}
    atype = _get(entry, "AttestationType")
    if atype is not _MISSING:
        node["comet-tfs:attestationType"] = _individual(_ATTESTATION_TYPE, atype)
    for field, prop in _ATTESTATION_FIELDS.items():
        val = _get(entry, field)
        if val is not _MISSING:
            node[prop] = val
    return node


# ── Public API ───────────────────────────────────────────────────────

def convert(tfs: dict[str, Any]) -> dict[str, Any]:
    """Convert a TfS PCF Data Model v3.1 payload into a COMET JSON-LD object.

    Parameters
    ----------
    tfs : the parsed TfS v3.1 PCF payload (technical field names)

    Returns
    -------
    A COMET JSON-LD dict typed ``comet-tfs:TfSProductFootprint``.
    """
    node: dict[str, Any] = {"@type": COMET_TYPE}

    # Identity / lifecycle metadata (comet-pcf:PCFResult surface).
    pcf_id = _get(tfs, "id")
    if pcf_id is not _MISSING:
        node["@id"] = f"urn:tfs-initiative.com:pcf:{pcf_id}"
        node["comet-pcf:pcfId"] = pcf_id
    for field, prop in (
        ("version", "comet-pcf:version"),
        ("status", "comet-pcf:status"),
        ("precedingPfIds", "comet-pcf:precedingPcfIds"),
    ):
        val = _get(tfs, field)
        if val is not _MISSING:
            node[prop] = val

    # Boundary declaration (partial vs full).
    boundary = _get(tfs, "partialFullPcf")
    if boundary is not _MISSING:
        node["comet-tfs:hasBoundaryDeclaration"] = _individual(_BOUNDARY, boundary)

    # Characterization factor version.
    cf = _get(tfs, "characterizationFactors")
    if cf is not _MISSING:
        node["comet-tfs:usesCharacterizationFactor"] = _individual(_CHARACTERIZATION, cf)

    # Cross-sectoral standards (multi-select → array of individuals).
    standards = _get(tfs, "crossSectoralStandards")
    if standards is not _MISSING:
        values = standards if isinstance(standards, list) else [standards]
        node["comet-tfs:crossSectoralStandard"] = [
            _individual(_CROSS_SECTORAL, v) for v in values
        ]

    # Product / sector rule.
    rule = _get(tfs, "productOrSectorSpecificRules")
    if rule is not _MISSING:
        node["comet-tfs:productOrSectorRule"] = _individual(_SECTOR_RULE, rule)

    # Recycled-content type.
    rct = _get(tfs, "typeRecycledContent")
    if rct is not _MISSING:
        node["comet-tfs:typeRecycledContent"] = _individual(_RECYCLED_CONTENT, rct)

    # TfS positive-list references (free-text / URL strings).
    for field, prop in (
        ("tfsPositivelistPcrUsed", "comet-tfs:tfsPositivelistPcrUsed"),
        ("systemexpansionPositivelistUsed", "comet-tfs:systemexpansionPositivelistUsed"),
    ):
        val = _get(tfs, field)
        if val is not _MISSING:
            node[prop] = val

    # Top-level scalar datatype fields.
    for field, prop in _TOP_LEVEL_SCALARS.items():
        val = _get(tfs, field)
        if val is not _MISSING:
            node[prop] = val

    # Core MERGE targets (Section A): org / product / declared unit / geo / period.
    org = _build_organization(tfs)
    if org is not None:
        node["comet:organization"] = org
    product = _build_product(tfs)
    if product is not None:
        node["comet:product"] = product
    declared_unit = _build_declared_unit(tfs)
    if declared_unit is not None:
        node["comet-pcf:declaredUnit"] = declared_unit
    geography = _build_geography(tfs)
    if geography is not None:
        node["comet:geographicScope"] = geography
    reference_period = _build_reference_period(tfs)
    if reference_period is not None:
        node["comet-pcf:referencePeriod"] = reference_period

    # TfS EXPAND sub-objects.
    cut_off = _build_cut_off(tfs)
    if cut_off is not None:
        node["comet-tfs:hasCutOffRule"] = cut_off
    allocation = _build_allocation(tfs)
    if allocation is not None:
        node["comet-tfs:hasAllocation"] = allocation
    mass_balancing = _build_mass_balancing(tfs)
    if mass_balancing is not None:
        node["comet-tfs:hasMassBalancing"] = mass_balancing
    dqr = _collect(tfs, _DQR, "comet-tfs:DataQualityRating")
    if dqr is not None:
        node["comet-tfs:hasDataQualityRating"] = dqr
    vshare = _collect(tfs, _VERIFICATION_SHARE, "comet-tfs:VerificationShare")
    if vshare is not None:
        node["comet-tfs:hasVerificationShare"] = vshare

    # Life-cycle stages with A–H GWP position breakdowns.
    stages: list[dict[str, Any]] = []
    for key in ("productionStage", "packaging", "distributionStage"):
        stage = _get(tfs, key)
        if stage is not _MISSING and isinstance(stage, dict):
            stages.append(_build_life_cycle_stage(key, stage))
    if stages:
        node["comet-tfs:hasLifeCycleStage"] = stages

    # Carbon-content breakdown.
    carbon = _collect(tfs, _CARBON_CONTENT, "comet-tfs:CarbonContentBreakdown")
    if carbon is not None:
        node["comet-tfs:hasCarbonContent"] = carbon

    # Attestation of Conformance array.
    attestations = _get(tfs, "attestationOfConformance")
    if attestations is not _MISSING:
        entries = attestations if isinstance(attestations, list) else [attestations]
        node["comet-tfs:hasAttestation"] = [
            _build_attestation(e) for e in entries if isinstance(e, dict)
        ]

    return {"@context": COMET_CONTEXT, **node}


def convert_tfs_to_comet(json_path: str | Path) -> dict[str, Any]:
    """Read a TfS v3.1 JSON file and return the COMET JSON-LD object."""
    json_path = Path(json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")
    with json_path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("Expected a single TfS PCF ProductFootprint JSON object")
    return convert(data)


# ── CLI ──────────────────────────────────────────────────────────────

_DEFAULT_INPUT = Path("tools/examples/tfs-v3-input.json")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a TfS PCF Data Model v3.1 JSON payload to COMET JSON-LD.",
        epilog=(
            "Examples:\n"
            "  python tfs_to_comet.py tools/examples/tfs-v3-input.json\n"
            "  python tfs_to_comet.py input.json --output comet.json\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        default=_DEFAULT_INPUT,
        help=f"Path to the TfS v3.1 JSON file (default: {_DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output file (default: stdout)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        doc = convert_tfs_to_comet(args.input)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
