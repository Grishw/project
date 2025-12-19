from flask import Blueprint

project_bp = Blueprint(
    "project_page",
    __name__,
    url_prefix="/project",
    template_folder="../../../templates",
    static_folder="../../../static"
)