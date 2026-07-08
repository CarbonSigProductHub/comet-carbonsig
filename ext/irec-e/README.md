# COMET Extension: I-REC(E)

**Module:** `comet-ext:irec-e`
**Namespace:** `https://comet.carbon/ext/irec-e#`
**Prefix:** `comet-irec:`
**Version:** 0.1.0
**Status:** RFC Open
**License:** CC BY 4.0 + Apache 2.0

## Summary

Maps the data model of the **Evident I-REC Code for Electricity v1.13**
(Document ID EC-I-REC(E), 12 June 2025) and its subsidiary **Standard Forms** —
**SF-02 Production Facility Registration v1.3** (+A/B/C) and **SF-04 Issue
Request v1.2** (+A/B/C) — onto the COMET seven-layer stack.

The Code defines its schema semantically (Definitions + "Required Information"
clauses) and delegates the column-level layouts to the SF-xx forms. This module
captures both.

### Reuse first

An I-REC(E) certificate **is** a COMET Energy Attribute Certificate. The module
adds only the I-REC-specific machinery that has no prior COMET home; everything
else points at an existing term (see `alignments/comet-irec-evident-alignment.ttl`):

| I-REC(E) concept | Reused COMET term |
|---|---|
| Entity / Registrant / Participant / Owner | `comet:Organization` |
| Production Facility / Device / Installation | `comet:Site` |
| Production Period | `comet:TimePeriod` |
| I-REC(E) certificate | `comet-eac:EnergyAttributeCert` / `comet-eac:EAC` (subType `IREC`) |
| Serial / issue date / volume (MWh) / vintage / status | `comet-eac:EAC.serialNumber` / `.issueDate` / `.unitCount` / `.vintageYear` / `.unitStatus` |
| Registry (Evident) | `comet-eac:CertificateRegistry` |
| Redemption (cancel-to-claim) | `comet-eac:RetirementEvent` |
| Book-and-claim custody | `comet-eac:BookAndClaim` |
| Verification Agent / Production Auditor | `comet-ver:QualifiedVerifier` |

`IREC`, `GuaranteeOfOrigin`, `REC` and `TIGR` were already enumerated as EAC
subtypes in `tools/schemas/comet-eac.schema.json` — this module gives the I-REC
lifecycle first-class OWL identity behind that flag.

### New terms (84)

| Group | New classes |
|---|---|
| L1 Core | `Registrant`, `Participant`, `Account`, `ProductionFacility`, `ProductionGroup`, `ProductionInstallation`, `LabellingScheme`, `StandardForm` |
| L5 EAC | `IRECCertificate`, `IssueRequest`, `RedemptionStatement`, `FuelConsumptionStatement`, `FuelInputRecord`, `ProductionAuditor`, `VerificationAgent` |
| L6 Verification | `Declaration`, `RegistrantDeclaration`, `OwnerDeclaration`, `IssuingDeclaration` |

Plus 18 object properties, 34 data properties, and the 12 named Standard-Form
individuals (`SF-02` … `SF-07`).

## The multi-fuel (co-firing) case

For a mixed-fuel generator, only the renewable portion of electricity is
I-REC(E)-eligible. SF-04C allocates it per fuel:

```
Fuel Consumed  (kg) = StockStart + StockAdded - StockEnd      # b + c - d
Energy from Source (MJ) = GrossCalorificValue × FuelConsumed  # a × (b + c - d)
renewable share = Σ energy(renewable) / Σ energy(all)
eligible MWh    = totalProductionMWh × renewable share
```

Both equalities are enforced as SHACL SPARQL constraints
(`comet-ext-irec-e-shapes.ttl`) and implemented in the converter.

## Files

| File | Description |
|---|---|
| `comet-ext-irec-e.ttl` | OWL ontology (19 classes, 18 object props, 34 data props, 12 individuals) |
| `comet-ext-irec-e-shapes.ttl` | SHACL shapes (enums, cardinality, SF-04C arithmetic, applied ≤ produced) |
| `alignments/comet-irec-evident-alignment.ttl` | Reuse bridges to `comet-eac`/`comet`/`comet-ver` + SF provenance |
| `examples/irec-e-certificate.comet.json` | JSON-LD certificate (validates against `comet-eac.schema.json`) |
| `tests/data/example-irec-valid.ttl` | Worked 45 MW biomass+coal co-firing plant (Conforms: True) |
| `tests/data/example-irec-invalid.ttl` | Negative test (Conforms: False) |
| `../../tools/converters/irec_to_comet.py` | SF-04 record → COMET JSON-LD converter |
| `../../tools/examples/irec-input.json` | Sample converter input |

## Usage

```bash
# Convert an SF-04-shaped Issue Request record to COMET JSON-LD
python tools/comet_cli.py convert tools/examples/irec-input.json --from irec --to comet --pretty

# Validate instance data against the shapes
pyshacl -s ext/irec-e/comet-ext-irec-e-shapes.ttl -d ext/irec-e/tests/data/example-irec-valid.ttl

# Run the converter + registry-consistency tests
python tools/converters/tests/test_irec_converter.py
```

## Standards references

- Evident I-REC Code for Electricity v1.13 (EC-I-REC(E), 12 Jun 2025)
- SF-02 Production Facility Registration v1.3 (+A Registrant's / B Production Group / C Owner's)
- SF-04 Issue Request v1.2 (+A Issuing Declaration / B Production Group Statement / C Fuel Consumption Statement)
- SD-02 Technologies and Fuels (technology/fuel code lists)

## Known gaps

- **Technology/fuel codes** are typed as strings referencing SD-02 rather than
  enumerated; SD-02 is a controlled list maintained by Evident and versioned
  separately.
- **Certificate serial-number mask** and **registry API field names/types** are
  defined by the Evident Registry platform, not the Code prose; modelled as
  `comet-eac:EAC.serialNumber` (opaque string) here.

## See also

- [COMET Extension Cookbook](../../docs/creating-extensions.md)
- [comet-eac schema](../../tools/schemas/comet-eac.schema.json)
- [ADR-003 Extension module pattern](../../docs/adr/ADR-003-extension-module-pattern.md)
