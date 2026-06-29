/* ──────────────────────────────────────────────────────────────────────
   COMET newcomer tooltips — auto-glossary.
   Wraps the FIRST occurrence of each known term in body prose with a
   .cterm span carrying a plain-language definition. No dependencies.

   Design rules:
   - Only the first match per term per page (avoids underline spam).
   - Skips headings, code, pre, a, button, and anything already inside .cterm.
   - Case-insensitive whole-word/phrase match; longer phrases match first.
   - Touch: tap toggles the bubble; tapping elsewhere closes it.
   ────────────────────────────────────────────────────────────────────── */
(function () {
  "use strict";

  // term (lower-case) -> plain-language definition for a newcomer.
  var GLOSSARY = {
    "ontology": "A shared, structured dictionary: an agreed list of terms (classes and properties) and how they relate, so different systems mean the same thing by the same word.",
    "pcf": "Product Carbon Footprint — the total greenhouse-gas emissions tied to one product, across its life cycle, expressed as kg of CO\u2082-equivalent.",
    "product carbon footprint": "The total greenhouse-gas emissions tied to one product across its life cycle, in kg CO\u2082-equivalent (per ISO 14067).",
    "epd": "Environmental Product Declaration — a verified, standardised label reporting a product's environmental impacts (a PCR defines the rules an EPD must follow).",
    "pcr": "Product Category Rules — the methodology rulebook that says how to calculate and report the footprint for a whole category of products. One PCR governs many EPDs.",
    "eac": "Environmental Attribute Certificate — a tradeable proof that one unit of an environmental benefit (e.g. a tonne of CO\u2082 removed, or a MWh of green power) happened. Carbon credits and renewable-energy certificates are EACs.",
    "shacl": "A W3C language for writing validation rules ('shapes') that check whether data follows an ontology's constraints \u2014 like a spell-checker for structured data.",
    "json-ld": "A way to write JSON so each field is linked to a shared vocabulary, turning ordinary JSON into machine-meaningful linked data.",
    "owl": "Web Ontology Language — the W3C standard for formally defining classes, properties and relationships in an ontology.",
    "rdf": "Resource Description Framework — the W3C data model that expresses facts as simple subject\u2013predicate\u2013object triples.",
    "turtle": "A compact, human-readable text format for writing RDF triples.",
    "namespace": "A prefix that groups related terms and keeps their names unique \u2014 e.g. everything starting 'comet-pcf:' belongs to the Product Carbon Footprint layer.",
    "crosswalk": "A mapping that says 'this term here means the same as that term in another standard', so data can move between standards without losing meaning.",
    "alignment": "A recorded link between a COMET term and an equivalent term in an external standard (a crosswalk).",
    "class": "A type of thing in an ontology (e.g. Organization, Site) \u2014 the template that individual records are instances of.",
    "property": "An attribute or relationship on a class (e.g. an Organization's legal name, or a footprint's emission value).",
    "emission factor": "A conversion number that turns an activity (e.g. 1 kWh of grid electricity) into its greenhouse-gas emissions.",
    "gwp": "Global Warming Potential \u2014 a factor that converts each greenhouse gas into a common CO\u2082-equivalent over a 100-year horizon.",
    "scope 1": "Direct emissions from sources a company owns or controls (e.g. its own boilers and vehicles).",
    "scope 2": "Indirect emissions from the energy a company buys (electricity, heat, steam).",
    "scope 3": "All other indirect emissions across a company's value chain (suppliers, transport, product use) \u2014 usually the largest and hardest to measure, split into 15 categories.",
    "cbam": "EU Carbon Border Adjustment Mechanism \u2014 a charge on the embedded carbon of certain imports (steel, cement, aluminium, etc.) to match the EU's own carbon price.",
    "corsia": "The UN aviation scheme (ICAO) requiring airlines to offset growth in international flight emissions.",
    "verification": "Independent third-party checking that a footprint or claim was calculated correctly and can be trusted.",
    "assurance": "The level of confidence a verifier provides: 'limited' (a lighter review) or 'reasonable' (a deeper, audit-grade review).",
    "materiality": "The threshold (often 5%) below which an error is considered too small to change the conclusion.",
    "system boundary": "Which life-cycle stages are included in a footprint \u2014 e.g. 'cradle-to-gate' (raw materials to factory exit) vs 'cradle-to-grave' (all the way to disposal).",
    "functional unit": "The precise unit a footprint is measured per \u2014 e.g. 'per 1 kg of product' or 'per 1 m\u00b2 of flooring' \u2014 so products can be compared fairly.",
    "life cycle assessment": "A method that totals a product's environmental impacts across every stage of its life, from raw materials to disposal.",
    "lca": "Life Cycle Assessment \u2014 totalling a product's environmental impacts across every stage of its life.",
    "iso 14067": "The international standard defining how to quantify a product's carbon footprint.",
    "iso 14025": "The international standard for Type III environmental declarations (EPDs) and the PCRs behind them.",
    "en 15804": "The European standard giving the core PCR for construction products' EPDs.",
    "ghg protocol": "The most widely used corporate greenhouse-gas accounting standard, source of the Scope 1/2/3 framework.",
    "issb": "International Sustainability Standards Board \u2014 sets global corporate climate-disclosure standards (IFRS S2).",
    "esrs": "European Sustainability Reporting Standards \u2014 the EU's mandatory corporate sustainability disclosure rules (CSRD).",
    "taxonomy": "A classification scheme that organises terms into groups and layers.",
    "provenance": "The traceable record of where a piece of data came from and how it was produced."
  };

  // Only run inside readable prose containers; never touch these.
  var SKIP_TAGS = { H1:1, H2:1, H3:1, H4:1, H5:1, H6:1, CODE:1, PRE:1, A:1,
                    BUTTON:1, SCRIPT:1, STYLE:1, SVG:1, CANVAS:1, TEXTAREA:1,
                    INPUT:1, SELECT:1, OPTION:1, TH:1 };

  function esc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

  // Build one regex, longest phrases first so 'product carbon footprint'
  // wins over 'pcf' etc.
  var terms = Object.keys(GLOSSARY).sort(function (a, b) { return b.length - a.length; });
  var used = {};                       // term -> already wrapped once
  var pattern = new RegExp("\\b(" + terms.map(esc).join("|") + ")\\b", "i");

  function inSkip(node) {
    for (var p = node.parentNode; p && p.nodeType === 1; p = p.parentNode) {
      if (SKIP_TAGS[p.tagName]) return true;
      if (p.classList && p.classList.contains("cterm")) return true;
      if (p.classList && p.classList.contains("no-tip")) return true;
    }
    return false;
  }

  function wrapTextNode(textNode) {
    var text = textNode.nodeValue;
    var m = pattern.exec(text);
    if (!m) return;
    var key = m[1].toLowerCase();
    if (used[key]) {
      // already used this term: blank it from the live regex by retrying
      // on the remainder only after this match position.
      var after = text.slice(m.index + m[1].length);
      // recurse on the tail via a temporary node swap
      var tailNode = document.createTextNode(after);
      textNode.nodeValue = text.slice(0, m.index + m[1].length);
      textNode.parentNode.insertBefore(tailNode, textNode.nextSibling);
      wrapTextNode(tailNode);
      return;
    }
    used[key] = true;

    var before = text.slice(0, m.index);
    var match = m[1];
    var after = text.slice(m.index + match.length);

    var span = document.createElement("span");
    span.className = "cterm";
    span.setAttribute("data-tip", GLOSSARY[key]);
    span.setAttribute("tabindex", "0");
    span.textContent = match;

    var frag = document.createDocumentFragment();
    if (before) frag.appendChild(document.createTextNode(before));
    frag.appendChild(span);
    var tail = document.createTextNode(after);
    frag.appendChild(tail);

    var parent = textNode.parentNode;
    parent.replaceChild(frag, textNode);

    // edge-flip if the term sits in the right third of the viewport
    requestAnimationFrame(function () {
      var r = span.getBoundingClientRect();
      if (r.left > window.innerWidth * 0.62) span.setAttribute("data-tip-align", "right");
    });

    if (after) wrapTextNode(tail);
  }

  function walk(root) {
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        if (!n.nodeValue || !n.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        if (inSkip(n)) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var nodes = [];
    var n;
    while ((n = walker.nextNode())) nodes.push(n);
    nodes.forEach(function (node) {
      if (Object.keys(used).length >= terms.length) return;
      if (node.parentNode) wrapTextNode(node);
    });
  }

  function injectLegend() {
    var main = document.querySelector("main, .page, .wrap, body");
    if (!main) return;
    var chip = document.createElement("div");
    chip.className = "cterm-legend no-tip";
    chip.innerHTML = "\uD83D\uDCA1 New here? <b>Dotted-underlined</b> terms have plain-language explanations \u2014 hover or tap them.";
    main.insertBefore(chip, main.firstChild);
  }

  function init() {
    var scope = document.querySelector("main, .page, .wrap") || document.body;
    walk(scope);
    injectLegend();

    // touch: tap toggles, tap-away closes
    document.addEventListener("click", function (e) {
      var t = e.target.closest(".cterm");
      document.querySelectorAll(".cterm.cterm-open").forEach(function (el) {
        if (el !== t) el.classList.remove("cterm-open");
      });
      if (t) t.classList.toggle("cterm-open");
    });
    // keyboard: Esc closes
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape")
        document.querySelectorAll(".cterm.cterm-open").forEach(function (el) {
          el.classList.remove("cterm-open");
        });
    });
  }

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", init);
  else init();
})();
