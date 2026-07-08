#!/usr/bin/env python3
"""Convert an Evident I-REC(E) Issue Request / certificate record to COMET JSON-LD.

FULL (v0.4.0): implements the Evident I-REC Code for Electricity v1.13 data model
as expressed by the COMET ``comet-irec`` extension, reusing ``comet-eac`` for the
certificate body. Accepts a JSON record shaped like an SF-04 Issue Request
(see tools/examples/irec-input.json) and, for multi-fuel generators, computes the
renewable-eligible MWh from the SF-04C per-fuel calorific allocation:

    fuelConsumed   = stockStart + stockAdded - stockEnd          # b + c - d
    energyFromSrc  = grossCalorificValue * fuelConsumed          # a * (b+c-d)
    renewableShare = sum(energyFromSrc where renewable) / sum(all energyFromSrc)
    eligibleMWh    = totalProductionMWh * renewableShare

Target COMET classes (reuse-first):
    comet-eac:EnergyAttributeCert   (via subType "IREC")   <- the certificate
    comet-eac:CertificateRegistry                          <- Evident/I-REC registry
    comet-eac:RetirementEvent                              <- redemption
    comet-irec:ProductionFacility (comet:Site)             <- SF-02 facility
    comet-irec:IssueRequest / FuelConsumptionStatement     <- SF-04 / SF-04C
    comet-irec:RedemptionStatement                         <- Code s.10

Usage:
    python irec_to_comet.py issue_request.json
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

COMET_CONTEXT = ["https://comet.carbon/v1/jsonld/context.json",
                 "https://comet.carbon/ext/irec-e#"]
COMET_TYPE = "comet-eac:EnergyAttributeCertificate"

_REQUEST_TYPES = {"normal": "Normal", "self consumption": "SelfConsumption",
                  "self-consumption": "SelfConsumption", "selfconsumption": "SelfConsumption"}
_EVIDENCE = {"settlement metering data": "SettlementMetering",
             "settlement": "SettlementMetering",
             "non-settlement metering data": "NonSettlementMetering",
             "non-settlement": "NonSettlementMetering",
             "measured volume transfer documentation": "MeasuredVolumeTransfer",
             "measured volume transfer": "MeasuredVolumeTransfer"}


def _num(x: Any) -> float | None:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def allocate_renewable_share(fuels: list[dict[str, Any]]) -> tuple[float | None, list[dict[str, Any]]]:
    """Apply the SF-04C co-firing allocation. Returns (renewable_share, enriched_rows).

    renewable_share is None when there is no fuel data (single-fuel / fully renewable
    plants need no allocation and get share 1.0 handled by the caller).
    """
    if not fuels:
        return None, []
    rows: list[dict[str, Any]] = []
    total_energy = 0.0
    renewable_energy = 0.0
    for f in fuels:
        a = _num(f.get("grossCalorificValueMJkg"))
        b = _num(f.get("stockBalanceStartKg"))
        c = _num(f.get("stockAddedKg"))
        d = _num(f.get("stockBalanceEndKg"))
        if None in (a, b, c, d):
            raise ValueError(
                "Each fuel row needs grossCalorificValueMJkg, stockBalanceStartKg, "
                "stockAddedKg, stockBalanceEndKg (SF-04C)."
            )
        consumed = b + c - d
        energy = a * consumed
        is_ren = bool(f.get("isRenewableSource", False))
        total_energy += energy
        if is_ren:
            renewable_energy += energy
        rows.append({
            "@type": "comet-irec:FuelInputRecord",
            "fuelCode": f.get("fuelCode"),
            "isRenewableSource": is_ren,
            "grossCalorificValueMJkg": a,
            "stockBalanceStartKg": b,
            "stockAddedKg": c,
            "stockBalanceEndKg": d,
            "fuelConsumedKg": round(consumed, 6),
            "energyFromSourceMJ": round(energy, 6),
        })
    share = (renewable_energy / total_energy) if total_energy > 0 else 0.0
    return share, rows


def convert_irec_to_comet(input_path: str | Path) -> dict[str, Any]:
    """Convert an SF-04-shaped I-REC(E) JSON record into a COMET JSON-LD document."""
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"I-REC record file not found: {input_path}")
    if input_path.suffix.lower() != ".json":
        raise ValueError("irec_to_comet expects a JSON Issue Request record.")

    rec = json.loads(input_path.read_text(encoding="utf-8"))
    fac = rec.get("facility", {}) or {}
    period = rec.get("period", {}) or {}
    fuels = rec.get("fuels", []) or []
    redemption = rec.get("redemption") or None

    total_mwh = _num(rec.get("totalProductionMWh"))
    share, fuel_rows = allocate_renewable_share(fuels)
    if share is None:
        # single-fuel / fully renewable: eligible = applied-for or total
        eligible = _num(rec.get("amountAppliedForMWh")) or total_mwh
    else:
        eligible = round((total_mwh or 0.0) * share, 6)

    doc: dict[str, Any] = {
        "@context": COMET_CONTEXT,
        "@type": COMET_TYPE,
        "eacId": rec.get("eacId") or f"urn:uuid:{uuid.uuid4()}",
        "eacType": "EnergyAttributeCertificate",
        "subType": "IREC",
        "unit": "MWh",
        "quantity": eligible,
    }

    if rec.get("serialNumber"):
        doc["serialNumber"] = rec["serialNumber"]
    if rec.get("issueDate"):
        doc["issueDate"] = rec["issueDate"]
    if rec.get("status"):
        doc["status"] = rec["status"]

    # Registry (reuse comet-eac:CertificateRegistry)
    doc["registry"] = {
        "@type": "comet-eac:CertificateRegistry",
        "registryName": rec.get("registryName", "I-REC"),
        "programName": rec.get("programName", "Evident I-REC Standard for Electricity"),
        "registryURI": rec.get("registryURI", "https://evident.global/"),
    }

    # Production period (reuse comet:TimePeriod)
    if period:
        doc["vintage"] = {
            "@type": "comet:TimePeriod",
            "startDate": period.get("startDate"),
            "endDate": period.get("endDate"),
        }

    # Production facility (comet-irec:ProductionFacility / comet:Site)
    if fac:
        pf = {"@type": "comet-irec:ProductionFacility"}
        for src, dst in [
            ("name", "siteName"), ("country", "siteCountry"), ("gis", "siteGIS"),
        ]:
            if fac.get(src) is not None:
                pf[dst] = fac[src]
        for k in ("installedCapacityMW", "numberOfGeneratingUnits", "commissioningDate",
                  "effectiveRegistrationDate", "meterId", "technologyCode", "fuelCode",
                  "gridConnectionVoltage", "networkOwner", "publicFundingType"):
            if fac.get(k) is not None:
                pf[k] = fac[k]
        doc["productionFacility"] = pf

    # Issue request (comet-irec:IssueRequest / SF-04)
    ir: dict[str, Any] = {"@type": "comet-irec:IssueRequest", "definedByForm": "comet-irec:SF-04"}
    rt = (rec.get("requestType") or "Normal").strip().lower()
    ir["requestType"] = _REQUEST_TYPES.get(rt, "Normal")
    if total_mwh is not None:
        ir["totalProductionMWh"] = total_mwh
    if rec.get("amountAppliedForMWh") is not None:
        ir["amountAppliedForMWh"] = _num(rec["amountAppliedForMWh"])
    else:
        ir["amountAppliedForMWh"] = eligible
    ev = (rec.get("evidenceType") or "").strip().lower()
    if ev:
        ir["evidenceType"] = _EVIDENCE.get(ev, rec["evidenceType"])
    doc["issueRequest"] = ir

    # Fuel consumption statement (SF-04C) — only for multi-fuel generators
    if fuel_rows:
        doc["fuelConsumptionStatement"] = {
            "@type": "comet-irec:FuelConsumptionStatement",
            "definedByForm": "comet-irec:SF-04C",
            "renewableShare": round(share, 6),
            "hasFuelInput": fuel_rows,
        }

    if rec.get("chainOfCustodyReference"):
        doc["chainOfCustodyReference"] = rec["chainOfCustodyReference"]
    if rec.get("carbonOffsetRightsExcluded") is not None:
        doc["carbonOffsetRightsExcluded"] = bool(rec["carbonOffsetRightsExcluded"])

    # Redemption (reuse comet-eac:RetirementEvent + comet-irec:RedemptionStatement)
    if redemption:
        doc["retirementInfo"] = {
            "@type": "comet-eac:RetirementEvent",
            "retiredDate": redemption.get("retiredDate"),
            "beneficiary": redemption.get("beneficiary"),
            "purpose": redemption.get("purpose"),
        }
        rs = {"@type": "comet-irec:RedemptionStatement"}
        for k in ("qrCode", "verificationKey", "redemptionPurpose"):
            if redemption.get(k) is not None:
                rs[k] = redemption[k]
        if len(rs) > 1:
            doc["redemptionStatement"] = rs
        doc["status"] = doc.get("status", "retired")

    return doc


def convert(input_path: str) -> dict[str, Any]:
    """Bridge for comet_cli.py."""
    return convert_irec_to_comet(input_path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert an Evident I-REC(E) Issue Request record to COMET JSON-LD.",
    )
    parser.add_argument("input", type=Path, help="Path to the SF-04-shaped Issue Request JSON file")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output file (default: stdout)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        doc = convert_irec_to_comet(args.input)
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
