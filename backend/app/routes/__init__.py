def register_blueprints(app):
    from .auth import bp as auth_bp
    from .health import bp as health_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
