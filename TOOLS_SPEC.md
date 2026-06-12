# COMET Data Tools — Requirements Specification

*Authored by 5 MECE domain experts with 20+ years experience each.*
*Date: 2026-03-17 · Status: Approved for build*

---



## Problem Statement

Users arrive at COMET with data in existing formats (CSV spreadsheets, PACT v3 JSON, CBAM XML, CAD Trust registry exports, LCA tool outputs). They need to:

1. **Ingest**: Convert their existing data into COMET-compliant JSON-LD
2. **Validate**: Verify their COMET data is structurally correct and complete
3. **Egress**: Export COMET data into formats required by specific consumers (CBAM authority, PACT platforms, registries, procurement systems)

Today, zero tools exist for any of these operations. Every user must read the ontology spec, understand JSON-LD, and manually construct payloads. This is the #1 barrier to adoption.

---

## Tool Inventory

### A. Core Infrastructure

#### A1. JSON Schema Files
**Goal**: Machine-readable validation rules for every COMET data type.
**Expert**: Priya Sharma
**Function**: Define the exact structure, required fields, types, enumerations, and constraints for each COMET data class. These schemas are the foundation for all validation and conversion tools.

**Files to build**:

**`comet-pcf.schema.json`** — Product Carbon Footprint
- `pcfId` (string, required, format: uuid)
- `declaredUnit` (string, required, enum: kilogram, litre, cubicMetre, kilowattHour, megajoule, tonneKilometre, squareMetre)
- `unitaryProductAmount` (number, required, minimum: 0, exclusiveMinimum: true)
- `fossilGWP` (number, required, minimum: 0) — kgCO2e per declared unit
- `totalGWP` (number, nullable) — including biogenic
- `fossilEmissions` (number, nullable)
- `biogenicCarbonContent` (number, default: 0)
- `biogenicUptake` (number, default: 0)
- `landUseChange` (number, default: 0)
- `aircraftEmissions` (number, default: 0)
- `packagingEmissions` (number, default: 0)
- `exemptedPercent` (number, minimum: 0, maximum: 100)
- `ipccAR` (string, enum: AR5, AR6)
- `standardRef` (array of strings, minItems: 1) — e.g., ["ISO14067", "GHGProtocol"]
- `pcrName` (string, nullable)
- `allocationDescription` (string, nullable)
- `boundaryDescription` (string, required)
- `referencePeriod` (object: {startDate: date-time, endDate: date-time}, required)
- `organization` (object: {orgName: string required, orgId: string[], country: ISO3166-2})
- `material` (object: {materialName: string required, materialId: string[], cpcCode: string, tradeName: string})
- `site` (object: {siteCountry: ISO3166-2, region: string})
- `primaryDataShare` (number, minimum: 0, maximum: 100)
- `dqi` (object: {coveragePercent: number, technologyDQI: 1-3, temporalityDQI: 1-3, geographyDQI: 1-3, reliabilityDQI: 1-3})
- `verification` (object: {hasAssurance: boolean, levelType: enum [limited, reasonable], verifierName: string, verificationDate: date-time, standardRef: string})
- JSON-LD: include `@context` field pointing to COMET + PACT contexts

**`comet-eac.schema.json`** — Environmental Attribute Certificate
- `eacId` (string, required, format: uuid)
- `eacType` (string, required, enum: EnergyAttributeCertificate, CarbonRemovalCertificate, MaterialStewardshipCertificate, CarbonAvoidanceCredit)
- `subType` (string, enum per eacType — e.g., IREC, GuaranteeOfOrigin, REC, DACCredit, BiocharCredit, VCU, GoldStandardVER, CDMCER, ResponsibleSteelSCC, ASICertification)
- `registry` (object: {registryName: string required, registryId: string})
- `project` (object: {projectName: string required, projectId: string, projectType: string, country: ISO3166-2, methodology: string})
- `vintage` (object: {startDate: date, endDate: date})
- `quantity` (number, required, minimum: 0)
- `unit` (string, required, enum: tCO2e, MWh, kg)
- `status` (string, enum: issued, active, retired, cancelled)
- `retirementInfo` (object nullable: {retiredDate: date-time, retiredBy: string, beneficiary: string, purpose: string})
- `verification` (object: same as PCF verification sub-schema)
- `cadTrust` (object nullable — for CAD Trust mapped credits: projectId, unitId, issuanceId per CAD Trust v2.0.2)

**`comet-core.schema.json`** — Shared entities
- Organization: {orgName, orgId[], orgType, country}
- Site: {siteName, siteId, siteCountry, region, latitude, longitude}
- Material: {materialName, materialId[], cpcCode, tradeName, hsCode}
- TimePeriod: {startDate, endDate}
- UnitOfMeasure: {unit, qudtUri}
- EmissionFactor: {efId, efValue, efUnit, source, vintage, geography, technology}

#### A2. Validation Script
**Goal**: Validate any COMET JSON-LD file against the schemas.
**Expert**: Priya Sharma
**Function**: Load a COMET JSON-LD file, detect its type (PCF, EAC, Core), validate against the correct schema, and report all errors with field paths, expected types, and fix suggestions.

**Features**:
- Auto-detect document type from `@type` field
- Validate required fields, types, enums, ranges
- Report errors as structured JSON: `{field, error, expected, got, suggestion}`
- Return exit code 0 (valid) or 1 (invalid)
- Support batch validation (directory of files)
- `--strict` mode: also check optional fields for type correctness
- `--quiet` mode: only output error count

#### A3. CLI Entry Point (`comet_cli.py`)
**Goal**: Single command-line interface for all COMET operations.
**Function**: Unified CLI that dispatches to converters and validators.

**Commands**:
```
comet validate <file>              Validate a COMET JSON-LD file
comet convert <input> --from <fmt> --to comet   Convert to COMET
comet export <input> --to <fmt>                  Export from COMET
comet template <type>                            Generate blank template
```

**Supported formats**: `csv`, `pact`, `cbam-xml`, `cad-trust`, `json`
**Supported template types**: `pcf`, `eac`, `scope3`

**Requirements**:
- Python 3.9+, no external dependencies beyond stdlib + jsonschema
- Colored terminal output for errors/warnings
- `--output` flag for all commands (default: stdout)
- `--pretty` flag for formatted JSON output
- `--help` with examples for every command

---

### B. Ingest Converters (External Format → COMET JSON-LD)

#### B1. CSV → COMET (`csv_to_comet.py`)
**Goal**: Convert a filled-in CSV template into COMET JSON-LD.
**Function**: Read a CSV file where columns map to COMET fields, validate each row, and output one COMET JSON-LD document per row.

**Input**: CSV file with COMET-aligned column headers (from template)
**Output**: One or more `.comet.json` files

**Column mapping (PCF template)**:
```
org_name, org_id, product_name, product_id, cpc_code, declared_unit,
amount, fossil_gwp, total_gwp, biogenic_carbon, boundary_description,
period_start, period_end, country, region, primary_data_share,
dqi_coverage, dqi_technology, dqi_temporality, dqi_geography, dqi_reliability,
standard_ref, pcr_name, allocation_description,
has_assurance, assurance_level, verifier_name, verification_date
```

**Features**:
- Header auto-detection (fuzzy match column names to COMET fields)
- Skip blank rows, trim whitespace
- Validate each row against schema before outputting
- Error report: row number + field + issue
- Support for multi-row files (one PCF per row)
- `--batch` flag: output individual files or array
- Handle unit normalization (kg, t, kWh → COMET enum values)

#### B2. PACT v3 → COMET (`pact_to_comet.py`)
**Goal**: Enrich a PACT v3 JSON payload with COMET @context and type annotations.
**Function**: Read a PACT v3 ProductFootprint JSON, inject COMET @context, map fields to COMET properties, and output COMET JSON-LD.

**Input**: PACT v3 JSON (as per WBCSD spec)
**Output**: COMET JSON-LD with dual context (PACT + COMET)

**Field mapping** (44 fields, from data-exchange.html Section 2a):
- `id` → `pcfId`
- `companyName` → `organization.orgName`
- `companyIds` → `organization.orgId`
- `productDescription` → `material.materialName`
- `productIds` → `material.materialId`
- `productCategoryCpc` → `material.cpcCode`
- `pcf.declaredUnit` → `declaredUnit`
- `pcf.unitaryProductAmount` → `unitaryProductAmount`
- `pcf.pCfExcludingBiogenic` → `fossilGWP`
- `pcf.pCfIncludingBiogenic` → `totalGWP`
- `pcf.fossilGhgEmissions` → `fossilEmissions`
- `pcf.biogenicCarbonContent` → `biogenicCarbonContent`
- `pcf.dLucGhgEmissions` → `landUseChange`
- `pcf.biogenicCarbonWithdrawal` → `biogenicUptake`
- `pcf.aircraftGhgEmissions` → `aircraftEmissions`
- `pcf.characterizationFactors` → `ipccAR`
- `pcf.crossSectoralStandardsUsed` → `standardRef`
- `pcf.productOrSectorSpecificRules[].name` → `pcrName`
- `pcf.allocationRulesDescription` → `allocationDescription`
- `pcf.boundaryProcessesDescription` → `boundaryDescription`
- `pcf.referencePeriodStart` → `referencePeriod.startDate`
- `pcf.referencePeriodEnd` → `referencePeriod.endDate`
- `pcf.geographyCountry` → `site.siteCountry`
- `pcf.geographyRegionOrSubregion` → `site.region`
- `pcf.exemptedEmissionsPercent` → `exemptedPercent`
- `pcf.primaryDataShare` → `primaryDataShare`
- `pcf.packagingGhgEmissions` → `packagingEmissions`
- `pcf.dqi.*` → `dqi.*`
- `pcf.assurance.*` → `verification.*`
- `validityPeriodStart/End` → `referencePeriod.*`

**Features**:
- Accept single object or array of ProductFootprints
- Preserve all original PACT fields (non-destructive enrichment)
- Add `@context` array with both PACT and COMET context URIs
- Add `@type: "comet-pcf:ProductCarbonFootprint"`
- Validate output against COMET PCF schema
- Report unmapped fields as warnings
- `--strip-pact` flag: output pure COMET (remove PACT-specific fields)

#### B3. CBAM XML → COMET (`cbam_to_comet.py`)
**Goal**: Parse a CBAM embedded emissions declaration XML and convert to COMET JSON-LD.
**Function**: Read CBAM XML (per DG TAXUD schema), extract declarations, map to COMET classes, output JSON-LD.

**Input**: CBAM XML declaration file
**Output**: COMET JSON-LD (one per declaration or one combined)

**XML element mapping**:
- `<CBAMDeclaration>` → root object, `@type: "comet-pcf:CBAMDeclaration"`
- `<AuthorisedDeclarant>` → `declarant` object (name, EORI, address)
- `<CoveredGood>` → `coveredGoods[]` array
- `<CNCode>` → `material.hsCode`
- `<CountryOfOrigin>` → `site.siteCountry`
- `<EmbeddedEmissions>` → `fossilGWP` (direct) + indirect
- `<SpecificDirectEmissions>` → per-tonne direct emissions
- `<SpecificIndirectEmissions>` → per-tonne indirect emissions
- `<Installation>` → `site` object
- `<CarbonPricePaid>` → `carbonPricePaid` (local price, currency)

**Features**:
- Parse XML with standard library (xml.etree.ElementTree)
- Handle both transitional (reporting-only) and full (financial) declaration formats
- Map CN codes to product descriptions where known (steel: 7206-7229, aluminium: 7601-7616, cement: 2523, hydrogen: 2804, fertilisers: 3102-3105)
- Calculate total embedded emissions from specific rates × quantity
- Validate EORI format (2-letter country + 15 digits)
- Output includes both COMET structure and original CBAM reference IDs

#### B4. CAD Trust → COMET (`cad_trust_to_comet.py`)
**Goal**: Convert CAD Trust v2.0.2 registry data into COMET JSON-LD.
**Function**: Read CAD Trust data exports (CSV or JSON from registry APIs), map the 13 tables to COMET EAC and verification classes.

**Input**: CAD Trust export (CSV per table, or combined JSON)
**Output**: COMET JSON-LD (one document per credit unit, or combined)

**Table mapping** (13 CAD Trust tables):
- `project` → `eac.project` (projectName, projectId, projectType, country, methodology, standard, status)
- `unit` → `eac` root (eacId, quantity, vintage, serialNumber, status)
- `issuance` → `eac.issuanceInfo` (issuanceDate, quantity, vintage)
- `retirement` → `eac.retirementInfo` (retiredDate, retiredBy, beneficiary, purpose)
- `verification` → `verification` object (verifierName, verificationDate, standard, status)
- `label` → `eac.labels[]` (labelName, labelVersion, criteria)
- `co_benefit` → `eac.coBenefits[]` (benefitType: SDG number, description)
- `design` → `eac.project.design` (baselineScenario, additionality, leakage)
- `pricing` → `eac.pricing` (pricePerUnit, currency, transactionDate)
- `rating` → `eac.rating` (ratingAgency, ratingValue, ratingDate)
- `article6_authorization` → `eac.article6` (authorizingCountry, correspondingAdjustment)
- `article6_itmo` → `eac.article6.itmo` (transferringCountry, acquiringCountry, amount)
- `corresponding_adjustment` → `eac.article6.adjustment` (adjustmentType, reportingPeriod)

**Features**:
- Accept individual table CSVs or combined export
- Auto-detect table by column headers
- Join related tables on foreign keys (unit.project_id → project.id)
- Denormalize into COMET's flat-ish JSON-LD structure
- Map CAD Trust status values to COMET enums
- Handle SDG co-benefit codes (1-17 → UN SDG names)
- Preserve original CAD Trust IDs in `cadTrust` namespace for traceability

---

### C. Egress Converters (COMET → External Format)

#### C1. COMET → PACT v3 (`comet_to_pact.py`)
**Goal**: Export a COMET PCF as a PACT v3-compliant JSON payload.
**Function**: Read COMET JSON-LD, strip COMET-specific fields, reshape to PACT v3 schema, validate against PACT spec.

**Output**: PACT v3 JSON (as accepted by any Pathfinder API)

**Features**:
- Reverse field mapping (all 44 fields from B2, inverted)
- Generate `id` as UUID if not present
- Set `specVersion: "3.0.0"`, `status: "Active"`, `version: 1`
- Map COMET enums back to PACT enums (e.g., `kilogram` → `kilogram`)
- Reconstruct nested `pcf.dqi`, `pcf.assurance` objects
- Remove COMET @context and @type
- `--pact-only` flag: strip all COMET extension fields
- Validate output against PACT v3 JSON Schema (bundled)

#### C2. COMET → CBAM XML (`comet_to_cbam.py`)
**Goal**: Generate a CBAM-compliant XML declaration from COMET data.
**Function**: Read COMET PCF JSON-LD, generate CBAM XML per DG TAXUD schema.

**Output**: XML file conforming to CBAM declaration schema

**Features**:
- Generate proper XML structure with CBAM namespace
- Map COMET fields to CBAM XML elements (reverse of B3)
- Auto-populate CN codes from material descriptions where possible
- Calculate specific emissions rates (per tonne) from total and quantity
- Include installation data, carbon price paid, country of origin
- Generate unique declaration reference number
- Add XML declaration and schema reference headers
- Pretty-print XML with proper indentation
- Validate XML structure before output

#### C3. COMET → CSV (`comet_to_csv.py`)
**Goal**: Flatten COMET JSON-LD back to spreadsheet-friendly CSV.
**Function**: Read one or more COMET JSON-LD files, flatten nested structures, output as CSV with COMET-aligned column headers.

**Output**: CSV file matching the COMET template format

**Features**:
- Flatten nested objects (organization.orgName → org_name column)
- Handle arrays (standardRef → semicolon-separated in one column)
- Auto-detect COMET type (PCF vs EAC) and use appropriate column set
- Support single file or directory of files (one row per file)
- Include header row with column descriptions as comment row (optional)
- `--type pcf|eac|scope3` flag to force output format

---

### D. Templates & Examples

#### D1. CSV Templates
**Goal**: Downloadable, fill-in-the-blank CSV templates for each data type.

**`pcf-template.csv`**: One header row with all PCF fields, one example row (steel PCF), one blank row for user.
Columns: org_name, org_id, product_name, product_id, cpc_code, declared_unit, amount, fossil_gwp, total_gwp, biogenic_carbon, land_use_change, biogenic_uptake, aircraft_emissions, packaging_emissions, exempted_percent, boundary_description, period_start, period_end, country, region, primary_data_share, dqi_coverage, dqi_technology, dqi_temporality, dqi_geography, dqi_reliability, standard_ref, pcr_name, allocation_description, has_assurance, assurance_level, verifier_name, verification_date

**`scope3-template.csv`**: One row per Scope 3 category (15 rows pre-filled with category names).
Columns: category_number, category_name, emission_source, activity_data_value, activity_data_unit, emission_factor, ef_source, ef_unit, total_emissions_kgCO2e, data_quality_type (primary/secondary/estimated), methodology_notes

**`eac-template.csv`**: Columns for EAC/carbon credit registration.
Columns: eac_type, sub_type, registry_name, registry_id, project_name, project_id, project_type, country, methodology, vintage_start, vintage_end, quantity, unit, status, verifier_name, verification_date, verification_standard

#### D2. Example JSON-LD Files
**Goal**: Copy-paste-ready example files for each common use case.

**`steel-pcf.comet.json`**: Complete PCF for hot-rolled steel coil (BOF route). Real-world plausible values: 1.85 kgCO2e/kg, German site, Bureau Veritas verified, ISO 14067 + GHG Protocol standards.

**`pact-v3-input.json`**: A standard PACT v3 payload (no COMET context) that users can feed to the pact_to_comet converter to see the output.

**`cbam-declaration.xml`**: A CBAM embedded emissions declaration XML for steel imports. Includes AuthorisedDeclarant, two CoveredGoods with different CN codes, installation data.

**`cad-trust-project.json`**: A CAD Trust credit project with unit issuance, verification, and SDG co-benefits. Mapped from the v2.0.2 data dictionary.

**`aluminium-pcf.comet.json`**: PCF for primary aluminium (smelter route). 8.5 kgCO2e/kg, ASI certified, Norwegian site.

**`dac-credit.comet.json`**: Direct Air Capture carbon removal certificate. 1 tCO2e, Climeworks registry, Article 6 eligible.

---

### E. Web Playground

#### E1. COMET Playground (`playground.html`)
**Goal**: Browser-based tool where users paste data and get COMET output instantly.
**Function**: Static HTML/JS page (hosted on GitHub Pages) that provides in-browser conversion and validation. No server required.

**Layout**:
- Header with COMET branding (match site design)
- Two-panel layout: INPUT (left) | OUTPUT (right)
- Format selector: CSV → COMET | PACT → COMET | COMET → PACT | COMET → CBAM | Validate
- Paste area or file upload for input
- Convert button
- Output panel with syntax-highlighted JSON/XML
- Copy-to-clipboard button
- Download button

**Features**:
- All conversion logic runs client-side in JavaScript
- Implements the same field mappings as the Python converters
- JSON Schema validation built into the browser
- Syntax highlighting for JSON and XML output
- Error display with field-level highlighting
- Pre-loaded examples (click to fill input with steel PCF, PACT payload, etc.)
- Tab interface for multiple conversions
- Responsive: stacks vertically on mobile

**Conversion modes**:
1. **CSV → COMET**: Parse CSV text, map columns, output JSON-LD
2. **PACT v3 → COMET**: Parse PACT JSON, inject context, map fields
3. **COMET → PACT v3**: Strip COMET context, reshape to PACT
4. **COMET → CBAM XML**: Generate XML from COMET JSON-LD
5. **Validate**: Check any COMET JSON-LD against schemas, show errors

---

## Project Structure

```
comet-ontology/
├── docs/                          # GitHub Pages microsite
│   ├── playground.html            # NEW — Web-based converter
│   └── ...
├── tools/                         # NEW — CLI tools & converters
│   ├── README.md                  # Tool documentation
│   ├── requirements.txt           # Python dependencies
│   ├── comet_cli.py               # Unified CLI entry point
│   ├── schemas/
│   │   ├── comet-pcf.schema.json
│   │   ├── comet-eac.schema.json
│   │   └── comet-core.schema.json
│   ├── validators/
│   │   └── validate.py
│   ├── converters/
│   │   ├── __init__.py
│   │   ├── csv_to_comet.py
│   │   ├── pact_to_comet.py
│   │   ├── comet_to_pact.py
│   │   ├── cbam_to_comet.py
│   │   ├── comet_to_cbam.py
│   │   ├── cad_trust_to_comet.py
│   │   └── comet_to_csv.py
│   ├── templates/
│   │   ├── pcf-template.csv
│   │   ├── scope3-template.csv
│   │   └── eac-template.csv
│   └── examples/
│       ├── steel-pcf.comet.json
│       ├── aluminium-pcf.comet.json
│       ├── dac-credit.comet.json
│       ├── pact-v3-input.json
│       ├── cbam-declaration.xml
│       └── cad-trust-project.json
└── TOOLS_SPEC.md                  # THIS FILE
```

## Dependencies

**Python tools**: Python 3.9+, `jsonschema` library only. All other processing uses stdlib (`json`, `csv`, `xml.etree.ElementTree`, `argparse`, `pathlib`, `uuid`, `datetime`).

**Web playground**: Zero dependencies. Vanilla HTML/CSS/JS. Hosted on GitHub Pages.

---

## Success Criteria

1. A user with a CSV of PCF data can convert it to COMET JSON-LD in under 60 seconds
2. A user with a PACT v3 payload can enrich it with COMET context in one command
3. A user with COMET data can generate a CBAM XML declaration in one command
4. All outputs validate against the COMET JSON Schemas
5. The web playground works entirely client-side with no server
6. Every tool includes `--help` with at least one usage example
7. All example files pass validation
