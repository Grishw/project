from .blueprint import project_bp
from flask import request, jsonify
from modules.storage.projects import get_project, update_project, save_snapshot, load_snapshot, save_snapshot_metadata, load_snapshot_metadata, get_data_file_path, delete_project
from modules.data.ingest import save_uploaded_csv, dataframe_preview, sample_columns, restore_full_snapshot_from_metadata
from modules.data.preprocess import preprocess_pipeline

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

    # Обновляем метаданные
    metadata = load_snapshot_metadata(project_id) or {}
    metadata["preprocess"] = {"target": target, "method": method}
    save_snapshot_metadata(project_id, metadata)
   
    time_meta = (metadata.get("time") or {}) if isinstance(metadata, dict) else {}
    time_col = time_meta.get("column")
    if time_col:
        df_info = sample_columns(project["data_path"], [target, time_col])
    else:
        df_info = sample_columns(project["data_path"], [target])

    import pandas as pd
    df = pd.DataFrame(df_info["records"]) 
    out = preprocess_pipeline(df, target=target, method=method)
    seg = out["segment"].to_dict(orient="records")

    update_project(project_id, preprocessed=True)
    
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

