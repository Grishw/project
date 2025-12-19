import json
from datetime import datetime
from uuid import uuid4
import os

def _models_registry(save_dir: str) -> str:
    return os.path.join(save_dir, 'models.json')


def _active_model_path(save_dir: str) -> str:
    return os.path.join(save_dir, 'active_model.txt')


def _load_models(save_dir: str) -> list[dict]:
    path = _models_registry(save_dir)
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_models(save_dir: str, models: list[dict]):
    with open(_models_registry(save_dir), 'w', encoding='utf-8') as f:
        json.dump(models, f, ensure_ascii=False, indent=2)


def set_active_model(save_dir: str, model_file: str):
    with open(_active_model_path(save_dir), 'w', encoding='utf-8') as f:
        f.write(model_file)


def get_active_model(save_dir: str) -> str | None:
    path = _active_model_path(save_dir)
    if not os.path.exists(path):
        return None
    return open(path, encoding='utf-8').read().strip()
