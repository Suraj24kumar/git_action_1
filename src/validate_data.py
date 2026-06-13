"""Validate all CSV files in data/raw and write a data-quality report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from data_quality import discover_csv_files, project_root, summarize_file


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the validation script."""
    parser = argparse.ArgumentParser(description="Validate raw order CSV files.")
    parser.add_argument(
        "--fail-on-rejections",
        action="store_true",
        help="Fail the script if row-level data quality issues are found.",
    )
    return parser.parse_args()


def main() -> int:
    """Run schema and row-quality validation for all raw CSV files."""
    args = parse_args()
    root = project_root()
    raw_dir = root / "data" / "raw"
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    csv_files = discover_csv_files(raw_dir)
    if not csv_files:
        print("No CSV files found in data/raw/.")
        return 1

    summaries = []
    schema_errors = []

    for file_path in csv_files:
        try:
            summary = summarize_file(file_path)
            summaries.append(summary.to_dict())
            print(
                f"{summary.file_name}: total={summary.total_rows}, "
                f"clean={summary.clean_rows}, rejected={summary.rejected_rows}"
            )
        except Exception as exc:
            schema_errors.append(str(exc))
            print(f"Validation error: {exc}")

    report = {
        "raw_directory": str(raw_dir),
        "files_checked": len(csv_files),
        "schema_errors": schema_errors,
        "files": summaries,
    }

    report_path = reports_dir / "data_quality_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Data quality report written to {report_path}")

    if schema_errors:
        return 1

    total_rejected = sum(item["rejected_rows"] for item in summaries)
    if args.fail_on_rejections and total_rejected > 0:
        print(f"Failing because {total_rejected} rejected rows were found.")
        return 1

    print("Validation completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
