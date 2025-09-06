from flask import Flask
from flask import render_template

def create_app() -> Flask:
    app = Flask(__name__)

    # Blueprint регистрация откладывается до импорта
    from modules.web.routes import web_bp
    from modules.web.project_page import project_bp
    app.register_blueprint(web_bp)
    app.register_blueprint(project_bp)

    return app


app = create_app()


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(debug=True)