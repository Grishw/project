from .blueprint import project_bp
from flask import request, jsonify
from modules.storage.projects import get_project, update_project, save_snapshot, load_snapshot, save_snapshot_metadata, load_snapshot_metadata, get_data_file_path, delete_project
from modules.data.ingest import save_uploaded_csv, dataframe_preview, sample_columns, restore_full_snapshot_from_metadata

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
    target_requrent = None
    target_requrent_column_name = None
    
    # Собираем названия столбцов для извлечения
    cols.append(target)

    for item in features:
        if item != target:
            cols.append(item)
        else:
            target_requrent = target
            target_requrent_column_name = target_requrent+'_shift'
    
    # Если пользователь указал временную колонку — добавим её в сэмпл для построения оси X
    time_meta = payload.get("time") or {}
    time_column = time_meta.get("column") or None
    if time_column and time_column not in cols:
        cols.append(time_column)

    time = {"column": time_column, "kind": time_kind, "format": time_format}
    
    # Собираем данные
    data = sample_columns(project["data_path"], cols, target_requrent=target_requrent, limit=1000)

    # Обновляем данные проекта
    update_project(project_id, target=target, features=features, target_requrent=target_requrent_column_name, status="selected")


    # Обновляем метаданные
    metadata = load_snapshot_metadata(project_id) or {}
    metadata["selection"] = {"target": target, "features": features, "target_requrent": target_requrent_column_name}
    metadata["time"] = time
    save_snapshot_metadata(project_id, metadata)
    
    # Сохраняем только sample для быстрого доступа
    snap = load_snapshot(project_id) or {}
    snap["sample"] = data
    snap["time"] = time
    save_snapshot(project_id, snap)
    
    return jsonify({"ok": True, "data": data, "time": time})
