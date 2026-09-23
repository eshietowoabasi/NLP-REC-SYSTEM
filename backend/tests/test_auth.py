from flask import Blueprint

from app.models import AuditLog, Role
from app.utils.rbac import WRITE_ROLES, roles_required


def test_login_success_sets_session_and_audits(client, make_user, login, db):
    make_user()
    resp = login()
    assert resp.status_code == 200
    assert resp.json["user"]["role"] == "Curriculum Planner"
    assert "password_hash" not in resp.json["user"]

    me = client.get("/api/auth/me")
    assert me.status_code == 200 and me.json["user"]["username"] == "planner"
    assert db.session.query(AuditLog).filter_by(action_type="LOGIN").count() == 1


def test_login_wrong_password_uses_error_model(make_user, login, db):
    make_user()
    resp = login(password="nope")
    assert resp.status_code == 401
    assert resp.json == {
        "success": False,
        "error": {"code": "INVALID_CREDENTIALS", "message": "Invalid username or password", "details": {}},
    }
    assert db.session.query(AuditLog).filter_by(action_type="LOGIN_FAILED").count() == 1


def test_unknown_user_gets_same_message(login):
    resp = login(username="ghost")
    assert resp.status_code == 401 and resp.json["error"]["code"] == "INVALID_CREDENTIALS"


def test_inactive_user_cannot_login(make_user, login):
    make_user(is_active=False)
    assert login().status_code == 401


def test_login_requires_fields(client):
    resp = client.post("/api/auth/login", json={"username": ""})
    assert resp.status_code == 422
    assert set(resp.json["error"]["details"]) == {"username", "password"}


def test_me_requires_auth(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401 and resp.json["error"]["code"] == "UNAUTHORIZED"


def test_logout(client, make_user, login):
    make_user()
    login()
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_roles_required_enforced_server_side(app, client, make_user, login):
    bp = Blueprint("rbac_probe", __name__)

    @bp.post("/write")
    @roles_required(*WRITE_ROLES)
    def write():
        return {"success": True}

    @bp.get("/admin")
    @roles_required(Role.ADMIN)
    def admin_only():
        return {"success": True}

    app.register_blueprint(bp, url_prefix="/probe")

    assert client.post("/probe/write").status_code == 401

    make_user("viewer", role=Role.VIEWER)
    login("viewer")
    resp = client.post("/probe/write")
    assert resp.status_code == 403 and resp.json["error"]["code"] == "FORBIDDEN"
    client.post("/api/auth/logout")

    make_user("planner")
    login("planner")
    assert client.post("/probe/write").status_code == 200
    assert client.get("/probe/admin").status_code == 403
    client.post("/api/auth/logout")

    make_user("admin", role=Role.ADMIN)
    login("admin")
    assert client.get("/probe/admin").status_code == 200


def test_unknown_route_uses_error_model(client):
    resp = client.get("/api/does-not-exist")
    assert resp.status_code == 404 and resp.json["error"]["code"] == "NOT_FOUND"


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200 and resp.json["database"] == "ok"
