# Changelog

All notable changes to COMET (Carbon Ontology for Materials and Emissions Tracking) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

**TfS PCF Data Model v3.1 extension** (`ext/tfs-pcf/`, `docs/tfs-pcf.html`)
- New extension module `comet-ext:tfs-pcf` (`comet-tfs:`, namespace `https://comet.carbon/ext/tfs-pcf#`) mapping all 131 fields of the Together for Sustainability **PCF Data Model v3.1** (September 2025) — the data aspect model of the TfS PCF Guideline for the Chemical Industry, technically aligned to WBCSD PACT Pathfinder v3.0 — onto the COMET seven-layer stack. 167 `comet-tfs` terms: **24 new classes**, **79 enumerated value individuals**, **13 object properties**, **51 datatype properties**, **12 `owl:equivalentClass`/`skos:closeMatch` bridges** to existing COMET (`comet-pcf:PCFResult`, `comet:Organization`, `comet:Product`, `comet-pcf:DeclaredUnit`, `comet:GeographicScope`, `comet-pcf:ReferencePeriod`, `comet-pcf:GlobalWarmingPotential`, `comet-pcf:FossilGHGEmission`, `comet-pcf:GHGRemoval`, `comet-pcf:MethodologyStandard`, `comet-ver:VerificationBody`, `comet-ver:AuditClaim`)
- New classes cover the TfS-specific machinery with no prior COMET home: `TfSProductFootprint` (sub-class of `comet-pcf:PCFResult`), the partial/full boundary declaration, the per-life-cycle-stage **A–H GWP position decomposition** (`GWPPositionBreakdown`, PACT v3.0-aligned, with sign + total constraints), `CarbonContentBreakdown`, `CutOffRule`, the allocation approaches (waste incineration / recycled carbon / CCU), `MassBalancing` (+ certificate schemes REDcert2 / ISCC+), the TfS PCR/system-expansion positive-list references, `DataQualityRating` (primary-data share + three-axis DQR), `VerificationShare` (PCS / 1PVS / 2PVS / 3PVS), and the `AttestationOfConformance` object array (sub-class of `comet-ver:DisclosureRecord`)
- `ext/tfs-pcf/comet-ext-tfs-pcf-shapes.ttl` SHACL shapes (cut-off 0–10%, PDS 0–100, DQR 1–5, A–H position sign rules, T2 ≥ 0, conditional mass-balancing requirements, mandatory attestation fields) validated with pyshacl against the worked example `ext/tfs-pcf/examples/green-ethanol-pcf.ttl` (Conforms: True)
- New converter `tools/converters/tfs_to_comet.py` (+ `tools/examples/tfs-v3-input.json`) turning a TfS PCF Data Model v3.1 JSON payload into a COMET JSON-LD `comet-tfs:TfSProductFootprint`
- Registered in `registry/namespaces.json`, `registry/comet-curies.json` (88 `comet_tfs_pending` CURIEs), `comet-context.jsonld`, and the ontology map (`tools/scripts/build-ontology-map.py` → `docs/ontology-data.{json,js}`, `docs/comet-ontology-values.xlsx`); surfaced in `docs/index.html`, `docs/ontology.html`, `docs/data-exchange.html`, and the dedicated per-standard page `docs/tfs-pcf.html`

### Changed
- Ontology term count rises to 1113 total (from 946) with the addition of 167 `comet-tfs` terms

## [0.3.0] - 2026-06-17

### Added

**Carbon Verification Market Coverage** (`ext/verification/`, `docs/glossary.html`)
- 20 new core terms extending the seven-layer stack to fully represent verification engagements under the Global Carbon Verification Market taxonomy (EU ETS, CSRD/ESRS E1, ISSB S2, ISO 14064-3, ISAE 3410, ISO 14067, EPD/EN 15804, PAS 2050, VCS, Gold Standard, SBTi, EU CBAM, CORSIA, IRA 45V, Article 6, California SB 253/261):
  - **L6 Verification** (`comet-ver:`): `VerificationOpinion`, `MaterialityThreshold`, `FindingsLog`, `CorrectiveActionRequest` (+ `severity`/`status`/`dueDate`), `OpportunityForImprovement`, `AccreditationBody` (+ `accreditationNumber`), `VerificationMethodology`, `SiteVisitRecord`, `IndependenceDeclaration`, `DataSubstitutionRule` — closing the gap where L6 was required by 100% of standards yet was the thinnest layer
  - **L3 Supply Chain** (`comet-sc:`): aggregate inventory totals `Scope1Emissions`, `Scope2Emissions` (location- + market-based), `Scope3Emissions` (+ `category` 1-15), `BaseYearEmissions`, `EmissionIntensity`, `RecalculationTrigger`
  - **L4 PCF** (`comet-pcf:`): `CarbonIntensity` (+ `functionalBasis`), `UncertaintyAssessment`
  - **L5 EAC** (`comet-eac:`): `CORSIAEligibleUnit` (+ `eligiblePeriod`)
  - **L7 Market** (`comet-mkt:`): `CleanHydrogenCreditTier` (+ `creditValue`) — IRA 45V tiers; local name avoids a leading digit to remain a valid CURIE/NCName, alt-label "45V Credit Tier"
- New extension module `ext/verification/comet-ext-verification.ttl` giving the 20 terms first-class OWL identity, plus `comet-ext-verification-shapes.ttl` SHACL shapes validated with pyshacl (valid instance Conforms: True; invalid instance fails on enum/range/cardinality constraints) — test data under `ext/verification/tests/data/`
- 51 new standards-alignment crosswalk rows registering ISO 14064-3, ISO 14065, ISAE 3410/3000, ISSB S2, EU ETS MRV, IRA 45V, ICAO CORSIA, SBTi, EN 15804+A2, Verra VCS and GHG Protocol Scope 3 as formally aligned standards. Crosswalks without a citable external identifier carry an empty `target_iri` (coverage registered without fabricating IRIs)
- Extended `tools/schemas/comet-core.schema.json` `Verification` definition with `opinionType`, `materialityThreshold`, `accreditationBody`/`accreditationNumber`, `independenceDeclared`, `siteVisitPerformed` and a structured `findings` array

**New converters** (`tools/converters/`)
- `ghgprotocol_to_comet.py` (full) — GHG Protocol / ESRS E1 corporate inventory (JSON or CSV) to COMET, populating the new Scope 1/2/3, base-year and intensity aggregates; invalid Scope 3 categories are dropped with a warning
- `h45v_to_comet.py` (full) — IRA 45V clean-hydrogen attestation to COMET, implementing the four statutory 26 USC 45V(b) credit tiers keyed to 45VH2-GREET lifecycle carbon intensity, with credit-value and estimated-credit computation
- `epd_to_comet.py`, `corsia_to_comet.py`, `verra_to_comet.py` (scaffolds) — public API, CLI and COMET skeleton in place with a working JSON path and a marked TODO for full EN 15804 ILCD-XML / ICAO CORSIA registry / Verra-Gold Standard registry mapping
- All five wired into `tools/comet_cli.py` (`comet convert --from ghg-protocol|esrs|45v|epd|corsia|verra|gold-standard`); round-trip test suite `tools/converters/tests/test_v030_converters.py` (23 checks, all passing)

### Changed
- `tools/scripts/build-ontology-map.py` now resolves bare standard names (not just `prefix: term` chunks) in the glossary alignment column, so coverage registers for standards without per-term external identifiers
- Ontology term count rises from 113 to 141 core terms (904 to 937 total incl. incorporated CAD Trust); alignment crosswalks rise from 242 to 293

### Added

**Schema Map, Interactive Ontology & Value Lookup** (`docs/schema-map.html`)
- New single-source-of-truth extractor `tools/scripts/build-ontology-map.py` that reads **every** place a COMET term is defined — the seven-layer core vocabulary tables in `docs/glossary.html`, the OWL/SHACL extension modules (`comet-rs`, `comet-cn`), the incorporated CAD Trust v2.0.2 Data Dictionary (`docs/CAD-Trust-Data-Dictionary-v2.0.2.xlsx`), the three JSON Schemas, `comet-context.jsonld` and the alignment crosswalks — and normalises them into one 904-term table plus a node/edge graph
- New interactive page `docs/schema-map.html` with four views: (1) an interactive Cytoscape force-directed **ontology graph** (456 relational nodes, 267 edges incl. synthesised `partOf` property→class links) with namespace legend toggles, layout switching, search-to-isolate and per-node info cards; (2) a layered **schema map** of the COMET seven-layer stack + CAD Trust band with clickable term chips; (3) a sortable, searchable, filterable **value lookup** of all 904 terms (109 classes, 114 properties, 649 CAD Trust fields/picklist values, 32 individuals); (4) a sortable **alignments** crosswalk of 242 standards mappings (ISO 14068/14067, EU CBAM, EU ESRS, GHG Protocol, WBCSD PACT, UN SDG, CAD Trust, schema.org, QUDT, W3C PROV)
- New generated artifacts: `docs/comet-ontology-values.xlsx` (5-sheet workbook — Summary, Terms, Namespaces, Alignments, Schema Fields, with frozen panes + autofilter for in-Excel sorting), `docs/ontology-data.json` and `docs/ontology-data.js` (consolidated graph payload; the `.js` wrapper lets the page run from `file://`)
- The build canonicalises the two divergent `comet-rs` base IRIs so alignment edges connect to their defined term nodes, synthesises stub nodes for referenced-but-upstream COMET core terms and external standard targets, and keeps the flat 649-row CAD Trust dictionary in the table/XLSX (out of the relational graph) so the graph stays readable across the full stack
- Index page (`docs/index.html`) links to the new Schema Map
- `tools/requirements.txt` adds `rdflib` and `openpyxl`

**ISO 14068-1:2023 Carbon Neutrality Extension** (`comet-ext:iso14068`, prefix `comet-cn:`)
- New extension module aligning ISO 14068-1:2023 *Climate change management — Transition to net zero — Part 1: Carbon neutrality* with the COMET seven-layer stack
- 18 `owl:equivalentClass` bridges from ISO 14068 terms to existing COMET classes (carbon footprint, direct/indirect emissions, GHG removals, sources, sinks, GWP, CO2e, organizational + system boundaries, carbon credits, crediting programmes, registries, organization, product, stakeholder, top management, value chain)
- 24 new classes covering concepts COMET did not yet encode: `Subject`, `Entity`, `FinancialInstitution`, `Baseline`, `BasePeriod`, `ReportingPeriod`, `UnabatedGHGEmission`, `ResidualGHGEmission`, `GHGEmissionReduction`, `GHGRemovalEnhancement`, `CarbonNeutralityCommitment`, `CarbonNeutralityPathway`, `CarbonNeutralityManagementPlan`, `CarbonNeutralityClaim`, `CarbonNeutralityReport`, `HierarchyAction`, `CreditCriterion`, `CreditingProgrammeCriterion`, `CreditType`, `OffsettingEvent`, `CorrespondingAdjustment`, `RemovalReversal`, `VerificationOpinion`, `FinancedEmissionsAccount`
- 11 named-individual principles representing ISO 14068 Clause 4 (Transparency, Conservativeness, Hierarchy approach, Supporting transition, Ambition, Urgency, Science-based approach, Avoiding adverse impacts, Accountability, Value chain and life cycle approach)
- 15 object + datatype properties wiring the new classes together (`hasSubject`, `hasBoundary`, `hasCommitment`, `hasPathway`, `hasBaseline`, `hierarchyStep`, `meetsCriterion`, `targetYearResidualOnly`, `vintageEndYear`, `retirementDate`, `correspondingAdjustmentApplied`, `isExPostCredit`, `reportingPeriodStart`, `reportingPeriodEnd`, others)
- New extension files: `ext/iso14068/comet-ext-iso14068.ttl` (OWL ontology in Turtle), `ext/iso14068/README.md` (stakeholder summary report with merge map, expansion map, and benefits by stakeholder type)
- New documentation page: `docs/iso14068.html` — visual presentation of merge / expansion / stakeholder benefits / forbidden practices / adoption checklist
- JSON-LD context updated (`comet-context.jsonld`) with the new `comet-cn:` namespace and key terms
- Index page (`docs/index.html`) and ontology specification (`docs/ontology.html`) link to the new ISO 14068 extension

### Changed
- Top navigation on `docs/ontology.html` now exposes the ISO 14068 extension and the Materials hub

## [0.2.1] - 2026-04-27

### Added

**COMET Materials hub** (`docs/materials.html`)
- New page pairing the *A Shared Carbon Language* explainer video (~6 min, MP4, 33 MB) with the v0.1 Carbon Protocol stakeholder deck (14 slides, PPTX, 15 MB)
- Slide-by-slide summaries linking each visualization to the COMET layers, namespaces, and governance model it depicts
- Banner + TOC link on `docs/ontology.html` and three-card row on `docs/index.html` make the materials discoverable from the home page and the spec

## [0.2.0] - 2026-03-30

### Added

**Core Ontology Enhancements**
- SHACL constraint shapes for all core classes and properties
- Multilingual labels and definitions in 10 languages (English, Spanish, German, French, Mandarin, Portuguese, Japanese, Italian, Dutch, Swedish)
- RDF example datasets demonstrating emissions calculations, supply chain tracking, and carbon accounting scenarios
- Competency questions for each ontology domain with corresponding SPARQL query solutions
- JSON-LD context files for easier integration with web applications and APIs

**Infrastructure & Quality**
- Continuous Integration (CI) pipeline with automated testing and validation
- Community governance structure with decision-making processes and roles
- Extension module framework for domain-specific specialization
- SKOS concept schemes for controlled vocabularies and translations
- Alignment files mapping COMET to external standards (GHG Protocol, ISO 14001, PACT)
- Comprehensive documentation suite with tutorials, FAQs, and architectural decisions

**Documentation**
- Getting Started guide (5-minute quick start)
- Frequently Asked Questions (20 entries)
- Extension creation cookbook with worked examples
- Architecture Decision Records (ADRs 001-006)
- VoID dataset description for semantic web integration

### Changed
- Improved semantic clarity in core emissions calculation layer
- Enhanced domain-specific constraint definitions for better validation
- Strengthened alignment with international standards

### Fixed
- Resolved namespace URI conflicts with external vocabularies
- Improved SPARQL query performance with better indexing recommendations

## [0.1.0] - 2026-03-30

### Added

**ResponsibleSteel Extension Module**
- 31 new ontology classes for steel supply chain domain
- 15 object properties for relationships between steel entities
- 22 data properties for steel-specific attributes
- 13 named individuals representing common steel certifications and standards
- SHACL validation shapes for steel-specific constraints
- Example instance data for representative steel products and supply chains
- Multilingual labels (minimum 3 languages)
- Documentation and use cases for steel emissions tracking

**Core Infrastructure**
- Extension module pattern for building domain-specific specializations
- Support for extension integration with main ontology
- Framework for managing extension lifecycle (RFC → Draft → Stable)

## [0.0.1] - 2026-03-15

### Added

**Initial Release: Seven-Layer Stack Architecture**

Core ontology foundation with 7 semantic layers:

1. **Data Layer**: Raw emissions data, measurement units, temporal information
2. **Process Layer**: Manufacturing processes, supply chain operations, activity data
3. **Product Layer**: Material definitions, product specifications, bill of materials
4. **Certification Layer**: Standards compliance, certifications (ISO, PACT, CBAM), metadata
5. **Calculation Layer**: Emissions factors, calculation methodologies, accounting rules
6. **Reporting Layer**: Emissions assertions, report generation, disclosure requirements
7. **Impact Layer**: Planetary boundaries, decarbonization pathways, sustainability metrics

**Core Components**
- OWL 2 DL ontology definition with 250+ classes and properties
- Dual licensing (CC BY 4.0 for data, Apache 2.0 for software)
- Namespace URI design (https://comet.carbon/ontology/)
- RDF serialization in Turtle format
- Example SPARQL queries for common use cases

**Documentation**
- Ontology specification document
- Seven-layer architecture overview
- Example instance data in RDF/Turtle
- SPARQL query examples

---

## Deprecation Timeline

**Deprecations are announced 6+ months in advance with clear migration paths.**

Currently no active deprecations.

## Version Support

| Version | Status | Support Until |
|---------|--------|---------------|
| 0.2.0   | Current | 2026-09-30 (or until 1.0.0) |
| 0.1.0   | Deprecated | 2026-06-30 |
| 0.0.1   | Retired | Available in history |

## Future Releases

**Planned for Q2 2026**:
- Additional extensions (textiles, automotive, renewable energy)
- SPARQL endpoint reference implementation
- Python SDK enhancements
- Performance optimization for large datasets

**Planned for Q3 2026**:
- Version 1.0.0 candidate
- Governance review and refinement
- Integration guides for major platforms

---

## How to Upgrade

### From 0.1.0 to 0.2.0

No breaking changes. All queries and data remain compatible. To take advantage of new features:

1. **Update namespace references** to include new vocabulary if using new layers
2. **Add SHACL validation** to your applications for improved data quality
3. **Incorporate multilingual labels** if supporting international users
4. **Review example datasets** for best practices on new features

### From 0.0.1 to 0.1.0

No breaking changes. Add ResponsibleSteel classes to your ontology imports:
```
@prefix rs: <https://comet.carbon/ontology/responsiblesteel/> .
```

Then use steel classes as needed in your instance data.

---

## Reporting Issues

Found an issue with a specific release? File a bug report at https://github.com/comet-ontology/comet/issues with the version tag.

## Credits

COMET development is community-driven. See CONTRIBUTING.md for recognition and contribution guidelines.
