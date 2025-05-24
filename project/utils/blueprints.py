from flask import Flask

def register_blueprints(app: Flask) -> None:
    from project.views.main import views
    from project.views.auth import auth

    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/auth")