import os
import pandas as pd
from typing import Dict, Any


def save_uploaded_csv(file_storage, base_dir: str, project_id: str) -> str:
    project_dir = os.path.join(base_dir, project_id)
    os.makedirs(project_dir, exist_ok=True)
    filepath = os.path.join(project_dir, file_storage.filename)
    file_storage.save(filepath)
    return filepath


def dataframe_preview(csv_path: str, max_rows: int = 5) -> Dict[str, Any]:
    df = pd.read_csv(csv_path)
    head = df.head(max_rows)
    info = {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "column_names": list(df.columns.astype(str)),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "na_counts": {col: int(df[col].isna().sum()) for col in df.columns},
    }
    return {
        "head": head.to_dict(orient="records"),
        "info": info,
    }


def sample_columns(csv_path: str, columns: list[str], limit: int = 1000) -> Dict[str, Any]:
    usecols = columns if columns else None
    df = pd.read_csv(csv_path, usecols=usecols)
    sample = df.head(limit)
    return {
        "records": sample.to_dict(orient="records"),
        "columns": list(sample.columns.astype(str)),
        "size": int(sample.shape[0]),
    }

