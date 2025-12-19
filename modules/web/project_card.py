import os
from flask import Blueprint, render_template,  jsonify, abort, redirect, url_for
from modules.storage.projects import get_project, load_snapshot,  load_snapshot_metadata, get_data_file_path, delete_project
from modules.data.ingest import restore_full_snapshot_from_metadata

project_card_bp = Blueprint(
    "project_card", __name__, url_prefix="/project",
    template_folder="../../templates", static_folder="../../static"
)


BASE_DATA_DIR = os.path.abspath(os.path.join(os.getcwd(), "data", "projects"))


@project_card_bp.route("/<project_id>/edit")
def view(project_id: str):
    project = get_project(project_id)
    if not project:
        abort(404)
    
    # Загружаем метаданные снапшота
    metadata = load_snapshot_metadata(project_id)
    data_path = get_data_file_path(project_id)
    snapshot_old= load_snapshot(project_id) or {}
    snapshot = restore_full_snapshot_from_metadata(project_id, metadata, data_path, snapshot_old)
    
    return render_template("project_view.html", project=project, snapshot=snapshot)


@project_card_bp.route("/<project_id>/delete", methods=["GET", "POST"])
def project_delete(project_id: str):
    project = get_project(project_id)
    if not project:
        return jsonify({"error": "Проект не найден"}), 404
    
    ok = delete_project(project_id)
    if not ok:
        return jsonify({"error": "Ошибка при удалении проекта"}), 500
    # После удаления возвращаемся на главную
    return redirect(url_for("web.index"))