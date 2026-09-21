"""
check_missing.py
================
Compare a directory of Palmarès PDF files against a directory of extracted
JSON files and report which PDFs have not yet been fully processed.

Each processed PDF is expected to produce TWO JSON files:
    <stem>_students_data.json
    <stem>_schools_data.json

Usage:
    python check_missing.py <pdf_dir> <json_dir> [--export missing.txt]

Examples:
    python check_missing.py ./pdfs ./json_output
    python check_missing.py ./pdfs ./json_output --export missing.txt
"""

import argparse
import sys
from pathlib import Path


def check_missing(pdf_dir: Path, json_dir: Path) -> dict:
    """
    Scan pdf_dir and json_dir, return a report dict with three categories:

      fully_processed   — both _students_data.json and _schools_data.json exist
      partially_missing — only one of the two JSON files exists
      not_processed     — neither JSON file exists

    Returns:
        {
          "fully_processed":   [{"pdf": ..., "students_json": ..., "schools_json": ...}],
          "partially_missing": [{"pdf": ..., "missing": [...], "present": [...]}],
          "not_processed":     [Path, ...],
        }
    """
    pdf_files = sorted(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"[WARN] No PDF files found in '{pdf_dir}'")

    fully_processed   = []
    partially_missing = []
    not_processed     = []

    for pdf_path in pdf_files:
        stem = pdf_path.stem

        students_json = json_dir / f"{stem}_students_data.json"
        schools_json  = json_dir / f"{stem}_schools_data.json"

        has_students = students_json.exists()
        has_schools  = schools_json.exists()

        if has_students and has_schools:
            fully_processed.append({
                "pdf":          pdf_path,
                "students_json": students_json,
                "schools_json":  schools_json,
            })

        elif has_students or has_schools:
            present = []
            missing = []
            (present if has_students else missing).append(students_json)
            (present if has_schools  else missing).append(schools_json)

            partially_missing.append({
                "pdf":     pdf_path,
                "present": present,
                "missing": missing,
            })

        else:
            not_processed.append(pdf_path)

    return {
        "fully_processed":   fully_processed,
        "partially_missing": partially_missing,
        "not_processed":     not_processed,
    }


def print_report(report: dict, pdf_dir: Path, json_dir: Path) -> None:
    total = (
        len(report["fully_processed"])
        + len(report["partially_missing"])
        + len(report["not_processed"])
    )

    print()
    print("=" * 60)
    print("  PALMARÈS PROCESSING STATUS REPORT")
    print("=" * 60)
    print(f"  PDF  directory : {pdf_dir.resolve()}")
    print(f"  JSON directory : {json_dir.resolve()}")
    print(f"  Total PDFs     : {total}")
    print(f"  ✅ Fully processed   : {len(report['fully_processed'])}")
    print(f"  ⚠️  Partially missing : {len(report['partially_missing'])}")
    print(f"  ❌ Not processed     : {len(report['not_processed'])}")
    print("=" * 60)

    # ── Not processed ────────────────────────────────────────────
    if report["not_processed"]:
        print(f"\n❌  NOT PROCESSED ({len(report['not_processed'])} files)")
        print("    Neither _students_data.json nor _schools_data.json found.\n")
        for pdf in report["not_processed"]:
            print(f"    • {pdf.name}")

    # ── Partially missing ─────────────────────────────────────────
    if report["partially_missing"]:
        print(f"\n⚠️   PARTIALLY MISSING ({len(report['partially_missing'])} files)")
        print("    One of the two JSON files is absent.\n")
        for entry in report["partially_missing"]:
            print(f"    • {entry['pdf'].name}")
            for p in entry["present"]:
                print(f"        ✅ {p.name}")
            for m in entry["missing"]:
                print(f"        ❌ {m.name}  ← missing")

    # ── Fully processed (summary only) ────────────────────────────
    if report["fully_processed"]:
        print(f"\n✅  FULLY PROCESSED ({len(report['fully_processed'])} files)")
        for entry in report["fully_processed"]:
            print(f"    • {entry['pdf'].name}")

    print()


def export_missing(report: dict, export_path: Path) -> None:
    """Write unprocessed and partially-missing PDF paths to a plain text file."""
    lines = []

    if report["not_processed"]:
        lines.append("# NOT PROCESSED (no JSON files found)")
        for pdf in report["not_processed"]:
            lines.append(str(pdf.resolve()))

    if report["partially_missing"]:
        lines.append("")
        lines.append("# PARTIALLY MISSING (one JSON file missing)")
        for entry in report["partially_missing"]:
            lines.append(str(entry["pdf"].resolve()))
            for m in entry["missing"]:
                lines.append(f"    MISSING: {m.name}")

    export_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n📄 Missing PDF list written to: {export_path.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find Palmarès PDFs that are missing their JSON extracts."
    )
    parser.add_argument("pdf_dir",  type=Path, help="Directory containing PDF files")
    parser.add_argument("json_dir", type=Path, help="Directory containing JSON files")
    parser.add_argument(
        "--export", type=Path, default=None, metavar="FILE",
        help="Optional: write unprocessed PDF paths to this file",
    )
    args = parser.parse_args()

    # Validate directories
    if not args.pdf_dir.is_dir():
        print(f"[ERROR] PDF directory not found: '{args.pdf_dir}'")
        sys.exit(1)
    if not args.json_dir.is_dir():
        print(f"[ERROR] JSON directory not found: '{args.json_dir}'")
        sys.exit(1)

    report = check_missing(args.pdf_dir, args.json_dir)
    print_report(report, args.pdf_dir, args.json_dir)

    if args.export:
        export_missing(report, args.export)

    # Exit with non-zero code if anything is missing (useful in CI / shell scripts)
    if report["not_processed"] or report["partially_missing"]:
        sys.exit(2)


if __name__ == "__main__":
    main()