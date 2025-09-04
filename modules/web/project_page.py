import os
from flask import Blueprint, render_template, request, jsonify, abort
from modules.storage.projects import get_project, update_project, save_snapshot, load_snapshot
from modules.data.ingest import save_uploaded_csv, dataframe_preview, sample_columns
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
    snapshot = load_snapshot(project_id) or {}
    return render_template("project_view.html", project=project, snapshot=snapshot)


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
    path = save_uploaded_csv(f, BASE_DATA_DIR, project_id)
    update_project(project_id, data_path=path, status="uploaded")
    preview = dataframe_preview(path)
    save_snapshot(project_id, {"preview": preview})
    return jsonify({"ok": True, "preview": preview})


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
    snap = load_snapshot(project_id) or {}
    snap.update({"selection": {"target": target, "features": features}, "sample": data})
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
    snap = load_snapshot(project_id) or {}
    snap.update({"preprocess": {"segment": {"columns": list(out["segment"].columns), "records": seg}, "bounds": out["bounds"], "curve": out["curve"]}})
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
    snap = load_snapshot(project_id) or {}
    snap.update({"train": {"loss": out['loss'], "prediction": out['prediction'], "cfg": {
      "model": model_type, "window": window, "horizon": horizon, "epochs": epochs
    }}})
    save_snapshot(project_id, snap)
    return jsonify({"ok": True, "loss": out['loss'], "prediction": out['prediction']})

