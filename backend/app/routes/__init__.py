def register_blueprints(app):
    from . import (
        admin,
        auth,
        dashboard,
        documents,
        health,
        mappings,
        recommendations,
        reports,
        results,
        sessions,
    )

    for blueprint, prefix in (
        (health.bp, "/api"),
        (auth.bp, "/api/auth"),
        (dashboard.bp, "/api/dashboard"),
        (documents.bp, "/api/documents"),
        (sessions.bp, "/api/sessions"),
        (results.bp, "/api/sessions"),
        (recommendations.sessions_bp, "/api/sessions"),
        (mappings.sessions_bp, "/api/sessions"),
        (reports.sessions_bp, "/api/sessions"),
        (recommendations.bp, "/api/recommendations"),
        (mappings.rec_bp, "/api/recommendations"),
        (mappings.bp, "/api/mappings"),
        (reports.bp, "/api/reports"),
        (admin.bp, "/api/admin"),
    ):
        app.register_blueprint(blueprint, url_prefix=prefix)
