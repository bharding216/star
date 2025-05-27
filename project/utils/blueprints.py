from flask import Flask

def register_blueprints(app: Flask) -> None:
    from project.views.main import views
    from project.views.auth import auth
    from project.views.star import star
    from project.views.se_legacy import se_legacy

    app.register_blueprint(views, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/auth")
    app.register_blueprint(star, url_prefix="/")
    app.register_blueprint(se_legacy, url_prefix="/")