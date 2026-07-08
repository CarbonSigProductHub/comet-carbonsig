#!/usr/bin/env python3
"""Tests for the Evident I-REC(E) -> COMET converter and extension registration.

Run:
    python tools/converters/tests/test_irec_converter.py

Exits non-zero on first failure. Stdlib only for the converter checks; the
registry-consistency check uses the shared registry JSON.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve()
CONV_DIR = HERE.parents[1]
ROOT = HERE.parents[3]
sys.path.insert(0, str(CONV_DIR))

import irec_to_comet as irec  # noqa: E402

_fails = 0


def check(cond: bool, msg: str) -> None:
    global _fails
    if not cond:
        _fails += 1
    print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")


def _write(tmp: Path, name: str, obj) -> Path:
    p = tmp / name
    p.write_text(json.dumps(obj), encoding="utf-8")
    return p


def test_cofiring_allocation(tmp: Path) -> None:
    print("SF-04C co-firing allocation:")
    rec = {
        "totalProductionMWh": 5000.0,
        "requestType": "Normal",
        "evidenceType": "Settlement Metering data",
        "period": {"startDate": "2025-06-01", "endDate": "2025-06-30"},
        "fuels": [
            {"fuelCode": "ES200", "isRenewableSource": True,
             "grossCalorificValueMJkg": 15.0, "stockBalanceStartKg": 500000.0,
             "stockAddedKg": 8200000.0, "stockBalanceEndKg": 700000.0},
            {"fuelCode": "FF100", "isRenewableSource": False,
             "grossCalorificValueMJkg": 27.0, "stockBalanceStartKg": 300000.0,
             "stockAddedKg": 1000000.0, "stockBalanceEndKg": 300000.0},
        ],
    }
    doc = irec.convert(str(_write(tmp, "ir.json", rec)))
    fcs = doc["fuelConsumptionStatement"]
    rows = {r["fuelCode"]: r for r in fcs["hasFuelInput"]}
    # Fuel Consumed = b + c - d
    check(rows["ES200"]["fuelConsumedKg"] == 8000000.0, "biomass consumed = b + c - d")
    check(rows["FF100"]["fuelConsumedKg"] == 1000000.0, "coal consumed = b + c - d")
    # Energy = a * consumed
    check(rows["ES200"]["energyFromSourceMJ"] == 120000000.0, "biomass energy = a * consumed")
    check(rows["FF100"]["energyFromSourceMJ"] == 27000000.0, "coal energy = a * consumed")
    # renewable share and eligible MWh
    check(abs(fcs["renewableShare"] - 0.816327) < 1e-5, "renewable share ~= 0.816327")
    check(abs(doc["quantity"] - 4081.632653) < 1e-3, "eligible MWh ~= 4081.63")
    check(doc["subType"] == "IREC" and doc["unit"] == "MWh", "reuses comet-eac subType IREC, unit MWh")
    check(doc["@type"] == "comet-eac:EnergyAttributeCertificate", "reuses comet-eac certificate type")


def test_single_fuel(tmp: Path) -> None:
    print("Single-fuel (no SF-04C) path:")
    rec = {"totalProductionMWh": 1000.0, "amountAppliedForMWh": 1000.0,
           "facility": {"name": "Solar Farm", "country": "TH", "technologyCode": "TC110"}}
    doc = irec.convert(str(_write(tmp, "solar.json", rec)))
    check(doc["quantity"] == 1000.0, "fully renewable eligible = total")
    check("fuelConsumptionStatement" not in doc, "no fuel statement for single-fuel plant")


def test_registry_consistency() -> None:
    print("Registry / TTL consistency:")
    reg = json.loads((ROOT / "registry" / "comet-curies.json").read_text())
    pending = set(reg.get("comet_irec_pending", []))
    check(len(pending) > 0, "comet_irec_pending is populated")
    check("comet-irec" in reg["namespaces"], "comet-irec namespace registered")
    ttl = (ROOT / "ext" / "irec-e" / "comet-ext-irec-e.ttl").read_text()
    for curie in pending:
        check(f"{curie} " in ttl or f"{curie}\n" in ttl, f"registry term defined in TTL: {curie}")
    # counts stay internally consistent
    pend_total = sum(v for k, v in reg["counts"].items()
                     if k.endswith("_pending") and isinstance(v, int))
    check(reg["counts"]["total"] == reg["counts"]["comet_published"] + pend_total,
          "counts.total == published + all pending")


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        test_cofiring_allocation(tmp)
        test_single_fuel(tmp)
    test_registry_consistency()
    print(f"\n{'ALL PASS' if not _fails else str(_fails) + ' FAILED'}")
    return 0 if not _fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
