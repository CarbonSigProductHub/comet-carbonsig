# COMET, explained for beginners

*No jargon. If you've never heard of COMET, ontologies, or CURIEs, start here.*

---

## The problem COMET solves

Imagine three people describing the **same** steel beam:

- An **ISO 14067** expert calls its climate impact the *"carbon footprint of the product."*
- An **EN 15804** (construction) expert calls it the *"GWP‑total, module A1–A3."*
- An **EU PEF** expert calls it *"climate change, per declared unit."*

They're all talking about the *same real-world thing* — but they use different words. A
computer reading three documents has no way to know these are the same concept. So the data
can't be compared, reused, or added up. Every standard is its own little island with its own
private vocabulary.

**COMET is a shared dictionary that fixes this.** It gives every carbon/environmental concept
**one canonical name**, so a "carbon footprint" means the same thing no matter which standard
you started from. (COMET = *Carbon Ontology for Materials and Emissions Tracking*. An
"ontology" is just a fancy word for a **structured, agreed-upon dictionary of concepts and how
they relate**.)

---

## Two ideas you need (and that's it)

### 1. Every concept gets a web address (a URI)

In COMET, each concept has a unique address on the web, like:

```
https://comet.carbon/ext/pcr#PCRDocument
```

Think of it like a **passport number for an idea**. Anywhere in the world, that address means
exactly one thing: "a Product Category Rules document." No ambiguity.

### 2. A CURIE is a short nickname for that address

Web addresses are long. So COMET uses **CURIEs** — short nicknames. A CURIE has two parts,
a *prefix* and a *name*, joined by a colon:

```
comet-pcr:PCRDocument
└──┬───┘ └────┬────┘
 prefix     name
```

The prefix `comet-pcr:` is shorthand for `https://comet.carbon/ext/pcr#`. So the CURIE
`comet-pcr:PCRDocument` **expands to** the full address
`https://comet.carbon/ext/pcr#PCRDocument`.

> It's exactly like the contacts app on your phone. You type **"Mom"** (short, human‑friendly);
> your phone dials **+1‑555‑0142** (the real, unique number). CURIE = the nickname, URI = the
> real number. The list of prefix→address mappings (`comet-pcr:` → `https://…/ext/pcr#`) is the
> "contacts list," and it lives in a file called `comet-reference.json`.

That's the whole trick. **CURIE in, URI out.** Everything else below is just *using* it.

---

## How the PCR Requirements Builder uses COMET

When you use the builder, each requirement of a PCR (e.g. "Publication date," "Declared unit,"
"Global warming potential") is **tagged with its COMET CURIE** behind the scenes:

| Requirement you see | Hidden COMET tag (CURIE) | What it expands to (URI) |
|---|---|---|
| Publication/issue date | `comet-pcr:PCRDocument.validFrom` | `https://comet.carbon/ext/pcr#PCRDocument.validFrom` |
| Declared unit | `comet-pcf:FunctionalUnit` | `https://comet.carbon/v1/pcf#FunctionalUnit` |
| Programme operator | `comet-pcr:PCRProgramOperator` | `https://comet.carbon/ext/pcr#PCRProgramOperator` |

So the app doesn't just store *"Publication date = 2021‑10‑06."* It stores *"the concept
`comet-pcr:PCRDocument.validFrom` = 2021‑10‑06."* The value now carries a **universal label**
any other system can understand — not just a word that happens to make sense inside this one app.

**Turn on Developer mode** in the builder and you'll literally see these CURIE tags printed in
grey next to each requirement. Export a report as JSON and you'll find a `comet_variables`
block listing, for every field: its CURIE, its resolved URI, its value, and a `simulated` flag.
That block is what makes the export *machine‑usable* instead of just human‑readable.

---

## Why this unlocks the "cross‑standard readiness" score

Here's the payoff. Because every requirement is tagged with a **shared** COMET concept, the app
can answer a question that's normally very hard:

> *"I filled out a report for **one** standard. How much of **other** standards am I already
> ready for?"*

Each standard (ISO 14067, EN 15804, EU PEF, ResponsibleSteel, ASI, TfS PCF, I‑REC(E),
ISO 14068) is defined as a **set of COMET concepts** it requires. The app just checks the
**overlap**:

```
readiness for a standard  =  (COMET concepts you've filled in)  ∩  (concepts that standard needs)
                             ─────────────────────────────────────────────────────────────────────
                                             (concepts that standard needs)
```

That's why, in the demo, a **steel construction** PCR scores **highest on EN 15804 / EU PEF**
(they share lots of concepts) and **0% on I‑REC(E)** — energy‑certificate standards share
*no* concepts with a product footprint, so there's genuinely nothing in common. The number
isn't a guess; it's literal concept overlap. **Shared vocabulary is what makes
"reuse" measurable.**

---

## The "gold master" — where the official dictionary lives

There's one more piece. How do we know a tag like `comet-pcr:PCRDocument` is *real* and not
made up? Because there's a single **source of truth**: the
[`comet-carbonsig`](https://github.com/CarbonSigProductHub/comet-carbonsig) repository. It holds
the official list of every allowed COMET concept (called the **registry**).

- Before shipping, this app **validates** its tags against that registry — so it can't invent
  concepts that don't exist.
- When we found the app needed 15 concepts the registry didn't have yet (things like
  *"End‑of‑Life Scenario,"* *"Review Panel"*), we didn't fudge them locally — we **added them to
  the official dictionary** (a real, reviewed change to `comet-carbonsig`) and then used them.
  That's how a shared vocabulary is supposed to grow: propose, review, publish, then use.

One bug we caught along the way is a nice illustration: the data had tagged a bunch of concepts
with the prefix `comet-pcf:` (the general carbon‑footprint namespace) when they actually live
under `comet-pcr:` (the PCR‑specific namespace) in the official dictionary. Same "name," wrong
"area code." We corrected the prefix so the nicknames point at the right real addresses — which
took the app from 12 to 63 (of 64) tags matching the official registry.

---

## 30‑second recap

1. **Problem:** every standard uses different words for the same concepts → data can't be shared.
2. **COMET:** one shared dictionary; every concept gets a unique web address (**URI**).
3. **CURIE:** a short nickname for that address (`comet-pcr:PCRDocument` → `https://…/ext/pcr#PCRDocument`), like a contact name → phone number.
4. **This app:** tags every requirement with its COMET CURIE, so filled‑in values carry universal, machine‑readable meaning (visible in Developer mode; exported in the JSON `comet_variables` block).
5. **Payoff:** because the vocabulary is shared, the app can measure how ready you are for *other* standards by comparing concept overlap.
6. **Trust:** all tags are validated against the official `comet-carbonsig` dictionary; new concepts are added there properly, not faked locally.

*Want the technical, exhaustive version? See `docs/COMET-COMPLIANCE.md`.*
