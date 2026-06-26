# CarbonSig extension

Alignment of the **CarbonSig Verifier Hub export contract (v4)** to COMET.

CarbonSig is a carbon-accounting platform whose Verifier Hub export is a
graph-oriented payload (systems → processes + flows → declaration) that drives
verifier-facing Excel workbooks. This extension crosswalks that contract onto the
COMET seven-layer stack so a CarbonSig export can join the COMET graph.

## Contents

| File | Purpose |
| --- | --- |
| `alignments/comet-verifierexport-alignment.ttl` | SKOS alignment: COMET term → `csig:` field, with a `[certainty: High/Medium/Low]` note on each target. |

The alignment is **generated** from the crosswalk source of truth in the
CarbonSig repo (`packages/comet-mapping/src/crosswalk.ts` in
`CarbonSigProductHub/verifier-export`) — do not hand-edit the TTL there or here;
regenerate it upstream.

74 of 87 contract fields map to a COMET term (High 30 · Medium 37 · Low 7). The
build (`tools/scripts/build-ontology-map.py`, which registers the `csig:` prefix)
ingests this file into `docs/ontology-data.json` as 74 alignment rows under the
standard **CarbonSig Verifier Export v4**.

### Layer coverage

- **L2 Emission Factor** — `EmissionFactor` value/unit/source/geography
- **L3 Supply Chain** — flows, activity data, scope 1/2/3, transport
- **L4 PCF** — system boundary, declaration, declared products, intensity
- **L1 Core** — processes, sites, time periods, units
- **L6 Verification** — `verificationStatus` → assurance level
- **ISO 14068 ext** — product offset `credits`
