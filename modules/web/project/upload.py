
from .blueprint import project_bp
import os
from flask import request, jsonify, abort
from modules.storage.projects import get_project, update_project, save_snapshot, load_snapshot, save_snapshot_metadata, load_snapshot_metadata
from modules.data.ingest import save_uploaded_csv, dataframe_preview

BASE_DATA_DIR = os.path.abspath(os.path.join(os.getcwd(), "data", "projects"))

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