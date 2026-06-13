"""Shared data-quality utilities for the order pipeline."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import pandas as pd

REQUIRED_COLUMNS = ["order_id", "customer_id", "order_date", "amount", "status"]
ALLOWED_STATUS = {"completed", "pending", "cancelled"}


@dataclass
class FileQualitySummary:
    """Summary statistics for one processed CSV file."""

    file_name: str
    total_rows: int
    clean_rows: int
    rejected_rows: int
    rejection_reason_counts: dict[str, int]

    def to_dict(self) -> dict:
        """Convert the summary dataclass to a serializable dictionary."""
        return asdict(self)


def project_root() -> Path:
    """Return the repository root based on this file location."""
    return Path(__file__).resolve().parents[1]


def discover_csv_files(raw_dir: Path) -> list[Path]:
    """Find all CSV files in the raw data directory."""
    return sorted(raw_dir.glob("*.csv"))


def read_orders_csv(file_path: Path) -> pd.DataFrame:
    """Read an orders CSV as strings so validation is consistent across environments."""
    return pd.read_csv(file_path, dtype=str, keep_default_na=False)


def validate_required_columns(df: pd.DataFrame, file_name: str) -> None:
    """Raise a ValueError when a file does not contain the required order columns."""
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"{file_name}: missing required columns: {missing}")


def _blank_mask(series: pd.Series) -> pd.Series:
    """Return True for empty or whitespace-only values."""
    return series.astype(str).str.strip().eq("")


def add_quality_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add parsed fields, rejection reasons, and row validity status to an orders DataFrame."""
    working_df = df.copy()

    # Normalize text fields before validation.
    for column in REQUIRED_COLUMNS:
        working_df[column] = working_df[column].astype(str).str.strip()

    # Parse date and amount values using coercion so invalid values become NaT/NaN.
    working_df["parsed_order_date"] = pd.to_datetime(
        working_df["order_date"], errors="coerce", format="%Y-%m-%d"
    )
    working_df["amount_numeric"] = pd.to_numeric(working_df["amount"], errors="coerce")

    # Mark duplicate order IDs inside each individual file, excluding blank IDs.
    non_blank_order_id = ~_blank_mask(working_df["order_id"])
    duplicate_order_id = working_df.loc[non_blank_order_id, "order_id"].duplicated(keep=False)
    working_df["is_duplicate_order_id"] = False
    working_df.loc[non_blank_order_id, "is_duplicate_order_id"] = duplicate_order_id.reindex(
        working_df.loc[non_blank_order_id].index, fill_value=False
    )

    # Build readable rejection reasons for every row.
    rejection_reasons: list[str] = []
    for _, row in working_df.iterrows():
        reasons: list[str] = []
        if str(row["order_id"]).strip() == "":
            reasons.append("missing_order_id")
        if str(row["customer_id"]).strip() == "":
            reasons.append("missing_customer_id")
        if pd.isna(row["parsed_order_date"]):
            reasons.append("invalid_order_date")
        if pd.isna(row["amount_numeric"]):
            reasons.append("invalid_amount")
        elif row["amount_numeric"] <= 0:
            reasons.append("non_positive_amount")
        if str(row["status"]).strip().lower() not in ALLOWED_STATUS:
            reasons.append("invalid_status")
        if bool(row["is_duplicate_order_id"]):
            reasons.append("duplicate_order_id")
        rejection_reasons.append(";".join(reasons))

    working_df["rejection_reasons"] = rejection_reasons
    working_df["is_valid"] = working_df["rejection_reasons"].eq("")
    return working_df


def split_clean_and_rejected(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a quality-checked DataFrame into clean and rejected records."""
    clean_columns = ["order_id", "customer_id", "order_date", "amount", "status", "amount_numeric"]
    rejected_columns = REQUIRED_COLUMNS + ["rejection_reasons"]

    clean_df = df.loc[df["is_valid"], clean_columns].copy()
    clean_df = clean_df.rename(columns={"amount_numeric": "amount_clean"})

    rejected_df = df.loc[~df["is_valid"], rejected_columns].copy()
    return clean_df, rejected_df


def summarize_file(file_path: Path) -> FileQualitySummary:
    """Create a quality summary for one CSV file."""
    df = read_orders_csv(file_path)
    validate_required_columns(df, file_path.name)
    quality_df = add_quality_columns(df)
    clean_df, rejected_df = split_clean_and_rejected(quality_df)

    reason_counts: dict[str, int] = {}
    for reasons in rejected_df["rejection_reasons"].dropna():
        for reason in str(reasons).split(";"):
            if reason:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

    return FileQualitySummary(
        file_name=file_path.name,
        total_rows=len(df),
        clean_rows=len(clean_df),
        rejected_rows=len(rejected_df),
        rejection_reason_counts=reason_counts,
    )


def process_file(file_path: Path, processed_dir: Path, rejected_dir: Path) -> FileQualitySummary:
    """Validate, split, and write clean/rejected output files for one raw CSV."""
    df = read_orders_csv(file_path)
    validate_required_columns(df, file_path.name)
    quality_df = add_quality_columns(df)
    clean_df, rejected_df = split_clean_and_rejected(quality_df)

    processed_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir.mkdir(parents=True, exist_ok=True)

    file_stem = file_path.stem
    clean_output_path = processed_dir / f"{file_stem}_clean.csv"
    rejected_output_path = rejected_dir / f"{file_stem}_rejected.csv"

    clean_df.to_csv(clean_output_path, index=False)
    rejected_df.to_csv(rejected_output_path, index=False)

    reason_counts: dict[str, int] = {}
    for reasons in rejected_df["rejection_reasons"].dropna():
        for reason in str(reasons).split(";"):
            if reason:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

    return FileQualitySummary(
        file_name=file_path.name,
        total_rows=len(df),
        clean_rows=len(clean_df),
        rejected_rows=len(rejected_df),
        rejection_reason_counts=reason_counts,
    )
