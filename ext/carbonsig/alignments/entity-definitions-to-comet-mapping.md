# CarbonSig Entity Definitions → COMET Mapping

## Overview

This document maps the CarbonSig entity definitions from the `carbonsig-entity-definitions` repository to the COMET ontology. Each entity is analyzed for its alignment with COMET's seven-layer architecture (Core Identity, Emission Factors, Supply Chain & Activity Data, Product Carbon Footprint, Environmental Attributes, Verification & Assurance, and Market Signals).

## Entity Mappings with Confidence Levels

### 1. User Entity (carbonsig_auth_service)

**Full Term Definition:** A system user with authentication credentials and profile information.

**Fields:**
- `id`: Unique identifier
- `username`: Login credential
- `email`: Contact information
- `password`: Authentication secret
- `fullName`: User display name  
- `disabled`: Account status flag
- `confirmed`: Email confirmation status
- `activeSiteId`: Current site context reference
- `imagePath`: User avatar location
- `lastLoginDate`: Temporal activity tracking
- `activeTime`: Session duration tracking
- `status`: Current user state

**COMET Alignment:**

| Field | COMET Term | Layer | Confidence | Definition |
|-------|-----------|-------|-----------|-----------|
| id | dcat:Identifier | Core Identity | High (95%) | Unique system identifier for user |
| username | foaf:name | Core Identity | Medium (75%) | User identifier for authentication |
| email | foaf:mbox | Core Identity | High (90%) | User contact email address |
| fullName | foaf:name | Core Identity | High (95%) | User's full name for display |
| disabled | adms:status | Core Identity | Medium (70%) | Account activation status |
| activeSiteId | comet:siteReference | Core Identity | High (85%) | Reference to active operational site |
| status | adms:status | Core Identity | Medium (70%) | User account state indicator |

---

### 2. Tenant Entity (carbonsig_auth_service)

**Full Term Definition:** An organizational container representing a separate customer/organization with isolated data scope.

**COMET Alignment:**

| Field | COMET Term | Layer | Confidence | Definition |
|-------|-----------|-------|-----------|-----------|
| id | dcat:Identifier | Core Identity | High (95%) | Unique tenant identifier |
| name | skos:name | Core Identity | High (90%) | Organization name |
| code | skos:notation | Core Identity | High (85%) | Short organizational code |
| description | dct:description | Core Identity | Medium (80%) | Organization description |

---

### 3. Site Entity (carbonsig_auth_service)

**Full Term Definition:** A physical or logical operational location/facility within an organization.

**COMET Alignment:**

| Field | COMET Term | Layer | Confidence | Definition |
|-------|-----------|-------|-----------|---------|
| id | dcat:Identifier | Core Identity | High (95%) | Unique site identifier |
| name | skos:name | Core Identity | High (95%) | Site facility name |
| location | dcat:spatial | Core Identity | High (90%) | Geographic location reference |
| type | rdf:type | Core Identity | High (85%) | Facility type classification |
| tenantId | comet:tenantReference | Core Identity | High (95%) | Reference to owning organization |

---

### 4. Country Entity (carbonsig_auth_service)

**Full Term Definition:** A sovereign nation with specific regulatory and geographic context for carbon accounting.

**COMET Alignment:**

| Field | COMET Term | Layer | Confidence | Definition |
|-------|-----------|-------|-----------|---------|
| id | dcat:Identifier | Core Identity | High (95%) | Unique country code |
| code | skos:notation | Core Identity | High (95%) | ISO 3166 country code |
| name | skos:name | Core Identity | High (95%) | Country name |
| region | dcat:spatial | Core Identity | Medium (75%) | Geographic region classification |

---

### 5. Emission Entity (carbonsig_inventory_service)

**Full Term Definition:** A quantified greenhouse gas emission from a specific activity or source with calculation formula and default settings.

**Fields:**
- `id`: Unique identifier
- `title`: Human-readable name
- `formula`: Calculation methodology (e.g., "Activity × Emission Factor")
- `isDefault`: Whether this is the standard calculation method
- `createdBy`: Audit field (from Audit base class)
- `lastModifiedBy`: Audit field (from Audit base class)
- `createdDate`: Audit field (from Audit base class)
- `lastModifiedDate`: Audit field (from Audit base class)

**COMET Alignment:**

| Field | COMET Term | Layer | Confidence | Definition |
|-------|-----------|-------|-----------|---------|
| id | dcat:Identifier | PCF / Activity Data | High (95%) | Unique emission record identifier |
| title | skos:name | PCF | High (90%) | Emission type or source description |
| formula | comet:calculationMethodology | PCF | High (85%) | Mathematical formula for emission calculation |
| isDefault | comet:primaryMethod | PCF | High (80%) | Whether this is the preferred calculation method |
| createdBy | prov:wasAttributedTo | Verification | High (85%) | Creator audit trail |
| createdDate | dct:issued | Verification | High (90%) | Creation timestamp for verification chain |
| lastModifiedBy | prov:wasAttributedTo | Verification | High (80%) | Last modifier audit trail |
| lastModifiedDate | dct:modified | Verification | High (90%) | Last modification timestamp |

---

### 6. CarbonCredit Entity (carbonsig_credits)

**Full Term Definition:** A verified unit of carbon offset or removal eligible for trading or retirement in carbon markets.

**COMET Alignment:**

| Field | COMET Term | Layer | Confidence | Definition |
|-------|-----------|-------|-----------|---------|
| id | dcat:Identifier | Environmental Attributes | High (95%) | Unique credit serial number |
| standard | dct:standard | Environmental Attributes | High (90%) | Verification standard (VCS, Gold Standard, etc.) |
| vintage | comet:vintageYear | Environmental Attributes | High (85%) | Year of credit issuance |
| quantity | qudt:value | Environmental Attributes | High (95%) | Amount of CO2e represented |
| retired | comet:retirementStatus | Market Signals | High (80%) | Whether credit has been retired |

---

### 7. EconomicCategorizationCategory Entity

**Full Term Definition:** High-level classification framework for emissions by economic activity (e.g., Industrial, Commercial, Residential).

**COMET Alignment:**

| Field | COMET Term | Layer | Confidence | Definition |
|-------|-----------|-------|-----------|---------|
| id | dcat:Identifier | Core Identity | High (95%) | Unique category identifier |
| name | skos:name | Core Identity | High (95%) | Category name |
| description | dct:description | Core Identity | Medium (80%) | Category purpose and scope |

---

### 8. EconomicCategorizationSubcategory Entity

**Full Term Definition:** Detailed sub-classification under an economic category for granular emission source tracking.

**COMET Alignment:**

| Field | COMET Term | Layer | Confidence | Definition |
|-------|-----------|-------|-----------|---------|
| id | dcat:Identifier | Core Identity | High (95%) | Unique subcategory identifier |
| categoryId | comet:categoryReference | Core Identity | High (95%) | Reference to parent category |
| name | skos:name | Core Identity | High (95%) | Subcategory name |
| description | dct:description | Core Identity | Medium (80%) | Subcategory purpose and scope |

---

## Mapping Strategy

### Confidence Levels Explained

- **High (85-95%):** Direct semantic alignment with established COMET terms; minimal interpretation needed
- **Medium (70-84%):** Reasonable mapping with some context dependency; requires domain validation
- **Low (<70%):** Loose alignment; may need specialized subtypes or additional context

### Layer Allocation

Entities map primarily to:

1. **Core Identity Layer:** Fundamental organizational and reference data (User, Tenant, Site, Country, Categories)
2. **Supply Chain & Activity Data Layer:** Source data for calculations (Emission)
3. **PCF Layer:** Processed emission values and calculations
4. **Verification & Assurance Layer:** Audit trails and validation metadata
5. **Environmental Attributes Layer:** Offset/credit metadata (CarbonCredit)
6. **Market Signals Layer:** Trading and retirement status

---

## Integration Notes

- **Namespace:** Use `<https://api.carbonsig.com/schemas/entities/>` for CarbonSig entity URIs
- **Audit Fields:** All entities extending the `Audit` base class include creation/modification tracking aligned with `prov:` and `dct:` namespaces
- **Relationships:** This mapping excludes relationship fields (@ManyToOne, @OneToMany, @ManyToMany) as per entity definition conventions; see the carbonsig Verifier Export alignment for relationship mappings
- **JSON-LD Context:** Recommend adding CarbonSig entities to the COMET JSON-LD context for serialization

---

## References

- CarbonSig Entity Definitions: https://github.com/CarbonSigProductHub/carbonsig-entity-definitions
- COMET Ontology Specification: https://nickgogerty.github.io/comet-ontology/ontology.html
- Existing CarbonSig Alignment: `ext/carbonsig/alignments/comet-verifierexport-alignment.ttl`

