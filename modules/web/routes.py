from flask import Blueprint, render_template, request, redirect, url_for, abort
from modules.storage.projects import list_projects, create_project, get_project

web_bp = Blueprint("web", __name__, template_folder="../../templates", static_folder="../../static")


@web_bp.route("/")
def index():
    projects = list_projects()
    return render_template("index.html", projects=projects)


@web_bp.route("/project/new", methods=["GET", "POST"])
def project_new():
    if request.method == "POST":
        name = request.form.get("name", "Новый проект")
        description = request.form.get("description", "")
        p = create_project(name=name, description=description)
        return redirect(url_for("web.project_detail", project_id=p["id"]))
    return render_template("project_new.html")


@web_bp.route("/project/<project_id>")
def project_detail(project_id: str):
    p = get_project(project_id)
    if not p:
        abort(404)
    return render_template("project_card.html", project=p)

