#!/usr/bin/env python3
"""
COMET CLI — Unified command-line interface for COMET ontology tools.

Commands:
    comet validate <file>              Validate a COMET JSON-LD file
    comet convert <input> --from <fmt> --to comet   Convert to COMET
    comet export <input> --to <fmt>                  Export from COMET
    comet template <type>                            Generate blank template

Usage:
    python comet_cli.py validate steel-pcf.comet.json
    python comet_cli.py convert data.csv --from csv --to comet
    python comet_cli.py export steel-pcf.comet.json --to pact
    python comet_cli.py template pcf --output my-template.json
"""

import argparse
import json
import sys
from pathlib import Path

# ── Terminal colors ─────────────────────────────────────────────────────
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def disable(cls):
        for attr in ("RED", "GREEN", "YELLOW", "CYAN", "BOLD", "DIM", "RESET"):
            setattr(cls, attr, "")


if not sys.stdout.isatty():
    Colors.disable()


TOOLS_DIR = Path(__file__).resolve().parent
SCHEMAS_DIR = TOOLS_DIR / "schemas"
TEMPLATES_DIR = TOOLS_DIR / "templates"
CONVERTERS_DIR = TOOLS_DIR / "converters"
VALIDATORS_DIR = TOOLS_DIR / "validators"

# ── Supported formats ───────────────────────────────────────────────────
INGEST_FORMATS = ["csv", "pact", "cbam-xml", "cad-trust",
                  "ghg-protocol", "esrs", "45v", "epd", "corsia",
                  "verra", "gold-standard", "irec"]
EXPORT_FORMATS = ["pact", "cbam-xml", "csv"]
TEMPLATE_TYPES = ["pcf", "eac", "scope3"]


# ── Helpers ─────────────────────────────────────────────────────────────
def error(msg: str) -> None:
    print(f"{Colors.RED}Error:{Colors.RESET} {msg}", file=sys.stderr)


def success(msg: str) -> None:
    print(f"{Colors.GREEN}OK:{Colors.RESET} {msg}")


def info(msg: str) -> None:
    print(f"{Colors.CYAN}Info:{Colors.RESET} {msg}")


def write_output(content: str, output_path: str | None, pretty: bool = False) -> None:
    """Write content to a file or stdout."""
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        success(f"Written to {path}")
    else:
        print(content)


# ── VALIDATE command ────────────────────────────────────────────────────
def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a COMET JSON-LD file against its schema."""
    # Import validator
    sys.path.insert(0, str(VALIDATORS_DIR))
    try:
        from validate import validate_file, validate_batch, validate_to_json
    except ImportError as e:
        error(f"Could not import validator: {e}")
        return 1

    file_path = Path(args.file)

    if file_path.is_dir():
        ok = validate_batch(file_path, strict=args.strict, quiet=args.quiet)
        return 0 if ok else 1

    if args.json_output:
        print(validate_to_json(file_path, strict=args.strict))
        result = json.loads(validate_to_json(file_path, strict=args.strict))
        return 0 if result["valid"] else 1

    ok = validate_file(file_path, strict=args.strict, quiet=args.quiet)
    return 0 if ok else 1


# ── CONVERT command ─────────────────────────────────────────────────────
def cmd_convert(args: argparse.Namespace) -> int:
    """Convert an external format into COMET JSON-LD."""
    input_path = Path(args.input)
    if not input_path.exists():
        error(f"Input file not found: {input_path}")
        return 1

    from_fmt = args.from_format
    converter_map = {
        "csv": "csv_to_comet",
        "pact": "pact_to_comet",
        "cbam-xml": "cbam_to_comet",
        "cad-trust": "cad_trust_to_comet",
        # v0.3.0 carbon-verification-market converters
        "ghg-protocol": "ghgprotocol_to_comet",
        "esrs": "ghgprotocol_to_comet",
        "45v": "h45v_to_comet",
        "epd": "epd_to_comet",
        "corsia": "corsia_to_comet",
        "verra": "verra_to_comet",
        "gold-standard": "verra_to_comet",
        "irec": "irec_to_comet",
    }

    module_name = converter_map.get(from_fmt)
    if not module_name:
        error(f"Unknown input format: {from_fmt}. Supported: {', '.join(INGEST_FORMATS)}")
        return 1

    module_path = CONVERTERS_DIR / f"{module_name}.py"
    if not module_path.exists():
        error(
            f"Converter '{module_name}.py' not yet implemented.\n"
            f"  Expected at: {module_path}\n"
            f"  This converter is planned — see TOOLS_SPEC.md section B."
        )
        return 1

    # Dynamic import of the converter module
    sys.path.insert(0, str(CONVERTERS_DIR))
    try:
        converter = __import__(module_name)
    except ImportError as e:
        error(f"Could not import converter {module_name}: {e}")
        return 1

    if not hasattr(converter, "convert"):
        error(f"Converter {module_name} missing 'convert()' function.")
        return 1

    try:
        result = converter.convert(str(input_path))
        if isinstance(result, dict):
            indent = 2 if args.pretty else None
            output = json.dumps(result, indent=indent, ensure_ascii=False)
        elif isinstance(result, list):
            indent = 2 if args.pretty else None
            output = json.dumps(result, indent=indent, ensure_ascii=False)
        else:
            output = str(result)
        write_output(output, args.output, pretty=args.pretty)
        return 0
    except Exception as e:
        error(f"Conversion failed: {e}")
        return 1


# ── EXPORT command ──────────────────────────────────────────────────────
def cmd_export(args: argparse.Namespace) -> int:
    """Export COMET JSON-LD to an external format."""
    input_path = Path(args.input)
    if not input_path.exists():
        error(f"Input file not found: {input_path}")
        return 1

    to_fmt = args.to_format
    exporter_map = {
        "pact": "comet_to_pact",
        "cbam-xml": "comet_to_cbam",
        "csv": "comet_to_csv",
    }

    module_name = exporter_map.get(to_fmt)
    if not module_name:
        error(f"Unknown export format: {to_fmt}. Supported: {', '.join(EXPORT_FORMATS)}")
        return 1

    module_path = CONVERTERS_DIR / f"{module_name}.py"
    if not module_path.exists():
        error(
            f"Exporter '{module_name}.py' not yet implemented.\n"
            f"  Expected at: {module_path}\n"
            f"  This exporter is planned — see TOOLS_SPEC.md section C."
        )
        return 1

    sys.path.insert(0, str(CONVERTERS_DIR))
    try:
        exporter = __import__(module_name)
    except ImportError as e:
        error(f"Could not import exporter {module_name}: {e}")
        return 1

    if not hasattr(exporter, "export"):
        error(f"Exporter {module_name} missing 'export()' function.")
        return 1

    try:
        result = exporter.export(str(input_path))
        if isinstance(result, dict) or isinstance(result, list):
            indent = 2 if args.pretty else None
            output = json.dumps(result, indent=indent, ensure_ascii=False)
        else:
            output = str(result)
        write_output(output, args.output, pretty=args.pretty)
        return 0
    except Exception as e:
        error(f"Export failed: {e}")
        return 1


# ── TEMPLATE command ────────────────────────────────────────────────────

# Built-in JSON-LD templates
PCF_TEMPLATE = {
    "@context": [
        "https://wbcsd.github.io/pact/v3/context.json",
        "https://comet.carbon/v1/jsonld/context.json",
    ],
    "@type": "comet-pcf:ProductCarbonFootprint",
    "pcfId": "YOUR-UUID-HERE",
    "declaredUnit": "kilogram",
    "unitaryProductAmount": 1,
    "fossilGWP": 0.0,
    "totalGWP": None,
    "fossilEmissions": None,
    "biogenicCarbonContent": 0,
    "biogenicUptake": 0,
    "landUseChange": 0,
    "aircraftEmissions": 0,
    "packagingEmissions": 0,
    "exemptedPercent": 0,
    "ipccAR": "AR6",
    "standardRef": ["ISO14067"],
    "pcrName": None,
    "allocationDescription": None,
    "boundaryDescription": "Cradle-to-gate",
    "referencePeriod": {
        "startDate": "2024-01-01T00:00:00Z",
        "endDate": "2024-12-31T23:59:59Z",
    },
    "organization": {
        "orgName": "Your Company Name",
        "orgId": [],
        "country": "XX",
    },
    "material": {
        "materialName": "Your Product Name",
        "materialId": [],
        "cpcCode": "",
        "tradeName": "",
    },
    "site": {
        "siteCountry": "XX",
        "region": "",
    },
    "primaryDataShare": 0,
    "dqi": {
        "coveragePercent": 0,
        "technologyDQI": 3,
        "temporalityDQI": 3,
        "geographyDQI": 3,
        "reliabilityDQI": 3,
    },
    "verification": {
        "hasAssurance": False,
        "levelType": "limited",
        "verifierName": "",
        "verificationDate": "",
        "standardRef": "",
    },
}

EAC_TEMPLATE = {
    "@context": [
        "https://comet.carbon/v1/jsonld/context.json",
        "https://climateactiondata.org/api/v2/context.json",
    ],
    "@type": "comet-eac:CarbonRemovalCertificate",
    "eacId": "YOUR-UUID-HERE",
    "eacType": "CarbonRemovalCertificate",
    "subType": "",
    "serialNumber": "",
    "unitType": "Removal",
    "quantity": 0,
    "unit": "tCO2e",
    "status": "issued",
    "registry": {
        "registryName": "Your Registry",
        "registryId": "",
        "programName": "",
    },
    "project": {
        "projectName": "Your Project Name",
        "projectId": "",
        "projectType": "",
        "country": "XX",
        "methodology": "",
        "standard": "",
        "status": "registered",
    },
    "vintage": {
        "startDate": "2024-01-01",
        "endDate": "2024-12-31",
        "vintageYear": 2024,
    },
    "retirementInfo": None,
    "verification": {
        "hasAssurance": False,
        "levelType": "limited",
        "verifierName": "",
        "verificationDate": "",
        "standardRef": "",
    },
    "site": {
        "siteCountry": "XX",
        "region": "",
    },
    "cadTrust": None,
    "labels": [],
    "coBenefits": [],
    "article6": None,
}

SCOPE3_TEMPLATE = {
    "@context": "https://comet.carbon/v1/jsonld/context.json",
    "@type": "comet-pcf:ProductCarbonFootprint",
    "pcfId": "YOUR-UUID-HERE",
    "declaredUnit": "kilogram",
    "unitaryProductAmount": 1,
    "fossilGWP": 0.0,
    "boundaryDescription": "Scope 3 upstream supply chain emissions",
    "standardRef": ["GHGProtocol"],
    "ipccAR": "AR6",
    "referencePeriod": {
        "startDate": "2024-01-01T00:00:00Z",
        "endDate": "2024-12-31T23:59:59Z",
    },
    "organization": {
        "orgName": "Your Company Name",
    },
    "material": {
        "materialName": "Your Product / Service",
    },
    "scope3Categories": [
        {
            "categoryNumber": 1,
            "categoryName": "Purchased goods and services",
            "emissionSource": "",
            "activityDataValue": 0,
            "activityDataUnit": "",
            "emissionFactor": 0,
            "efSource": "",
            "efUnit": "kgCO2e",
            "totalEmissionsKgCO2e": 0,
            "dataQualityType": "estimated",
            "methodologyNotes": "",
        },
        {"categoryNumber": 2, "categoryName": "Capital goods", "totalEmissionsKgCO2e": 0, "dataQualityType": "estimated"},
        {"categoryNumber": 3, "categoryName": "Fuel- and energy-related activities", "totalEmissionsKgCO2e": 0, "dataQualityType": "estimated"},
        {"categoryNumber": 4, "categoryName": "Upstream transportation and distribution", "totalEmissionsKgCO2e": 0, "dataQualityType": "estimated"},
        {"categoryNumber": 5, "categoryName": "Waste generated in operations", "totalEmissionsKgCO2e": 0, "dataQualityType": "estimated"},
        {"categoryNumber": 6, "categoryName": "Business travel", "totalEmissionsKgCO2e": 0, "dataQualityType": "estimated"},
        {"categoryNumber": 7, "categoryName": "Employee commuting", "totalEmissionsKgCO2e": 0, "dataQualityType": "estimated"},
        {"categoryNumber": 8, "categoryName": "Upstream leased assets", "totalEmissionsKgCO2e": 0, "dataQualityType": "estimated"},
        {"categoryNumber": 9, "categoryName": "Downstream transportation and distribution", "totalEmissionsKgCO2e": 0, "dataQualityType": "estimated"},
        {"categoryNumber": 10, "categoryName": "Processing of sold products", "totalEmissionsKgCO2e": 0, "dataQualityType": "estimated"},
        {"categoryNumber": 11, "categoryName": "Use of sold products", "totalEmissionsKgCO2e": 0, "dataQualityType": "estimated"},
        {"categoryNumber": 12, "categoryName": "End-of-life treatment of sold products", "totalEmissionsKgCO2e": 0, "dataQualityType": "estimated"},
        {"categoryNumber": 13, "categoryName": "Downstream leased assets", "totalEmissionsKgCO2e": 0, "dataQualityType": "estimated"},
        {"categoryNumber": 14, "categoryName": "Franchises", "totalEmissionsKgCO2e": 0, "dataQualityType": "estimated"},
        {"categoryNumber": 15, "categoryName": "Investments", "totalEmissionsKgCO2e": 0, "dataQualityType": "estimated"},
    ],
}


def cmd_template(args: argparse.Namespace) -> int:
    """Generate a blank COMET template."""
    template_type = args.type

    templates = {
        "pcf": PCF_TEMPLATE,
        "eac": EAC_TEMPLATE,
        "scope3": SCOPE3_TEMPLATE,
    }

    if template_type not in templates:
        error(f"Unknown template type: {template_type}. Supported: {', '.join(TEMPLATE_TYPES)}")
        return 1

    template = templates[template_type]
    indent = 2 if args.pretty else 2  # Templates always pretty-printed
    output = json.dumps(template, indent=indent, ensure_ascii=False)

    write_output(output, args.output, pretty=args.pretty)
    return 0


# ── Main parser ─────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="comet",
        description=(
            f"{Colors.BOLD}COMET CLI{Colors.RESET} — Carbon Ontology for Measurable, "
            f"Exchangeable Transparency\n\n"
            f"Validate, convert, and export carbon data in COMET JSON-LD format."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            f"Examples:\n"
            f"  python comet_cli.py validate steel-pcf.comet.json\n"
            f"  python comet_cli.py validate --batch examples/\n"
            f"  python comet_cli.py convert data.csv --from csv --to comet --pretty\n"
            f"  python comet_cli.py export steel.comet.json --to pact --output out.json\n"
            f"  python comet_cli.py template pcf --output my-pcf.json\n"
            f"  python comet_cli.py template eac\n"
        ),
    )
    parser.add_argument(
        "--pretty", action="store_true", default=False,
        help="Pretty-print JSON output with indentation.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── validate ────────────────────────────────────────────────────
    p_validate = subparsers.add_parser(
        "validate",
        help="Validate a COMET JSON-LD file against its schema.",
        epilog=(
            "Examples:\n"
            "  python comet_cli.py validate steel-pcf.comet.json\n"
            "  python comet_cli.py validate --batch examples/ --strict\n"
            "  python comet_cli.py validate data.json --quiet\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_validate.add_argument("file", help="Path to a COMET JSON-LD file (or directory with --batch).")
    p_validate.add_argument("--strict", action="store_true", help="Strict mode: also check optional fields.")
    p_validate.add_argument("--quiet", action="store_true", help="Quiet mode: only output error count.")
    p_validate.add_argument("--json", action="store_true", dest="json_output", help="Output as structured JSON.")
    p_validate.set_defaults(func=cmd_validate)

    # ── convert ─────────────────────────────────────────────────────
    p_convert = subparsers.add_parser(
        "convert",
        help="Convert an external format into COMET JSON-LD.",
        epilog=(
            "Examples:\n"
            "  python comet_cli.py convert data.csv --from csv --to comet\n"
            "  python comet_cli.py convert footprint.json --from pact --to comet --pretty\n"
            "  python comet_cli.py convert declaration.xml --from cbam-xml --to comet\n"
            "  python comet_cli.py convert credits.json --from cad-trust --to comet --output out.json\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_convert.add_argument("input", help="Path to the input file.")
    p_convert.add_argument(
        "--from", dest="from_format", required=True,
        choices=INGEST_FORMATS,
        help=f"Source format ({', '.join(INGEST_FORMATS)}).",
    )
    p_convert.add_argument(
        "--to", dest="to_format", default="comet",
        help="Target format (default: comet).",
    )
    p_convert.add_argument("--output", "-o", help="Output file path (default: stdout).")
    p_convert.set_defaults(func=cmd_convert)

    # ── export ──────────────────────────────────────────────────────
    p_export = subparsers.add_parser(
        "export",
        help="Export COMET JSON-LD to an external format.",
        epilog=(
            "Examples:\n"
            "  python comet_cli.py export steel.comet.json --to pact\n"
            "  python comet_cli.py export steel.comet.json --to cbam-xml --output declaration.xml\n"
            "  python comet_cli.py export steel.comet.json --to csv --output report.csv\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_export.add_argument("input", help="Path to a COMET JSON-LD file.")
    p_export.add_argument(
        "--to", dest="to_format", required=True,
        choices=EXPORT_FORMATS,
        help=f"Target format ({', '.join(EXPORT_FORMATS)}).",
    )
    p_export.add_argument("--output", "-o", help="Output file path (default: stdout).")
    p_export.set_defaults(func=cmd_export)

    # ── template ────────────────────────────────────────────────────
    p_template = subparsers.add_parser(
        "template",
        help="Generate a blank COMET JSON-LD template.",
        epilog=(
            "Examples:\n"
            "  python comet_cli.py template pcf\n"
            "  python comet_cli.py template eac --output my-eac.json\n"
            "  python comet_cli.py template scope3 --pretty\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_template.add_argument(
        "type",
        choices=TEMPLATE_TYPES,
        help=f"Template type ({', '.join(TEMPLATE_TYPES)}).",
    )
    p_template.add_argument("--output", "-o", help="Output file path (default: stdout).")
    p_template.set_defaults(func=cmd_template)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
