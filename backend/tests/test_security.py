from datetime import timedelta

import pytest

from app.models import AuditLog, Role


def test_security_headers_on_api(client):
    resp = client.get("/api/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Cache-Control"] == "no-store"
    assert "default-src 'none'" in resp.headers["Content-Security-Policy"]


@pytest.mark.parametrize("header", ["Origin", "Referer"])
def test_cross_site_writes_refused(client, make_user, header):
    make_user()
    evil = {header: "https://evil.example.com/page"}
    resp = client.post("/api/auth/login", json={"username": "planner", "password": "s3cret-pass"}, headers=evil)
    assert resp.status_code == 403 and resp.json["error"]["code"] == "CSRF_ORIGIN_MISMATCH"


def test_same_origin_and_headerless_writes_allowed(client, make_user):
    make_user()
    ok = client.post("/api/auth/login", json={"username": "planner", "password": "s3cret-pass"}, headers={"Origin": "http://localhost"})
    assert ok.status_code == 200
    assert client.post("/api/auth/logout").status_code == 200  # no Origin: CLI / scripts
    assert client.get("/api/health", headers={"Origin": "https://evil.example.com"}).status_code == 200  # reads unaffected


def test_trusted_origins(app, client, make_user):
    make_user()
    app.config["TRUSTED_ORIGINS"] = ("curriculum.uniuyo.edu.ng",)
    resp = client.post("/api/auth/login", json={"username": "planner", "password": "s3cret-pass"},
                       headers={"Origin": "https://curriculum.uniuyo.edu.ng"})
    assert resp.status_code == 200


def test_malformed_origin_refused(client):
    assert client.post("/api/auth/logout", headers={"Origin": "null"}).status_code == 403


def test_account_locked_after_repeated_failures(app, client, make_user, login, db):
    make_user()
    for _ in range(5):
        assert login(password="wrong").status_code == 401
    locked = login()  # even the right password is refused while locked
    assert locked.status_code == 429 and locked.json["error"]["code"] == "ACCOUNT_LOCKED"
    assert 1 <= locked.json["error"]["details"]["retry_after_minutes"] <= 15
    assert db.session.query(AuditLog).filter_by(action_type="LOGIN_BLOCKED").count() == 1

    # Failures older than the window no longer count.
    for entry in db.session.query(AuditLog).filter_by(action_type="LOGIN_FAILED"):
        entry.action_timestamp = entry.action_timestamp - timedelta(minutes=16)
    db.session.commit()
    assert login().status_code == 200


def test_successful_login_resets_failure_count(client, make_user, login):
    make_user()
    for _ in range(4):
        login(password="wrong")
    assert login().status_code == 200
    client.post("/api/auth/logout")
    for _ in range(4):
        assert login(password="wrong").status_code == 401  # counting restarted after the success
    assert login().status_code == 200


def test_unknown_usernames_are_not_locked(client, login):
    for _ in range(6):
        assert login(username="ghost", password="x").status_code == 401


def test_session_cookie_flags(client, make_user, login):
    make_user()
    resp = login()
    cookie = next(c for c in resp.headers.getlist("Set-Cookie") if c.startswith("session="))
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie and "Expires=" in cookie


def test_production_config_validation(monkeypatch):
    from app.config import ProductionConfig

    monkeypatch.setenv("SECRET_KEY", "short")
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("EMBEDDING_BACKEND", "hashing")
    with pytest.raises(RuntimeError) as exc:
        ProductionConfig.validate()
    assert "SECRET_KEY" in str(exc.value) and "EMBEDDING_BACKEND" in str(exc.value)
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    monkeypatch.setenv("EMBEDDING_BACKEND", "sbert")
    ProductionConfig.validate()


def test_cli_rejects_short_password(app):
    result = app.test_cli_runner().invoke(args=["create-user", "--username", "u", "--email", "u@x.ng", "--password", "short"])
    assert result.exit_code != 0 and "at least 8" in result.output
