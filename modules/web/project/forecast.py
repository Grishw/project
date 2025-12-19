from .blueprint import project_bp
from flask import request, jsonify
from modules.storage.projects import get_project, update_project, save_snapshot, load_snapshot, save_snapshot_metadata, load_snapshot_metadata, get_data_file_path, delete_project
from modules.data.ingest import save_uploaded_csv, dataframe_preview, sample_columns, restore_full_snapshot_from_metadata
from modules.data.preprocess import preprocess_pipeline
from modules.models.tf_models import ModelConfig, train_and_predict, train_model, iterative_forecast
import os

BASE_DATA_DIR = os.path.abspath(os.path.join(os.getcwd(), "data", "projects"))

@project_bp.route("/<project_id>/forecast", methods=["POST"])
def forecast(project_id: str):
    project = get_project(project_id)
    if not project or not project.get("data_path"):
        return jsonify({"error": "Данные не загружены"}), 400
    payload = request.get_json(silent=True) or {}
    target = payload.get("target") or project.get("target")
    steps = int(payload.get("steps", 12))
    context = payload.get("context")
    try:
        context = int(context) if context is not None else None
    except Exception:
        context = None
    if not target:
        return jsonify({"error": "Не указан target"}), 400

    # Читаем конфигурацию из снапшота (из последнего обучения)
    snap = load_snapshot(project_id) or {}
    train_info = snap.get("train") or {}
    cfg_info = (train_info.get("cfg") or {})
    window = int(cfg_info.get("window", 32))
    horizon = int(cfg_info.get("horizon", 12))

    # Загружаем ряд и метаданные времени
    import pandas as pd
    metadata = load_snapshot_metadata(project_id) or {}
    time_meta = (metadata.get("time") or {}) if isinstance(metadata, dict) else {}

    time_col = time_meta.get("column")
    usecols = [target] + ([time_col] if time_col else [])
    df = pd.read_csv(project["data_path"], usecols=usecols)
    series = df[target].astype(float).to_numpy()

    model_path = os.path.join(BASE_DATA_DIR, project_id, "artifacts", "model.keras")
    if not os.path.exists(model_path):
        return jsonify({"error": "Сначала обучите модель"}), 400

    # Прогнозируем
    print("Start predict")
    pred = iterative_forecast(series, model_path, window=window, steps=steps, horizon=horizon, context=context)

    # Подготовим временную ось продолжения
    time_future = None
    try:
        if time_col:
            kind = time_meta.get("kind")
            fmt = time_meta.get("format")
            if kind in ("timestamp_sec", "timestamp_ms"):
                unit = "s" if kind == "timestamp_sec" else "ms"
                t = pd.to_datetime(df[time_col], unit=unit, errors="coerce")
            elif kind == "datetime_format" and fmt:
                t = pd.to_datetime(df[time_col], format=fmt, errors="coerce")
            elif kind in ("iso_date", "rfc_2822", "human_readable"):
                t = pd.to_datetime(df[time_col], errors="coerce")
            else:
                t = None
            
            if t is not None:
                x_base = t.dt.tz_localize(None) if hasattr(t, 'dt') else t
                diffs = x_base.diff().dropna()
                step = diffs.median() if not diffs.empty else pd.Timedelta(seconds=1)
                last = x_base.iloc[-1]
                time_future = [ (last + step * (i+1)).isoformat() for i in range(horizon*steps) ]
    except Exception:
        time_future = None

    context_val = series[-context:]
    time_current = df[time_col].iloc[-context:].to_numpy()

    snap = load_snapshot(project_id) or {}
    snap["predict"] = {"segment": {"prediction_val": pred.tolist(), "prediction_time": time_future, "context_val": context_val.tolist(), "context_time": time_current.tolist()}}
    save_snapshot(project_id, snap)

    return jsonify({"ok": True, "prediction_val": pred.tolist(), "prediction_time": time_future, "context_val": context_val.tolist(), "context_time": time_current.tolist()})

