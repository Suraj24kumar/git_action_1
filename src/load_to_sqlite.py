"""Load all processed clean CSV outputs into a SQLite analytics table."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd

from data_quality import project_root


def main() -> int:
    """Load processed clean orders into data/warehouse/orders.db."""
    root = project_root()
    processed_dir = root / "data" / "processed"
    warehouse_dir = root / "data" / "warehouse"
    warehouse_dir.mkdir(parents=True, exist_ok=True)

    clean_files = sorted(processed_dir.glob("*_clean.csv"))
    if not clean_files:
        print("No clean CSV files found. Run transform_data.py first.")
        return 1

    frames = []
    for file_path in clean_files:
        df = pd.read_csv(file_path)
        df["source_file"] = file_path.name
        frames.append(df)

    combined_df = pd.concat(frames, ignore_index=True)
    db_path = warehouse_dir / "orders.db"

    with sqlite3.connect(db_path) as connection:
        combined_df.to_sql("clean_orders", connection, if_exists="replace", index=False)
        row_count = connection.execute("SELECT COUNT(*) FROM clean_orders").fetchone()[0]

    print(f"Loaded {row_count} clean rows into SQLite table clean_orders at {db_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
