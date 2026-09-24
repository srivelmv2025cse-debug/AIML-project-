from pathlib import Path
import json
import re

import pandas as pd

SUPPORTED_EXTENSIONS = {"csv", "xlsx", "json"}
COMMON_COLUMNS = (
    "date",
    "product",
    "product_id",
    "category",
    "quantity",
    "price",
    "sales",
    "customer_id",
    "region",
    "discount",
    "inventory",
)
NUMERIC_FIELDS = {"quantity", "price", "sales", "discount", "inventory"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def file_extension(filename):
    return Path(filename).suffix.lower().lstrip(".")


def validate_upload(filename, content_length):
    if not filename or not filename.strip():
        raise ValueError("Please select a file to upload.")
    if Path(filename).name != filename or "\x00" in filename:
        raise ValueError("The file name is not valid.")
    extension = file_extension(filename)
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported file type. Upload a CSV, XLSX, or JSON file.")
    if content_length and content_length > MAX_UPLOAD_BYTES:
        raise ValueError("The file is too large. The maximum upload size is 10 MB.")
    return extension


def read_dataset(path, extension):
    if extension == "csv":
        return pd.read_csv(path)
    if extension == "xlsx":
        return pd.read_excel(path, engine="openpyxl")
    with path.open("r", encoding="utf-8") as source:
        payload = json.load(source)
    if isinstance(payload, dict):
        payload = payload.get("data", payload)
    return pd.json_normalize(payload)


def normalize_name(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def detect_columns(columns):
    normalized = {column: normalize_name(column) for column in columns}
    detected = {}
    for common_name in COMMON_COLUMNS:
        exact = next((column for column, name in normalized.items() if name == common_name), None)
        if exact:
            detected[common_name] = exact
            continue
        match = next((column for column, name in normalized.items() if common_name in name), None)
        if match:
            detected[common_name] = match
    return detected


def dataframe_summary(dataframe):
    return {
        "rows": len(dataframe.index),
        "columns": len(dataframe.columns),
        "column_names": list(dataframe.columns),
        "data_types": {str(column): str(dataframe[column].dtype) for column in dataframe.columns},
        "missing_values": {str(column): int(dataframe[column].isna().sum()) for column in dataframe.columns},
        "duplicate_rows": int(dataframe.duplicated().sum()),
    }


def clean_dataset(dataframe, mapping):
    cleaned = dataframe.copy()
    cleaned.columns = [str(column).strip() for column in cleaned.columns]
    cleaned = cleaned.drop_duplicates().reset_index(drop=True)

    for field, source_column in mapping.items():
        if not source_column or source_column not in cleaned.columns:
            continue
        if field == "date":
            cleaned[source_column] = pd.to_datetime(cleaned[source_column], errors="coerce")
        elif field in NUMERIC_FIELDS:
            cleaned[source_column] = pd.to_numeric(cleaned[source_column], errors="coerce")

    for column in cleaned.columns:
        if pd.api.types.is_numeric_dtype(cleaned[column]):
            median = cleaned[column].median()
            cleaned[column] = cleaned[column].fillna(0 if pd.isna(median) else median)
        elif pd.api.types.is_datetime64_any_dtype(cleaned[column]):
            continue
        else:
            cleaned[column] = cleaned[column].fillna("Unknown")

    return cleaned


def save_dataset(dataframe, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output_path, index=False, date_format="%Y-%m-%d")
