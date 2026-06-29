# COMET PCR Japan Extension

**Module:** `comet-ext:pcr-japan` · **Version:** 0.1.0 · **Status:** RFC Open  
**Namespace:** `https://comet.carbon/ext/pcr-japan#` (prefix: `comet-pj:`)

---

## What this extension adds

This COMET extension models **SuMPO EPD Japan (EcoLeaf)** Product Category Rules as structured semantic data. SuMPO (Sustainable Management Promotion Organization, 一般社団法人サステナブル経営推進機構) operates Japan's primary EPD program, publishing PCRs under ISO 21930:2007, ISO 21930:2017, EN 15804+A1:2013, and EN 15804+A2:2019.

**Evidence base:** 76 PCRs and 85 bilingual (Japanese + English) requirements harvested from [ecoleaf-label.jp](https://ecoleaf-label.jp/en/pcr/search) via [PCRbase](https://nickgogerty.github.io/pcrbase).

---

## New classes

| Class | Description | Japanese |
|---|---|---|
| `comet-pj:SuMPOPCRDocument` | PCR document issued by SuMPO EcoLeaf (subClassOf `comet-pcf:PCRDocument`) | SuMPO PCR文書 |
| `comet-pj:EcoLeafDeclaration` | EPD under EcoLeaf program (subClassOf `comet-eac:Certification`) | エコリーフ環境ラベル宣言 |
| `comet-pj:ISO21930PCR` | PCR formally complying with ISO 21930 | ISO 21930 PCR |
| `comet-pj:LegacyEcoLeafPCR` | Pre-2024 PCR in PA-NNNNNN-XX-NN format | 旧エコリーフPCR |
| `comet-pj:JapanesePCRField` | SKOS concept scheme — 13 product fields | SuMPO製品分野分類 |

## New properties

| Property | Domain → Range | Description |
|---|---|---|
| `comet-pj:pcrRegistrationNumber` | `SuMPOPCRDocument → xsd:string` | Official registration number (PA-…) |
| `comet-pj:pcrOverviewJa` | `SuMPOPCRDocument → rdf:langString @ja` | Scope text verbatim in Japanese |
| `comet-pj:validityPeriodJa` | `SuMPOPCRDocument → rdf:langString @ja` | Validity period in Japanese |
| `comet-pj:workingGroupMember` | `SuMPOPCRDocument → schema:Organization` | PCR WG member organization |
| `comet-pj:japanesePCRField` | `SuMPOPCRDocument → JapanesePCRField` | Product field classification |

## Named individual

`comet-pj:SuMPOOperator` — the SuMPO organization as a `comet-pcf:PCRProgramOperator`.

---

## SKOS Product Field Taxonomy

13 top-level concepts mapping SuMPO product fields to SKOS:

| Concept | English | Japanese |
|---|---|---|
| `comet-pj:ConstructionProducts` | Construction products | 建設製品 |
| `comet-pj:MachineryEquipment` | Machinery & equipment | 機械・設備 |
| `comet-pj:FoodBeverages` | Food & beverages | 食品・飲料 |
| `comet-pj:ChemicalProducts` | Chemical products | 化学製品 |
| `comet-pj:MetalMineralPlasticGlass` | Metal, mineral, plastic & glass | 金属・鉱物・プラスチック・ガラス製品 |
| `comet-pj:PaperPlasticProducts` | Paper and plastic products | 紙・プラスチック製品 |
| `comet-pj:TextilesFootwearApparel` | Textiles, footwear & apparel | 繊維・履物・衣料品 |
| `comet-pj:FurnitureOtherGoods` | Furniture & other goods | 家具・その他製品 |
| `comet-pj:VehiclesTransportEquipment` | Vehicles & transport equipment | 車両・輸送機器 |
| `comet-pj:ElectricitySteamFuels` | Electricity, steam & fuels | 電力・蒸気・燃料 |
| `comet-pj:InfrastructureBuildings` | Infrastructure & buildings | インフラ・建物 |
| `comet-pj:Services` | Services | サービス |
| `comet-pj:Others` | Others | その他 |

---

## Japanese language support (`labels/labels-ja.ttl`)

Provides `rdfs:label @ja` and `skos:prefLabel @ja` for:
- All `comet:` core classes (ProductCarbonFootprint, FunctionalUnit, SystemBoundary, etc.)
- All `comet-pcf:` classes (PCRDocument, DeclaredModule, CutOffRule, etc.)
- All `comet-pj:` extension classes and properties
- All 65 PCRbase clause vocabulary keys (as `pcrbase:clause/*` URIs)

This enables cross-lingual SPARQL queries over bilingual PCR requirements.

---

## Usage — Turtle

```turtle
@prefix comet-pj: <https://comet.carbon/ext/pcr-japan#> .
@prefix comet-pcf: <https://comet.carbon/v1/pcf#> .
@prefix dcterms:   <http://purl.org/dc/terms/> .
@prefix xsd:       <http://www.w3.org/2001/XMLSchema#> .

# A SuMPO cement PCR as a COMET document
ex:cement-pcr
    a comet-pj:SuMPOPCRDocument , comet-pj:ISO21930PCR ;
    dcterms:title "Cement"@en , "セメント"@ja ;
    comet-pj:pcrRegistrationNumber "PA-SuMPO-PCR-01003-1-0-0" ;
    comet-pcf:programOperator comet-pj:SuMPOOperator ;
    comet-pj:japanesePCRField comet-pj:ConstructionProducts ;
    comet-pcf:validUntil "2031-05-25"^^xsd:date ;
    comet-pj:pcrOverviewJa
        "ポルトランドセメント、混合セメント、エコセメントを対象とする。"@ja .

# An EPD governed by this PCR
ex:cement-epd-001
    a comet-eac:Certification ;
    comet-pcf:governedByPCR ex:cement-pcr .
```

---

## Usage — SPARQL (bilingual query)

```sparql
PREFIX comet-pj: <https://comet.carbon/ext/pcr-japan#>
PREFIX comet-pcf: <https://comet.carbon/v1/pcf#>
PREFIX pcrbase:  <https://pcrbase.org/v1/>

# Find all SuMPO construction PCRs with their Japanese scope text
SELECT ?pcr ?title_en ?title_ja ?overview_ja ?field WHERE {
    ?pcr a comet-pj:SuMPOPCRDocument ;
         dcterms:title ?title_en , ?title_ja ;
         comet-pj:japanesePCRField ?field ;
         comet-pj:pcrOverviewJa ?overview_ja .
    FILTER(lang(?title_en) = "en")
    FILTER(lang(?title_ja) = "ja")
    FILTER(lang(?overview_ja) = "ja")
    ?field a skos:Concept .
}
```

---

## Files

| File | Description |
|---|---|
| `comet-ext-pcr-japan.ttl` | Main ontology — classes, properties, SKOS scheme, SuMPO operator individual |
| `comet-ext-pcr-japan-shapes.ttl` | SHACL validation shapes |
| `labels/labels-ja.ttl` | Japanese labels — COMET core, PCF, and PCR-Japan extension (85 terms) |
| `examples/cement-pcr.ttl` | 3 worked examples: Cement, Steel, Rice PCRs |

---

## Governance

- **Status:** RFC Open — seeking community review before promotion to Draft
- **Domain WG:** PCRbase (nickgogerty@gmail.com)
- **Data source:** [PCRbase](https://nickgogerty.github.io/pcrbase) — open, quarterly updated
- **Upstream PRs welcome:** especially for `japanesePCRField` alignment to UN CPC codes and ISO 14025 Annex B product categories

---

## Links

- [SuMPO EPD Japan](https://ecoleaf-label.jp/en/)
- [PCRbase data source](https://nickgogerty.github.io/pcrbase)
- [COMET core ontology](https://nickgogerty.github.io/comet-ontology/)
- [ISO 21930:2017](https://www.iso.org/standard/61694.html)
