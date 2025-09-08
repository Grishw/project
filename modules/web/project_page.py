import os
from flask import Blueprint, render_template, request, jsonify, abort
from modules.storage.projects import get_project, update_project, save_snapshot, load_snapshot, save_snapshot_metadata, load_snapshot_metadata, get_data_file_path, delete_project
from modules.data.ingest import save_uploaded_csv, dataframe_preview, sample_columns, restore_full_snapshot_from_metadata
from modules.data.preprocess import preprocess_pipeline
from modules.models.tf_models import ModelConfig, train_and_predict, train_model, iterative_forecast
import math


project_bp = Blueprint(
    "project_page", __name__, url_prefix="/project",
    template_folder="../../templates", static_folder="../../static"
)


BASE_DATA_DIR = os.path.abspath(os.path.join(os.getcwd(), "data", "projects"))


@project_bp.route("/<project_id>/view")
def view(project_id: str):
    project = get_project(project_id)
    if not project:
        abort(404)
    
    # Загружаем метаданные снапшота
    metadata = load_snapshot_metadata(project_id)
    data_path = get_data_file_path(project_id)
    
    if metadata and data_path:
        # Восстанавливаем снапшот из метаданных
        snapshot = restore_full_snapshot_from_metadata(project_id, metadata, data_path)
    else:
        # Fallback на старый формат снапшота
        snapshot = load_snapshot(project_id) or {}
    
    return render_template("project_view.html", project=project, snapshot=snapshot)


@project_bp.route("/<project_id>/delete", methods=["GET", "POST"])
def project_delete(project_id: str):
    project = get_project(project_id)
    if not project:
        return jsonify({"error": "Проект не найден"}), 404
    
    ok = delete_project(project_id)
    if not ok:
        return jsonify({"error": "Ошибка при удалении проекта"}), 500
    # После удаления возвращаемся на главную
    from flask import redirect, url_for
    return redirect(url_for("web.index"))


@project_bp.route("/<project_id>/upload", methods=["POST"])
def upload(project_id: str):
    project = get_project(project_id)
    if not project:
        abort(404)
    if "file" not in request.files:
        return jsonify({"error": "Файл не найден"}), 400
    f = request.files["file"]
    if not f.filename.lower().endswith(".csv"):
        return jsonify({"error": "Ожидается CSV"}), 400

    path, file_exists = save_uploaded_csv(f, BASE_DATA_DIR, project_id)
    
    # Проверяем, изменилось ли имя файла
    current_filename = os.path.basename(path)
    previous_filename = os.path.basename(project.get("data_path", "")) if project.get("data_path") else None
    
    # Если имя файла изменилось или файл не существовал ранее, пересоздаем снапшот
    should_recreate_snapshot = (current_filename != previous_filename) or not file_exists
    
    update_project(project_id, data_path=path, status="uploaded")
    preview = dataframe_preview(path)
    
    if should_recreate_snapshot:
        # Пересоздаем метаданные снапшота с нуля
        metadata = {"has_preview": True}
        save_snapshot_metadata(project_id, metadata)
        # Сохраняем только preview для быстрого доступа
        save_snapshot(project_id, {"preview": preview})
    else:
        # Обновляем только метаданные
        metadata = load_snapshot_metadata(project_id) or {}
        metadata["has_preview"] = True
        save_snapshot_metadata(project_id, metadata)
        # Обновляем только preview в существующем снапшоте
        snap = load_snapshot(project_id) or {}
        snap["preview"] = preview
        save_snapshot(project_id, snap)
    
    return jsonify({"ok": True, "preview": preview, "recreated": should_recreate_snapshot})


@project_bp.route("/<project_id>/select", methods=["POST"])
def select_columns(project_id: str):
    project = get_project(project_id)
    if not project or not project.get("data_path"):
        return jsonify({"error": "Данные не загружены"}), 400

    payload = request.get_json(silent=True) or {}
    target = payload.get("target")
    features = payload.get("features", [])
    time_meta = payload.get("time") or {}
    time_column = time_meta.get("column") or None
    time_kind = time_meta.get("kind") or "index"
    time_format = time_meta.get("format") or None
    cols = []
    if target:
        cols.append(target)
    cols.extend([c for c in features if c and c != target])
    # Если пользователь указал временную колонку — добавим её в сэмпл для построения оси X
    time_meta = payload.get("time") or {}
    time_column = time_meta.get("column") or None
    if time_column and time_column not in cols:
        cols.append(time_column)
    data = sample_columns(project["data_path"], cols)
    update_project(project_id, target=target, features=features, status="selected")
    
    # Обновляем метаданные
    metadata = load_snapshot_metadata(project_id) or {}
    metadata["selection"] = {"target": target, "features": features}
    metadata["time"] = {"column": time_column, "kind": time_kind, "format": time_format}
    save_snapshot_metadata(project_id, metadata)
    
    # Сохраняем только sample для быстрого доступа
    snap = load_snapshot(project_id) or {}
    snap["sample"] = data
    snap["time"] = {"column": time_column, "kind": time_kind, "format": time_format}
    save_snapshot(project_id, snap)
    
    return jsonify({"ok": True, "data": data, "time": {"column": time_column, "kind": time_kind, "format": time_format}})


@project_bp.route("/<project_id>/preprocess", methods=["POST"])
def preprocess(project_id: str):
    project = get_project(project_id)
    if not project or not project.get("data_path"):
        return jsonify({"error": "Данные не загружены"}), 400
    payload = request.get_json(silent=True) or {}
    target = payload.get("target") or project.get("target")
    method = payload.get("method", "cusum")
    if not target:
        return jsonify({"error": "Не указан target"}), 400
   
    # читаем нужные столбцы
    df_info = sample_columns(project["data_path"], [target])
    import pandas as pd
    df = pd.DataFrame(df_info["records"])  # ограниченный набор для демо; позже читать весь файл постранично
    out = preprocess_pipeline(df, target=target, method=method)
    seg = out["segment"].to_dict(orient="records")
    update_project(project_id, preprocessed=True)
    
    # Обновляем метаданные
    metadata = load_snapshot_metadata(project_id) or {}
    metadata["preprocess"] = {"target": target, "method": method}
    save_snapshot_metadata(project_id, metadata)
    
    # Построим ось времени X, если указана временная колонка
    time_meta = (metadata.get("time") or {}) if isinstance(metadata, dict) else {}
    time_col = time_meta.get("column")
    x_pp = None
    try:
        if time_col:
            # Загружаем такой же объём строк, что и использовался для df_info
            usecols = [c for c in [time_col, target] if c]
            df_all = pd.read_csv(project["data_path"], usecols=usecols)
            n = len(df_info["records"]) if isinstance(df_info.get("records"), list) else None
            if n is not None:
                df_all = df_all.head(n)
            kind = time_meta.get("kind", "index")
            fmt = time_meta.get("format")
            if kind in ("timestamp_sec", "timestamp_ms"):
                unit = "s" if kind == "timestamp_sec" else "ms"
                t = pd.to_datetime(df_all[time_col], unit=unit, errors="coerce")
            elif kind == "datetime_format" and fmt:
                t = pd.to_datetime(df_all[time_col], format=fmt, errors="coerce")
            elif kind in ("iso_date", "rfc_2822", "human_readable"):
                t = pd.to_datetime(df_all[time_col], errors="coerce")
            else:
                t = None
            if t is not None:
                x_base = t.dt.tz_localize(None) if hasattr(t, 'dt') else t
                x_pp = [d.isoformat() if hasattr(d, 'isoformat') else str(d) for d in x_base]
    except Exception:
        x_pp = None

    # Сохраняем только результаты предобработки для быстрого доступа
    snap = load_snapshot(project_id) or {}
    snap["preprocess"] = {"segment": {"columns": list(out["segment"].columns), "records": seg}, "bounds": out["bounds"], "curve": out["curve"], "x": x_pp}
    save_snapshot(project_id, snap)
    
    return jsonify({
        "ok": True,
        "segment": {"columns": list(out["segment"].columns), "records": seg},
        "bounds": out["bounds"],
        "curve": out["curve"],
        "x": x_pp,
    })


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

    loss_curve = sanitize_array(train_out.get('loss_curve')) or []
    val_loss_curve = sanitize_array(train_out.get('val_loss_curve')) or []
    mae_curve = sanitize_array(train_out.get('mae_curve')) or []
    val_mae_curve = sanitize_array(train_out.get('val_mae_curve')) or []

    snap = load_snapshot(project_id) or {}
    snap["train"] = {"loss": tr_loss, "val_loss": tr_vloss, "val_mae": tr_vmae, "model_file": train_out.get('model_file'), "loss_curve": loss_curve, "val_loss_curve": val_loss_curve, "mae_curve": mae_curve, "val_mae_curve": val_mae_curve, "x": x_axes, "cfg": {
      "model": model_type, "window": window, "horizon": horizon, "epochs": epochs, "batch_size": batch_size, "learning_rate": learning_rate, "val_split": val_split
    }}
    save_snapshot(project_id, snap)
    
    return jsonify({"ok": True, "loss": tr_loss, "val_loss": tr_vloss, "val_mae": tr_vmae, "model_file": train_out.get('model_file'), "continued": bool(train_out.get('continued')), "loss_curve": loss_curve, "val_loss_curve": val_loss_curve, "mae_curve": mae_curve, "val_mae_curve": val_mae_curve, "x": x_axes})


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

    y_pred = iterative_forecast(series, model_path, window=window, steps=steps, horizon=horizon, context=context)

    # Подготовим временную ось продолжения
    x_future = None
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
                x_base = t.dt.tz_localize(None) if hasattr(t, 'dt') else t
                diffs = x_base.diff().dropna()
                step = diffs.median() if not diffs.empty else pd.Timedelta(seconds=1)
                last = x_base.iloc[-1]
                x_future = [ (last + step * (i+1)).isoformat() for i in range(steps) ]
    except Exception:
        x_future = None

    return jsonify({"ok": True, "prediction": y_pred.tolist(), "x": {"future": x_future}})

