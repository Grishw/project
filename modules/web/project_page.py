import os
from flask import Blueprint, render_template, request, jsonify, abort
from modules.storage.projects import get_project, update_project, save_snapshot, load_snapshot, save_snapshot_metadata, load_snapshot_metadata, get_data_file_path, delete_project
from modules.data.ingest import save_uploaded_csv, dataframe_preview, sample_columns, restore_full_snapshot_from_metadata
from modules.data.preprocess import preprocess_pipeline
from modules.models.tf_models import ModelConfig, train_and_predict


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


@project_bp.route("/<project_id>/delete")
def project_delete(project_id: str):
    project = get_project(project_id)
    if not project:
        return jsonify({"error": "Проект не найден"}), 404
    
    success = delete_project(project_id)
    if success:
        consol.log(jsonify({"ok": True, "message": "Проект успешно удален"})) 
        return render_template("index.html", projects=projects)
    else:
        return jsonify({"error": "Ошибка при удалении проекта"}), 500

    return render_template("index.html", projects=projects)


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
    cols = []
    if target:
        cols.append(target)
    cols.extend([c for c in features if c and c != target])
    data = sample_columns(project["data_path"], cols)
    update_project(project_id, target=target, features=features, status="selected")
    
    # Обновляем метаданные
    metadata = load_snapshot_metadata(project_id) or {}
    metadata["selection"] = {"target": target, "features": features}
    save_snapshot_metadata(project_id, metadata)
    
    # Сохраняем только sample для быстрого доступа
    snap = load_snapshot(project_id) or {}
    snap["sample"] = data
    save_snapshot(project_id, snap)
    
    return jsonify({"ok": True, "data": data})


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
    
    # Сохраняем только результаты предобработки для быстрого доступа
    snap = load_snapshot(project_id) or {}
    snap["preprocess"] = {"segment": {"columns": list(out["segment"].columns), "records": seg}, "bounds": out["bounds"], "curve": out["curve"]}
    save_snapshot(project_id, snap)
    
    return jsonify({
        "ok": True,
        "segment": {"columns": list(out["segment"].columns), "records": seg},
        "bounds": out["bounds"],
        "curve": out["curve"],
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
    if not target:
        return jsonify({"error": "Не указан target"}), 400
    # Загружаем весь target столбец (для простоты демо)
    import pandas as pd
    df = pd.read_csv(project["data_path"], usecols=[target])
    series = df[target].astype(float).to_numpy()
    cfg = ModelConfig(model_type=model_type, window=window, horizon=horizon, epochs=epochs)
    out = train_and_predict(series, cfg, save_dir=os.path.join(BASE_DATA_DIR, project_id, "artifacts"))
    update_project(project_id, model=model_type, horizon=horizon, status="trained")
    
    # Обновляем метаданные
    metadata = load_snapshot_metadata(project_id) or {}
    metadata["train"] = {
        "target": target,
        "cfg": {"model": model_type, "window": window, "horizon": horizon, "epochs": epochs}
    }
    save_snapshot_metadata(project_id, metadata)
    
    # Сохраняем только результаты обучения для быстрого доступа
    snap = load_snapshot(project_id) or {}
    snap["train"] = {"loss": out['loss'], "prediction": out['prediction'], "cfg": {
      "model": model_type, "window": window, "horizon": horizon, "epochs": epochs
    }}
    save_snapshot(project_id, snap)
    
    return jsonify({"ok": True, "loss": out['loss'], "prediction": out['prediction']})

