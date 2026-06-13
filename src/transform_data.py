"""Transform all raw order CSV files into clean and rejected outputs."""

from __future__ import annotations

import json
import sys

from data_quality import discover_csv_files, process_file, project_root


def main() -> int:
    """Process every CSV file in data/raw into data/processed and data/rejected."""
    root = project_root()
    raw_dir = root / "data" / "raw"
    processed_dir = root / "data" / "processed"
    rejected_dir = root / "data" / "rejected"
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    csv_files = discover_csv_files(raw_dir)
    if not csv_files:
        print("No CSV files found in data/raw/.")
        return 1

    summaries = []
    for file_path in csv_files:
        summary = process_file(file_path, processed_dir, rejected_dir)
        summaries.append(summary.to_dict())
        print(
            f"Processed {summary.file_name}: "
            f"clean={summary.clean_rows}, rejected={summary.rejected_rows}"
        )

    transform_report_path = reports_dir / "transform_report.json"
    transform_report_path.write_text(json.dumps({"files": summaries}, indent=2), encoding="utf-8")
    print(f"Transform report written to {transform_report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
