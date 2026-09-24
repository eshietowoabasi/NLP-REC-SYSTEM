import pytest

from app import create_app
from app.extensions import db as _db
from app.models import Role, User


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()
        _db.engine.dispose()  # each test builds a new app; release its connection pool


@pytest.fixture()
def db(app):
    return _db


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_user(db):
    def _make(username="planner", password="s3cret-pass", role=Role.PLANNER, is_active=True):
        user = User(username=username, email=f"{username}@uniuyo.edu.ng", role=role, is_active=is_active)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    return _make


@pytest.fixture()
def login(client):
    def _login(username="planner", password="s3cret-pass"):
        return client.post("/api/auth/login", json={"username": username, "password": password})

    return _login


@pytest.fixture(autouse=True)
def _upload_folder(app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
