# Automated Data Quality Pipeline with GitHub Actions

This project is a small Data Engineering CI pipeline. It processes every CSV file inside `data/raw/`, validates the records, splits clean and rejected rows, loads clean output into SQLite, and runs automatically through GitHub Actions.

## Use case

A company receives order CSV files from different sources. Before the data is used for analytics, it must be checked for common quality issues:

- Missing `order_id`
- Missing `customer_id`
- Invalid `order_date`
- Non-positive or invalid `amount`
- Invalid `status`
- Duplicate `order_id` inside the same file
- Missing required columns

## Folder structure

```text
data-quality-ci-pipeline/
├── data/
│   ├── raw/                 # Put input CSV files here
│   ├── processed/           # Generated clean CSV files
│   ├── rejected/            # Generated rejected CSV files
│   ├── test_samples/        # Extra CSV files for manual testing
│   └── warehouse/           # Generated SQLite database
├── src/
│   ├── data_quality.py      # Shared validation and transformation logic
│   ├── validate_data.py     # Scans data/raw/*.csv and creates quality report
│   ├── transform_data.py    # Creates clean/rejected outputs per raw CSV
│   └── load_to_sqlite.py    # Loads clean CSVs into SQLite
├── tests/
│   └── test_data_quality.py
├── notebooks/
│   └── data_quality_colab.ipynb
└── .github/workflows/
    └── data_quality_ci.yml
```

## How GitHub Actions works here

GitHub Actions does not run Google Colab. It runs the `.py` scripts inside this GitHub repository on a temporary Ubuntu machine.

When you push a file into `data/raw/`, GitHub Actions starts automatically and runs:

```bash
python src/validate_data.py
python src/transform_data.py
python src/load_to_sqlite.py
pytest tests/
```

## Does it process one CSV or all CSVs?

It processes **all CSV files** inside `data/raw/`.

Example:

```text
data/raw/orders.csv
data/raw/orders_january.csv
data/raw/orders2.csv
```

The pipeline scans `data/raw/*.csv`, so all three files are processed.

Generated outputs:

```text
data/processed/orders_clean.csv
data/processed/orders_january_clean.csv
data/processed/orders2_clean.csv

data/rejected/orders_rejected.csv
data/rejected/orders_january_rejected.csv
data/rejected/orders2_rejected.csv
```

## How to test with a new CSV

1. Copy any file from `data/test_samples/` into `data/raw/`.
2. Rename it, for example:

```text
data/raw/orders2.csv
```

3. Commit and push:

```bash
git add .
git commit -m "Add new raw orders file"
git push origin main
```

4. Open GitHub → your repo → Actions.
5. You will see the workflow run automatically.

## Local execution

```bash
pip install -r requirements.txt
python src/validate_data.py
python src/transform_data.py
python src/load_to_sqlite.py
pytest tests/
```

## Strict validation mode

By default, the pipeline passes when row-level bad data exists because bad rows are moved to `data/rejected/`. It fails only for critical issues like missing required columns.

To fail the workflow even when rejected rows are found, change the GitHub Actions command to:

```bash
python src/validate_data.py --fail-on-rejections
```

## Expected interview explanation

I built a folder-driven data quality CI pipeline. Any CSV placed inside `data/raw/` is automatically picked by the Python pipeline. GitHub Actions runs the validation, transformation, SQLite load, and unit tests on every push or pull request. Clean rows go to `data/processed/`, bad rows go to `data/rejected/`, and schema-level issues fail the CI workflow.
