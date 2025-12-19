from .blueprint import project_bp
from flask import request, jsonify
from modules.storage.projects import get_project, update_project, save_snapshot, load_snapshot, save_snapshot_metadata, load_snapshot_metadata, get_data_file_path, delete_project
from modules.data.ingest import save_uploaded_csv, dataframe_preview, sample_columns, restore_full_snapshot_from_metadata
from modules.models.tf_models import ModelConfig, train_and_predict, train_model, iterative_forecast
import math

@project_bp.route("/<project_id>/train", methods=["POST"])
def train(project_id: str):
    project = get_project(project_id)
    if not project or not project.get("data_path"):
        return jsonify({"error": "Данные не загружены"}), 400
    payload = request.get_json(silent=True) or {}
    target = payload.get("target") or project.get("target")
    model_type = payload.get("model", "mlp")
    window = int(payload.get("window", 32))
    horizon = int(payload.get("horizon", 12))
    epochs = int(payload.get("epochs", 5))
    batch_size = int(payload.get("batch_size", 32))
    learning_rate = float(payload.get("learning_rate", 1e-3))
    val_split = float(payload.get("val_split", 0.2))
    if not target:
        return jsonify({"error": "Не указан target"}), 400
    # Загружаем target и, при наличии, временную колонку
    import pandas as pd
    metadata = load_snapshot_metadata(project_id) or {}
    time_meta = (metadata.get("time") or {}) if isinstance(metadata, dict) else {}
    time_col = time_meta.get("column")
    usecols = [target] + ([time_col] if time_col else [])
    df = pd.read_csv(project["data_path"], usecols=usecols)
    series = df[target].astype(float).to_numpy()
    cfg = ModelConfig(model_type=model_type, window=window, horizon=horizon, epochs=epochs, batch_size=batch_size, learning_rate=learning_rate, val_split=val_split)
    # Только обучение на этом этапе
    train_out = train_model(series, cfg, save_dir=os.path.join(BASE_DATA_DIR, project_id, "artifacts"))
    update_project(project_id, model=model_type, horizon=horizon, status="trained")
    
    # Обновляем метаданные
    metadata = load_snapshot_metadata(project_id) or {}
    metadata["train"] = {
        "target": target,
        "cfg": {"model": model_type, "window": window, "horizon": horizon, "epochs": epochs}
    }
    save_snapshot_metadata(project_id, metadata)
    
    # Сохраняем только результаты обучения для быстрого доступа
    # Санитизация значений (NaN/inf -> None)
    def finite_or_none(v):
        try:
            f = float(v)
            return f if math.isfinite(f) else None
        except Exception:
            return None

    tr_loss = finite_or_none(train_out.get('loss'))
    tr_vloss = finite_or_none(train_out.get('val_loss'))
    tr_vmae = finite_or_none(train_out.get('val_mae'))

    # Санитизация кривых обучения (NaN/inf -> None)
    def sanitize_array(arr):
        if not isinstance(arr, list):
            return None
        return [finite_or_none(v) for v in arr]

    # Подготовим временные оси для отрисовки прогноза
    x_axes = {"base": None, "future": None}
    try:
        if time_col:
            kind = time_meta.get("kind", "index")
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
                # сделать наивным без указания неподдерживаемых аргументов
                if hasattr(t, 'dt'):
                    x_base = t.dt.tz_localize(None)
                else:
                    try:
                        x_base = t.tz_localize(None)
                    except Exception:
                        x_base = t
                diffs = x_base.diff().dropna()
                step = diffs.median() if not diffs.empty else pd.Timedelta(seconds=1)
                last = x_base.iloc[-1]
                future = [ (last + step * (i+1)).isoformat() for i in range(horizon) ]
                x_axes["base"] = [d.isoformat() if hasattr(d, 'isoformat') else str(d) for d in x_base]
                x_axes["future"] = future
            else:
                x_axes["base"] = list(range(len(series)))
                x_axes["future"] = list(range(len(series), len(series)+horizon))
        else:
            x_axes["base"] = list(range(len(series)))
            x_axes["future"] = list(range(len(series), len(series)+horizon))
    except Exception:
        x_axes["base"] = list(range(len(series)))
        x_axes["future"] = list(range(len(series), len(series)+horizon))
    
    loss_curve = sanitize_array(train_out.get('loss_curve')) or []
    val_loss_curve = sanitize_array(train_out.get('val_loss_curve')) or []
    mae_curve = sanitize_array(train_out.get('mae_curve')) or []
    val_mae_curve = sanitize_array(train_out.get('val_mae_curve')) or []

    snap = load_snapshot(project_id) or {}
    snap["train"] = {"loss": tr_loss, "val_loss": tr_vloss, "val_mae": tr_vmae, "model_file": train_out.get('model_file'), 
                     "loss_curve": loss_curve, "val_loss_curve": val_loss_curve, "mae_curve": mae_curve, "val_mae_curve": val_mae_curve, 
                     "x": x_axes, "cfg": {
                            "model": model_type, "window": window, 
                            "horizon": horizon, "epochs": epochs, 
                            "batch_size": batch_size, "learning_rate": learning_rate, 
                            "val_split": val_split
    }}
    save_snapshot(project_id, snap)
    
    return jsonify({"ok": True, "loss": tr_loss, "val_loss": tr_vloss, "val_mae": tr_vmae, 
                    "model_file": train_out.get('model_file'), "continued": bool(train_out.get('continued')), 
                    "loss_curve": loss_curve, "val_loss_curve": val_loss_curve, "mae_curve": mae_curve, 
                    "val_mae_curve": val_mae_curve, "x": x_axes})
