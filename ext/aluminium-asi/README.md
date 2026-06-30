# COMET ASI Aluminium Extension (`comet-asi`)

**Status:** RFC Open (pending) · **Version:** 0.1.0 · **Namespace:** `https://comet.carbon/ext/aluminium-asi#`

Maps the aluminium-specific working variables of the **ASI Performance Standard V3**
(Principle 5 — GHG Emissions, Criteria 5.1–5.4) and the **ASI Chain of Custody
Standard V2 (2022)** onto the COMET seven-layer stack.

## Why this extension

ASI-certified producers already collect most of the GHG data CBAM, EPDs, and
Scope-3 customers ask for. The gap is **format and a handful of
aluminium-specific variables with no existing COMET home** — not data collection.
This extension types only those gaps; everything that already has a COMET class
(Scope 1/2/3, embedded emissions, verifier identity, site) is **reused**, not
duplicated.

## What's new here (the gaps COMET didn't cover)

| Class | Covers | ASI ref |
|---|---|---|
| `comet-asi:PFCAnodeEffect` | CF4 / C2F6 anode-effect emissions (high-GWP, aluminium-only) | PS Cr 5.1 |
| `comet-asi:GHGPathway` · `:SectoralSlope` | Decarbonisation trajectory & IAI 1.5°C slope | PS Cr 5.2 |
| `comet-asi:SmelterThreshold` | Cr 5.2 smelter GHG-threshold conformance | PS Cr 5.2 |
| `comet-asi:CoCModel` · `:CoCClaim` · `:MassBalanceAccount` · `:CoCTransferEvent` | ASI Chain of Custody (mass balance / segregation) | CoC V2 |
| `comet-asi:ASICertification` · `:ASICertifiedSite` · `:ASICertifiedEntity` | Certificate, site, entity identity | CoC V2 / Assurance |

These correspond 1:1 to the items the CarbonSig **PCR Rule Builder** flags as
"new module" when an ASI scheme has no COMET class to map to.

## Reused from core COMET (not redefined)

`comet-sc:Scope1Emissions` · `comet-sc:Scope2Emissions` · `comet-sc:Scope3Emissions`
· `comet-pcf:EmbeddedEmissions` · `comet-pcf:ProductCarbonFootprint.fossilGWP`
· `comet-sc:PrimaryDataShare` · `comet-sc:DataQualityIndicator`
· `comet-ver:QualifiedVerifier` · `comet-ver:AssuranceLevel` · `comet:Site`.

## Files

- `comet-ext-aluminium-asi.ttl` — the ontology (OWL classes + properties).
- `comet-ext-aluminium-asi-shapes.ttl` — SHACL validation shapes.
- `alignments/comet-cbam-alignment.ttl` — ASI → COMET → EU CBAM (CN 76) mapping.
- `tests/data/example-south32-coc.ttl` — worked example: the real South32 Worsley
  Alumina ASI CoC Certificate 409.

## Validate

```bash
python -c "from rdflib import Graph; Graph().parse('comet-ext-aluminium-asi.ttl',format='turtle')"
pyshacl -s comet-ext-aluminium-asi-shapes.ttl -d tests/data/example-south32-coc.ttl
```

After adding this extension, regenerate the CURIE registry:

```bash
python tools/build_registry.py   # harvests comet-asi into the comet_asi_pending allow-list
```

## Sources

- ASI Performance Standard V3 (Principle 5, Criteria 5.1–5.4)
- ASI Chain of Custody Standard V2 (2022)
- ASI Entity GHG Pathways Calculation Tool
- ASI → COMET → CBAM field-level translation

## License

CC BY 4.0 (data) + Apache 2.0 (code).
