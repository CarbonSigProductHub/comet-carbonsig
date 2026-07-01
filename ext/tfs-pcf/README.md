# COMET Extension: TfS PCF Data Model v3.1

**Module:** `comet-ext:tfs-pcf`
**Namespace:** `https://comet.carbon/ext/tfs-pcf#`
**Prefix:** `comet-tfs:`
**Version:** 0.1.0
**Status:** RFC Open (pending)
**License:** CC BY 4.0 + Apache 2.0
**Standard:** TfS PCF Data Model v3.1 (September 2025) — the data aspect model of the *Together for Sustainability Product Carbon Footprint Guideline for the Chemical Industry*

---

## 1. What the TfS PCF Data Model actually is

The TfS PCF Data Model v3.1 is the *data aspect model* — the "how to report PCF data" companion — of the Together for Sustainability (TfS) Product Carbon Footprint Guideline for the Chemical Industry. Where the Guideline tells a chemical company *how to calculate* a cradle-to-gate product carbon footprint, the Data Model specifies exactly *which 131 fields* that footprint must be transmitted in, so that a supplier and a customer exchanging a PCF are talking about the same 131 quantities with the same units, the same sign conventions, and the same conditionality rules. It supersedes TfS PCF Data Model v3.0.

The Data Model is technically aligned to the WBCSD PACT Pathfinder Framework v3.0 (the cross-industry emission taxonomy and data exchange spec), so a TfS-conformant record is also a PACT-conformant record. It is the payload carried by the **TfS PCF Data Exchange Platform**, the industry hub through which chemical suppliers publish PCFs to their downstream customers.

Every one of the 131 fields carries a **field discipline** flag that governs when it must be present:

| Flag | Meaning |
|---|---|
| **M** | **Mandatory** — must always be populated in a conformant record |
| **O** | **Optional** — populated at the data owner's discretion |
| **D** | **Default** — a prefilled value applies unless overridden (e.g. characterization factors default to AR6, boundary defaults to cradle-to-gate) |
| **R** | **Required-under-condition** — mandatory *only if* a trigger field is set (e.g. `massBalancingCalculationApproach` is required only when `massBalancingUsed = TRUE`) |
| **M202X** | **Phased-in mandatory** — currently optional but becomes Mandatory from a stated year. The v3.1 phase-in year is **M2027**: Primary Data Share, the three DQR axes, and Positions A, E, F of the GWP breakdown become mandatory in 2027 |

This M/O/D/R discipline is why the Data Model cannot be captured as a flat property bag: the conditionality (R) and the phase-in (M202X) are semantics that a downstream consumer must reason over, not just store.

## 2. Where COMET already covers TfS (MERGE)

Twelve TfS concepts already have a home in a COMET core layer. Section A of the ontology asserts these as `owl:equivalentClass` / `skos:closeMatch` alignments so a reasoner can move data between the TfS Data Model and COMET without lossy conversion. The TfS technical field name is recorded in `skos:notation` for round-tripping with the TfS Data Exchange Platform. **No new class is minted here — only the bridge.**

| TfS field(s) | Existing COMET class | Notes |
|---|---|---|
| `Id`, `precedingPfIds`, `version`, `status` | `comet-pcf:PCFResult` | The PCF record itself. Close match to both `tfs:ProductFootprint` and `pact:ProductFootprint`. The TfS profile is typed as `comet-tfs:TfSProductFootprint` (§3) |
| `companyName`, `companyIds` | `comet:Organization` | The Product Footprint Data Owner. TfS company IDs use the URN:FPI scheme (org-id, DUNS, VAT, LEI) |
| `productNameCompany`, `productIds`, `productClassifications`, `productDescription` | `comet:Product` | TfS product IDs/classifications use URN:FPI (GTIN, CAS number, UN CPC, CN code) |
| `declaredUnitOfMeasurement`, `declaredUnitAmount` | `comet-pcf:DeclaredUnit` | Constrained value list added as `comet-tfs:DeclaredUnitOfMeasurement` |
| `geographyCountry`, `geographyCountrySubdivision`, `geographyRegionOrSubregion` | `comet:GeographicScope` | ISO 3166-1/-2; region value list added as `comet-tfs:GeographyRegionOrSubregion` |
| `referencePeriodStart/End`, `validityPeriodStart/End`, `created` | `comet-pcf:ReferencePeriod` | ISO 8601 UTC. TfS caps validity at three years after reference-period end |
| `pcfIncludingBiogenicUptake` (T1), `pcfExcludingBiogenicUptake` (T2) | `comet-pcf:GlobalWarmingPotential` | kg CO2e per declared unit. Stage-level A–H decomposition added as `comet-tfs:GWPPositionBreakdown` |
| `fossilGhgEmissions` (Position A) | `comet-pcf:FossilGHGEmission` | Fossil component. Biogenic/land-use positions carry extra sign semantics → §3 |
| `TechnologicalCO2Removals` (B), `biogenicCO2Uptake` (D) | `comet-pcf:GHGRemoval` | Negative-contribution positions (≤ 0 kg CO2e) |
| `crossSectoralStandards` | `comet-pcf:MethodologyStandard` | Value list added as `comet-tfs:CrossSectoralStandard` |
| `providerName`, `providerID` | `comet-ver:VerificationBody` | The attestation issuer's legal entity + Business Partner Number |
| `attestationOfConformance` (as assurance statement) | `comet-ver:AuditClaim` | The attestation *object* is typed as `comet-tfs:AttestationOfConformance` (§3) |

**Implication:** the identity, unit, geography, period, GWP-total, and verifier-identity fields of a TfS record are implementable on a stock COMET dataset before a single extension class loads. The merge alone makes an existing COMET PCF partially TfS-readable.

## 3. Where TfS forces COMET to expand (NEW CLASSES)

The TfS-specific machinery — the partial/full boundary flag, the A–H position decomposition, mass balancing, CCU/CCS credit accounting, recycled-content allocation, the positive-list references, the primary-data share plus three-axis DQR, verification shares, and the Attestation of Conformance — has no COMET representation. These 24 classes live in the `comet-tfs:` namespace, grouped below by the COMET layer they extend.

| COMET layer | New class | TfS fields | Why needed |
|---|---|---|---|
| L4 PCF | `TfSProductFootprint` | Id/version/status profile | Sub-class of `comet-pcf:PCFResult` that binds all TfS-specific fields into one conformant profile |
| L4 PCF | `DataModelVersion` | 2 (`specVersion`) | The `urn:tfs-initiative.com:datamodel-version:3.1.0` spec-version declaration; selectable independently of the standard followed |
| L4 PCF | `PartialFullPcf` | 3 (`partialFullPcf`) | Cradle-to-gate vs cradle-to-grave boundary flag; TfS default is cradle-to-gate |
| L4 PCF | `DeclaredUnitOfMeasurement` | 13 | Constrains the MERGE target to the 10-value TfS unit dropdown (piece … megabit second) |
| L4 PCF | `GeographyRegionOrSubregion` | 34 | Constrains geography to the ISO 3166 region list when a country is not disclosed |
| L4 PCF | `CutOffRule` | 24–25 | Exempted-emissions percentage (capped at 10%) plus rationale |
| L4 PCF | `RecycledContentType` | 28 | Post-industrial vs post-consumer recycled input |
| L4 PCF | `CrossSectoralStandard` | 43 | Value list of standards the calculation is based on |
| L4 PCF | `ProductOrSectorRule` | 44 | Most specific applied PCR; default `TfS PCF Guideline V3.0` |
| L4 PCF | `CharacterizationFactor` | 46 | IPCC AR version of the GWP values; default AR6 |
| L4 PCF | `AllocationApproach` | 47–51 | Container for foreground / recycling / CCU / waste-incineration allocation |
| L4 PCF | `WasteIncinerationAllocation` | 49 | cut-off / reverse cut-off / system expansion / not-applicable |
| L4 PCF | `RecycledCarbonAllocation` | 50 | Upstream system expansion (USE) vs cut-off for material recycling |
| L5 EAC | `CCUCalculationApproach` | 51 | not-applicable / cut-off method / credit method for Carbon Capture and Utilization |
| L5 EAC | `PositiveListReference` | 52–53 | References into the TfS positive lists of accepted PCRs and substituted products |
| L5 EAC | `MassBalancing` | 54–58 | Whether mass balancing (credit method) is used, free-attribution flag, scheme |
| L5 EAC | `MassBalanceCalculationApproach` | 57 | Conventional reference / Inventory / both — required if `massBalancingUsed` |
| L4 PCF | `DataQualityRating` | 64–69 | Primary Data Share + three DQR axes (technological, temporal, geographical), each 1–5; M2027 |
| L6 Verification | `VerificationShare` | 70–74 | PCS + 1PVS/2PVS/3PVS shares (0–100). Sub-class of `comet-ver:AuditClaim` |
| L6 Verification | `AttestationOfConformance` | 78–86 | The 9-field attestation object array. Sub-class of `comet-ver:DisclosureRecord` |
| L6 Verification | `AttestationType` | 79 | Program certification / 3rd / 2nd / 1st party / mass-balance certificate |
| L4 PCF | `LifeCycleStage` | 87–124 | Production / Packaging / Distribution stage, each carrying its own GWP breakdown |
| L4 PCF | `GWPPositionBreakdown` | 89–124 | The PACT v3.0 A–H position decomposition of a stage's GWP (see §6) |
| L4 PCF | `CarbonContentBreakdown` | 125–131 | Total carbon content per DU + fossil/biogenic/packaging/recycled/CCU components |

### Summary count

| Metric | Count |
|---|---|
| New classes proposed | 24 |
| Named-individual enum values | 79 |
| Object properties added | 13 |
| Datatype properties added | 51 |
| TfS fields mapped to existing COMET (`owl:equivalentClass` / `skos:closeMatch`) | 12 |
| Total triples in extension | 863 |

## 4. What TfS PCF in COMET means to each stakeholder

### Chemical suppliers and product owners
- **One record, four destinations.** A single `comet-tfs:TfSProductFootprint` satisfies a TfS Data Exchange, a PACT exchange, an EPD, and a downstream Scope-3 ask simultaneously — because the identity, unit, geography, and GWP-total fields are the *same* COMET quantities reused via §2, not four parallel spreadsheets.
- **Conditionality becomes machine-enforced.** The R-flag rules (`massBalancingCalculationApproach` required when `massBalancingUsed = TRUE`; `ccuCreditCertificateScheme` required when CCU credit method) are typed as domain constraints, so a supplier's system can refuse to publish an under-specified record instead of shipping it and being bounced by the platform.
- **Phase-in is on the calendar, not a surprise.** M2027 fields (Primary Data Share, DQR axes, Positions A/E/F) are tagged in the ontology today, so a supplier can stage data-collection projects against a known deadline rather than scrambling in 2027.

### Downstream manufacturers (Scope 3 buyers)
- **Auditable supplier data, not a PDF.** A buyer aggregating Scope 3 category 1 receives typed positions with sign rules attached — Position B and D removals are guaranteed ≤ 0, T2 guaranteed ≥ 0 — so aggregation across hundreds of suppliers is arithmetic on a graph, not manual reconciliation of inconsistent report formats.
- **Boundary honesty is explicit.** `PartialFullPcf` (cradle-to-gate vs cradle-to-grave) plus `packagingEmissionsIncluded` and the per-stage breakdown mean a buyer can see exactly what a supplier's number does and does not cover before booking it into their own footprint.
- **Primary vs secondary data is visible.** The Primary Data Share lets a buyer weight or challenge suppliers whose footprints lean on generic ecoinvent factors rather than measured plant data.

### Carbon verifiers
- **The verification-share machinery is first-class.** `VerificationShare` carries PCS (program-certified supplier share) and 1PVS/2PVS/3PVS as separate percentages, so a verifier — and a buyer — can see that, say, 70% of a footprint is third-party verified and 30% is self-declared, rather than a binary "verified/not".
- **The Attestation of Conformance is a typed object, not prose.** `AttestationOfConformance` binds the attestation type, the standard it rests on, a UUID v4 attestation ID, a link to the declaration, the issuer's legal entity + BPN, and the completion timestamp. Re-issuing an opinion year over year becomes diff-on-graph.
- **Clean bridge to existing COMET verification.** `VerificationShare` sub-classes `comet-ver:AuditClaim` and `AttestationOfConformance` sub-classes `comet-ver:DisclosureRecord`, so existing COMET verification workflows extend without new plumbing.

### LCA practitioners
- **Existing ISO 14067 output wraps cleanly.** SimaPro / openLCA / GaBi results map straight onto the A–H positions and the carbon-content breakdown; the extension adds the TfS reporting envelope without demanding a parallel methodology.
- **Allocation choices are declared, not buried.** `WasteIncinerationAllocation`, `RecycledCarbonAllocation`, and `CCUCalculationApproach` make the practitioner's allocation decisions explicit and comparable — the difference between an upstream-system-expansion and a cut-off recycling result stops being invisible.
- **Characterization-factor provenance travels with the number.** `CharacterizationFactor` (AR6 default) records which IPCC GWP set produced the result, so a downstream re-computation on a different AR version is detectable.

### Regulators (EU CBAM, EU Green Claims / ESRS)
- **CBAM embedded-emissions substantiation.** A cradle-to-gate TfS PCF for a chemical precursor is exactly the embedded-emissions evidence a CBAM declarant needs; the typed positions make the fossil component (Position A) directly extractable.
- **Green Claims / ESRS queryability.** The EU Green Claims Directive and ESRS E1 demand substantiated, comparable climate data. A SPARQL query over a COMET+TfS dataset answers "what boundary, what standard, what verification share, what data quality?" without reading a sustainability report.
- **Cross-border comparability.** Because the same 131 fields carry the same units and sign rules across every supplier, a competent authority can compare firms rather than adjudicate incommensurable disclosures.

### Data-exchange platforms (TfS Data Exchange Platform, Catena-X, PACT interoperability)
- **Native TfS Data Exchange payload.** `skos:notation` carries every TfS technical field name, so a COMET record round-trips with the TfS PCF Data Exchange Platform field-for-field.
- **PACT interoperability by construction.** Because TfS v3.1 is technically aligned to PACT v3.0, the `pact:` close-matches in §2 mean a COMET record is simultaneously a Pathfinder exchange payload.
- **Catena-X alignment.** `Rule_CatenaX` and the Catena-X PCF Rulebook reference let an automotive-adjacent chemical supplier satisfy a Catena-X PCF request from the same record.

## 5. Architecture — how it threads through the seven-layer stack

```
L6 Verification   VerificationShare (PCS · 1PVS/2PVS/3PVS)
                  AttestationOfConformance · AttestationType
                     ↑
L5 EAC            MassBalancing · MassBalanceCalculationApproach
                  CCUCalculationApproach · PositiveListReference
                  (CCU/CCS credits, REDcert2 / ISCC+ certificate schemes)
                     ↑
L4 PCF            TfSProductFootprint  (sub-class of comet-pcf:PCFResult)
                    ├─ PartialFullPcf · CutOffRule · AllocationApproach
                    ├─ DataQualityRating (PDS + 3-axis DQR)
                    ├─ LifeCycleStage {Production · Packaging · Distribution}
                    │     └─ GWPPositionBreakdown  (A · A1 · B · C · D · E · F · G · H → T1/T2)
                    └─ CarbonContentBreakdown  (fossil · biogenic · recycled · CCU)
                     ↑
L1 Core           Organization · Product  (reused via §2 MERGE, not redefined)
```

**Cross-cutting:** `CharacterizationFactor`, `CrossSectoralStandard`, `ProductOrSectorRule`, `DataModelVersion` qualify the whole footprint and reach across L4–L6. The design principle is *reuse core identity, expand only the TfS-specific decomposition* — the A–H breakdown, mass balancing, and the attestation object are the parts COMET could not previously express.

## 6. The A–H GWP position decomposition

Each `LifeCycleStage` carries one `GWPPositionBreakdown`: the TfS / PACT v3.0 emission-position decomposition of that stage's global warming potential. Positions carry strict sign rules — the removal positions B, D, G are negative contributions (≤ 0) and the excluding-uptake total T2 must be non-negative.

| Position | Property | Meaning | Sign |
|---|---|---|---|
| **A** | `fossilGhgEmissions` | Fossil emissions (industrial process, combustion, fugitive) | ≥ 0 (M2027) |
| **A1** | `landManagementFossilGhgEmissions` | Fossil land-management emissions — a detail of A | ≥ 0 |
| **B** | `technologicalCO2Removals` | Technological/geologic CO2 removal (BECCS) | **≤ 0** |
| **C** | `biogenicNonCO2Emissions` | Non-CO2 biogenic (CH4, biomass burning, rice, degradation) | ≥ 0 |
| **D** | `biogenicCO2Uptake` | Biogenic CO2 uptake in the product | **≤ 0** |
| **E** | `landUseChangeGhgEmissions` | Direct land-use-change (dLUC; iLUC excluded) | ≥ 0 (M2027) |
| **F** | `landManagementBiogenicCO2Emissions` | Biogenic CO2 from net carbon-stock loss | ≥ 0 (M2027) |
| **G** | `landManagementBiogenicCO2Removals` | CO2 removals from increased land carbon stock | **≤ 0** |
| **H** | `aircraftGhgEmissions` | Aviation emissions in cradle-to-gate distribution | ≥ 0 |
| **T1** | `pcfIncludingBiogenicUptake` | Total incl. biogenic uptake = A+B+C+D+E+F+G+H | — |
| **T2** | `pcfExcludingBiogenicUptake` | Total excl. biogenic uptake = A+B+C+E+F+G+H | **≥ 0** |

The breakdown is reported **per life-cycle stage** — Production, Packaging, and Distribution — and is aligned to the WBCSD PACT Pathfinder v3.0 taxonomy. Packaging-stage emissions are additionally folded into the Production-stage total when `packagingEmissionsIncluded = TRUE`. Units throughout are kg CO2e per declared unit.

## 7. Files

| File | Description |
|---|---|
| `comet-ext-tfs-pcf.ttl` | OWL ontology in Turtle — 24 new classes, 79 named-individual enum values, 13 object + 51 datatype properties, 12 `owl:equivalentClass` / `skos:closeMatch` alignments (863 triples) |
| `comet-ext-tfs-pcf-shapes.ttl` | SHACL shapes — M/O/D/R field discipline, sign-rule constraints (B/D/G ≤ 0, T2 ≥ 0), and R-flag conditionality (next milestone) |
| `examples/green-ethanol-pcf.ttl` | Worked example — a mass-balanced, CCU-credited green-ethanol PCF instance |
| `README.md` | This document — merge analysis, expansion analysis, stakeholder benefits, architecture |

## 8. Standards references

- **TfS PCF Data Model v3.1** (September 2025) — "How to report PCF data", the data aspect model documented by this extension
- **TfS PCF Guideline for the Chemical Industry v3.0** — the calculation methodology the Data Model reports
- **WBCSD PACT Pathfinder Framework v3.0** — the cross-industry emission taxonomy and data-exchange spec TfS v3.1 is technically aligned to
- **ISO 14067:2018** — Carbon footprint of products (quantification reference)
- **GHG Protocol Product Life Cycle Accounting and Reporting Standard** — cross-sectoral standard option
- **Mass-balance certificate schemes** — REDcert2, ISCC+ (referenced by `massBalancingCertificateScheme`)
- **Catena-X PCF Rulebook** — product-rule option (`Rule_CatenaX`) for interoperability with the Catena-X data space

## 9. Open RFC questions

1. **Flat property set vs reified positions.** The A–H positions are currently a flat datatype-property set on `GWPPositionBreakdown`. Should each position instead be a reified per-position node (`comet-tfs:Position` instances) so provenance, uncertainty, and sign-rule violations can be attached individually? Flat is lighter; reified is more auditable. Vote in the Chemicals-WG.
2. **Mass balancing vs `comet-asi` chain-of-custody.** TfS chemical-industry mass balance (credit method, certificate-driven) parallels the ASI chain-of-custody mass balance in `comet-asi`. Should `MassBalancing` be re-based on a shared COMET chain-of-custody abstraction, or stay certificate-scheme-specific (REDcert2 / ISCC+)?
3. **Promotion to a published layer.** If TfS + PACT + Catena-X converge, should `comet-tfs:` graduate from an extension to a first-class published COMET layer, or should the shared A–H position taxonomy be lifted into `comet-pcf` core with `comet-tfs` retaining only the chemical-sector specifics?
4. **M202X phase-in encoding.** Should the M2027 phase-in be a SHACL constraint parameterized by an as-of date (so conformance checking is time-aware), or a static annotation? Default leans SHACL — see `comet-ext-tfs-pcf-shapes.ttl`.
