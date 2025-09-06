import json
import os
import uuid
import shutil
from typing import Any, Dict, List, Optional


DATA_DIR = os.path.abspath(os.path.join(os.getcwd(), "data"))
PROJECTS_FILE = os.path.join(DATA_DIR, "projects.json")


def ensure_data_dir() -> None:
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)


def _read_all() -> List[Dict[str, Any]]:
    ensure_data_dir()
    if not os.path.exists(PROJECTS_FILE):
        return []
    try:
        with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _write_all(items: List[Dict[str, Any]]) -> None:
    ensure_data_dir()
    with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def list_projects() -> List[Dict[str, Any]]:
    return _read_all()


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    for p in _read_all():
        if p.get("id") == project_id:
            return p
    return None


def create_project(name: str, description: str = "") -> Dict[str, Any]:
    items = _read_all()
    project = {
        "id": str(uuid.uuid4()),
        "name": name.strip() or "Новый проект",
        "description": description.strip(),
        "thumb": None,
        "status": "new",
    }
    items.insert(0, project)
    _write_all(items)
    return project


def update_project(project_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
    items = _read_all()
    for idx, p in enumerate(items):
        if p.get("id") == project_id:
            p.update(fields)
            items[idx] = p
            _write_all(items)
            return p
    return None


def delete_project(project_id: str) -> bool:
    items = _read_all()
    new_items = [p for p in items if p.get("id") != project_id]
    if len(new_items) != len(items):
        _write_all(new_items)
        # Удаляем папку проекта и все файлы
        project_path = os.path.join(DATA_DIR, "projects", project_id)
        if os.path.exists(project_path):
            shutil.rmtree(project_path)
        return True
    return False


def project_dir(project_id: str) -> str:
    ensure_data_dir()
    path = os.path.join(DATA_DIR, "projects", project_id)
    os.makedirs(path, exist_ok=True)
    return path


def save_snapshot(project_id: str, data: Dict[str, any]) -> str:
    path = os.path.join(project_dir(project_id), "snapshot.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def load_snapshot(project_id: str) -> Optional[Dict[str, any]]:
    path = os.path.join(project_dir(project_id), "snapshot.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_snapshot_metadata(project_id: str, metadata: Dict[str, any]) -> str:
    """Сохраняет метаданные снапшота (имена файлов и конфигурацию)"""
    path = os.path.join(project_dir(project_id), "snapshot_meta.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    return path


def load_snapshot_metadata(project_id: str) -> Optional[Dict[str, any]]:
    """Загружает метаданные снапшота"""
    path = os.path.join(project_dir(project_id), "snapshot_meta.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_data_file_path(project_id: str) -> Optional[str]:
    """Получает путь к файлу данных проекта"""
    project = get_project(project_id)
    if not project or not project.get("data_path"):
        return None
    return project["data_path"]


def get_artifacts_dir(project_id: str) -> str:
    """Получает путь к папке с артефактами проекта"""
    return os.path.join(project_dir(project_id), "artifacts")

