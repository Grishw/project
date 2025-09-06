import os
import pandas as pd
from typing import Dict, Any


def save_uploaded_csv(file_storage, base_dir: str, project_id: str) -> tuple[str, bool]:
    project_dir = os.path.join(base_dir, project_id)
    os.makedirs(project_dir, exist_ok=True)
    filepath = os.path.join(project_dir, file_storage.filename)
    
    # Проверяем, существует ли файл с таким же именем
    file_exists = os.path.exists(filepath)
    
    file_storage.save(filepath)
    return filepath, file_exists


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


def restore_preview_from_metadata(project_id: str, data_path: str) -> Dict[str, Any]:
    """Восстанавливает preview данных из файла"""
    return dataframe_preview(data_path)


def restore_selection_from_metadata(project_id: str, data_path: str, target: str, features: list[str]) -> Dict[str, Any]:
    """Восстанавливает выборку данных из файла"""
    cols = []
    if target:
        cols.append(target)
    cols.extend([c for c in features if c and c != target])
    return sample_columns(data_path, cols)


def restore_preprocess_from_metadata(project_id: str, data_path: str, target: str, method: str) -> Dict[str, Any]:
    """Восстанавливает результаты предобработки из файла"""
    from modules.data.preprocess import preprocess_pipeline
    import pandas as pd
    
    df_info = sample_columns(data_path, [target])
    df = pd.DataFrame(df_info["records"])
    out = preprocess_pipeline(df, target=target, method=method)
    seg = out["segment"].to_dict(orient="records")
    
    return {
        "segment": {"columns": list(out["segment"].columns), "records": seg}, 
        "bounds": out["bounds"], 
        "curve": out["curve"]
    }


def restore_train_from_metadata(project_id: str, data_path: str, target: str, model_config: Dict[str, Any]) -> Dict[str, Any]:
    """Восстанавливает результаты обучения из файла"""
    from modules.models.tf_models import ModelConfig, train_and_predict
    import pandas as pd
    import os
    
    # Загружаем данные
    df = pd.read_csv(data_path, usecols=[target])
    series = df[target].astype(float).to_numpy()
    
    # Создаем конфигурацию модели
    cfg = ModelConfig(
        model_type=model_config.get("model", "mlp"),
        window=model_config.get("window", 32),
        horizon=model_config.get("horizon", 12),
        epochs=model_config.get("epochs", 5)
    )
    
    # Получаем путь к артефактам
    artifacts_dir = os.path.join(os.path.dirname(data_path), "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    
    # Обучаем модель
    out = train_and_predict(series, cfg, save_dir=artifacts_dir)
    
    return {
        "loss": out['loss'], 
        "prediction": out['prediction'], 
        "cfg": model_config
    }


def restore_full_snapshot_from_metadata(project_id: str, metadata: Dict[str, Any], data_path: str) -> Dict[str, Any]:
    """Восстанавливает полный снапшот из метаданных"""
    snapshot = {}
    
    # Восстанавливаем preview
    if metadata.get("has_preview"):
        snapshot["preview"] = restore_preview_from_metadata(project_id, data_path)
    
    # Восстанавливаем selection
    if metadata.get("selection"):
        selection_meta = metadata["selection"]
        snapshot["selection"] = selection_meta
        snapshot["sample"] = restore_selection_from_metadata(
            project_id, data_path, 
            selection_meta.get("target"), 
            selection_meta.get("features", [])
        )
    
    # Восстанавливаем preprocess
    if metadata.get("preprocess"):
        preprocess_meta = metadata["preprocess"]
        snapshot["preprocess"] = restore_preprocess_from_metadata(
            project_id, data_path,
            preprocess_meta.get("target"),
            preprocess_meta.get("method", "cusum")
        )
    
    # Восстанавливаем train
    if metadata.get("train"):
        train_meta = metadata["train"]
        snapshot["train"] = restore_train_from_metadata(
            project_id, data_path,
            train_meta.get("target"),
            train_meta.get("cfg", {})
        )
    
    return snapshot

