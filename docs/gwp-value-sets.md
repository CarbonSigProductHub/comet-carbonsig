# GWP value sets — reconciling carbon data of mixed and indeterminate AR basis

> How COMET records *which* set of global-warming-potential factors produced a
> CO₂e number, why that had to become a registry rather than an enum, and why
> COMET's vocabulary is deliberately wider than PACT's.

## 1. The problem, precisely stated

A GWP is a characterisation factor. The IPCC republishes these with each
Assessment Report, and the values move materially:

| Gas | SAR (1995) | AR4 (2007) | AR5 (2013) | AR6 (2021) |
|---|---|---|---|---|
| CH₄ (GWP-100) | 21 | 25 | 28 | 29.8 fossil / 27.0 non-fossil |
| N₂O (GWP-100) | 310 | 298 | 265 | 273 |

A CO₂e figure is only interpretable if you know which set produced it. And the
moment gas-level data is multiplied by a GWP and summed, the basis becomes
**unrecoverable from the number alone**. Inbound data arrives at three levels of
surviving provenance:

- **Type A — tagged.** The basis travels with the data (a machine-readable tag). A schema problem, solved by a field.
- **Type B — recoverable.** No tag, but the gas split and the CO₂e total survive, so the basis can be *back-solved* arithmetically.
- **Type C — indeterminate.** Only a bare CO₂e number survives. The honest answer is "we do not fully know."

## 2. Why an enum was the wrong shape

The prior model was `ipccAR : Enum(AR5, AR6)`. It has three defects, and only
the first is about coverage:

1. **It cannot represent AR4 or SAR.** Both are live. California ARB runs its
   emissions inventory on AR4; US EPA GHGRP reporting years RY2010–RY2023 are an
   AR4 archive that feeds many corporate Scope 1 inventories; Verra VCS permits
   AR4 conversion for pre-2021 vintages, and credits do not expire. SAR — not
   AR4 — is the true floor, because transitioned Kyoto-era CERs carry SAR-basis
   values and trade indefinitely.

2. **It cannot distinguish a *declared* basis from an *inferred* one.** The
   provenance — how we came to believe the basis — is exactly what a verifier
   needs, and the enum throws it away.

3. **It has no null-safe "indeterminate" value.** A Type-C factor must either
   assert something false or drop out of the graph entirely.

The sharper defect sits underneath all three: **naming the edition does not pin
the numbers.** There are at least five distinct value sets hiding behind three
edition labels:

- AR5 published GWP-100 both **without** and **with** climate-carbon feedbacks. A bare "AR5" tag does not say which. (The GHG Protocol convention is the no-feedback set.)
- UNFCCC Decision 7/CP.27 adopted AR5 Table 8.A.1 **excluding the fossil-methane value** for the Paris Enhanced Transparency Framework — a third AR5 variant.
- AR6 introduced a **fossil vs non-fossil (biogenic) methane** distinction earlier editions lack. The GHG Protocol's August 2024 table directs the fossil value for fugitive emissions from oil, gas and coal and for fossil-origin industrial processes.

An enum keyed on edition is therefore under-determined *by construction*, not by
coverage. Adding "AR4" makes it a four-value enum that is still wrong for the
same structural reason, and it must be re-amended at every new Assessment Report
— AR7 lands around the UNFCCC's commitment to reconsider common-metric values no
later than 2028.

## 3. The fix: a value-set registry, not an enum

Key the field on the value **set** — edition *plus* variant — and hold the sets
in a versioned, machine-readable registry. Extension at AR7 becomes a registry
entry, not a schema amendment.

| Aspect | Before | After |
|---|---|---|
| Vocabulary form | closed enum | SKOS concept scheme in the registry |
| Members | AR5, AR6 | SAR, AR4, AR5-noFeedback, AR5-withFeedback, AR5-UNFCCC, AR6-fossilCH4, AR6-biogenicCH4 |
| Identity | edition label | edition **+ variant** (feedbacks, fossil-CH₄ treatment) |
| Extension at AR7 | schema change | registry entry |

This reuses COMET's existing machinery rather than inventing any: the CURIE
registry (`registry/comet-curies.json`, rebuilt by `tools/build_registry.py`)
and the SKOS-concept-scheme pattern already used by `comet-pcr:moduleScheme`.

### The `ipcc:` vocabulary — `extensions/ipcc-gwp.ttl`

Namespace `https://comet.carbon/vocab/ipcc-gwp#`. Each value set is a
`ipcc:GWPValueSet` concept carrying its edition, variant, publication year,
sourced witness GWP-100 values, and PACT-exportability. The differences between
sets are asserted as **machine-checkable relations** — `ipcc:differsFrom` with
`ipcc:onGas` — so a consumer can prove that two edition-sharing sets are not
interchangeable without recomputing:

```turtle
ipcc:AR5-UNFCCC  ipcc:differsFrom ipcc:AR5-noFeedback ; ipcc:onGas "CH4-fossil" .
ipcc:AR6-biogenicCH4  ipcc:differsFrom ipcc:AR6-fossilCH4 ; ipcc:onGas "CH4" .
```

### The four provenance properties — on `comet-ef:GWP100Value`

Defined in `comet-pcr:` (candidate to upstream onto `comet-ef` core):

| Property | Meaning |
|---|---|
| `comet-pcr:gwpValueSet` | CURIE into `ipcc:`. **Absent = indeterminate** (null-safe). |
| `comet-pcr:arBasis` | `Declared` / `BackSolved` / `Inferred` / `Indeterminate` |
| `comet-pcr:arConfidence` | decimal [0,1], **required when inferred** |
| `comet-pcr:gwpHorizon` | `GWP100` / `GWP20` (default GWP100) |

`comet-pcr:informedByRule` links the factor to the `comet-ver:DataSubstitutionRule`
that assigned the basis, so AR inference lands inside the existing verification
findings workflow.

SHACL shapes (`extensions/comet-pcr-shapes.ttl`) make all of this checkable:
inferred ⇒ confidence present; indeterminate ⇒ no value set; confidence in
[0,1]; value set drawn from the `ipcc:` scheme. Validated against
`extensions/examples/gwp-provenance-{valid,invalid}.ttl`.

## 4. Resolution order — cheapest determinate test first

Read the tag; failing that, back-solve; only then infer.

1. **Declared.** Honour the tag. Determinate (Type A).
2. **Back-solve.** If the gas split and CO₂e total survive, the basis is
   *arithmetically* recoverable. Since CO₂e = Σ(massᵢ × GWPᵢ), test each
   candidate value set and keep the one that reproduces the total. This is not
   inference — it is a determinate solve that converts a Type-B factor into
   effectively Type-A, and it should run at ingest before any model.

   > **Worked back-solve.** 1 kg CH₄ + 1 kg N₂O reported as **323** kg CO₂e is
   > AR4 (25 + 298). As **293** it is AR5-noFeedback (28 + 265). As **~303** it
   > is AR6-fossil (29.8 + 273). The witness values in `ipcc:hasGWP` are exactly
   > what this solve keys on — the routine is only as good as the encoded sets.
3. **Infer.** For factors that survive back-solve, a model estimates
   P(value set | source, vintage, unit, sector, gas hints); vintage alone is
   highly predictive. Records `arBasis = Inferred` with `arConfidence`.
4. **Flag.** Otherwise `arBasis = Indeterminate`, no value set asserted.

## 5. Why COMET is wider than PACT — the divergence, and the BLOCK

PACT is the closest existing convention: its `ipccCharacterizationFactors` field
carries an edition tag, and PACT v3 mandates AR6 GWP-100 (Kyoto gases + NF₃),
treating a mix of AR5 and AR6 in one PCF as non-conformant. COMET **adopts that
field verbatim on export** for interoperability — but PACT's enum names only an
*edition*, so it cannot express SAR, AR4, or the variant distinctions.

That forces a deliberate design choice, and COMET takes the wider side:

> **The ontology describes the world faithfully; the export layer enforces what
> each destination accepts.**

Making COMET narrower to match PACT would push AR4 and SAR back into free text —
which is where the problem started. So instead the two conformance regimes
legitimately **diverge**, and the divergence is enforced in the converters, not
the ontology:

- **`comet_to_pact.py`** collapses `gwpValueSet` to its PACT edition where one
  exists (AR5-* → `AR5`, AR6-* → `AR6`). For SAR, AR4, or an indeterminate
  factor there is no honest edition — the converter **omits**
  `characterizationFactors` and warns, rather than assert a false edition. This
  is the **BLOCK** condition: such a factor is non-declarable into a PACT (or a
  regulated) channel until its basis is resolved. That converts an abstract
  data-quality concern into a hard business consequence — and makes primary-data
  chasing actionable, because rescuing one supplier factor by back-solve becomes
  the difference between being able to file and not.

- **`pact_to_comet.py`** runs the other way: it upgrades PACT's lossy edition
  tag to that edition's conventional value set (AR6 → `ipcc:AR6-fossilCH4`,
  AR5 → `ipcc:AR5-noFeedback`) and records `arBasis = declared`. The variant PACT
  could not express is restored to the COMET default; `ipccAR` is kept verbatim
  for round-trip fidelity.

## 6. Files

| File | Role |
|---|---|
| `extensions/ipcc-gwp.ttl` | the `ipcc:` value-set vocabulary (7 sets + witness GWPs + relations) |
| `extensions/comet-pcr.ttl` | the 4 provenance properties + arBasis / horizon schemes |
| `extensions/comet-pcr-shapes.ttl` | SHACL shapes making it machine-checkable |
| `extensions/examples/gwp-provenance-{valid,invalid}.ttl` | validated instances |
| `tools/schemas/comet-pcf.schema.json` | `gwpValueSet`/`arBasis`/`arConfidence`/`gwpHorizon`; `ipccAR` deprecated |
| `tools/converters/comet_to_pact.py` | export collapse + BLOCK |
| `tools/converters/pact_to_comet.py` | import edition → value-set upgrade |
| `registry/namespaces.json`, `registry/comet-curies.json` | `ipcc` prefix + harvested CURIEs |

---
*Source: CarbonSig GWP/AR reconciliation working group. Witness GWP-100 values
each carry a `dcterms:source` in `ipcc-gwp.ttl`; extend gas-by-gas only with a
primary citation. Regulatory positions (esp. US EPA GHGRP Table A-1 under the
April 2024 rule, and any EU ETS/CBAM gas-level specifics) should be checked
against the current eCFR / EU regulation before being relied on.*
