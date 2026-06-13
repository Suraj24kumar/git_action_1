"""Unit tests for the data quality pipeline."""

from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_quality import add_quality_columns, process_file, validate_required_columns


def test_add_quality_columns_identifies_bad_rows() -> None:
    """The quality checker should identify missing IDs, bad dates, bad amounts, and invalid status values."""
    df = pd.DataFrame(
        [
            {"order_id": "1", "customer_id": "101", "order_date": "2025-01-01", "amount": "500", "status": "completed"},
            {"order_id": "", "customer_id": "102", "order_date": "wrong-date", "amount": "-50", "status": "unknown"},
        ]
    )

    quality_df = add_quality_columns(df)

    assert quality_df.loc[0, "is_valid"] is True or bool(quality_df.loc[0, "is_valid"])
    assert not bool(quality_df.loc[1, "is_valid"])
    assert "missing_order_id" in quality_df.loc[1, "rejection_reasons"]
    assert "invalid_order_date" in quality_df.loc[1, "rejection_reasons"]
    assert "non_positive_amount" in quality_df.loc[1, "rejection_reasons"]
    assert "invalid_status" in quality_df.loc[1, "rejection_reasons"]


def test_validate_required_columns_raises_for_missing_column() -> None:
    """Schema validation should fail when a required column is absent."""
    df = pd.DataFrame(
        [{"order_id": "1", "customer_id": "101", "order_date": "2025-01-01", "amount": "500"}]
    )

    with pytest.raises(ValueError, match="missing required columns"):
        validate_required_columns(df, "missing_status.csv")


def test_process_file_writes_clean_and_rejected_outputs(tmp_path: Path) -> None:
    """Processing a file should create separate clean and rejected CSV outputs."""
    raw_file = tmp_path / "orders_test.csv"
    processed_dir = tmp_path / "processed"
    rejected_dir = tmp_path / "rejected"

    raw_file.write_text(
        "order_id,customer_id,order_date,amount,status\n"
        "1,101,2025-01-01,500,completed\n"
        ",102,wrong-date,-50,unknown\n",
        encoding="utf-8",
    )

    summary = process_file(raw_file, processed_dir, rejected_dir)

    clean_output = processed_dir / "orders_test_clean.csv"
    rejected_output = rejected_dir / "orders_test_rejected.csv"

    assert summary.total_rows == 2
    assert summary.clean_rows == 1
    assert summary.rejected_rows == 1
    assert clean_output.exists()
    assert rejected_output.exists()
