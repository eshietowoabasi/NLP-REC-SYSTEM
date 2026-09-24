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
    app.config["REPORT_FOLDER"] = str(tmp_path / "reports")


@pytest.fixture()
def core_document(db, make_user):
    """A parsed NUC Core Reference document covering security topics (not cloud)."""
    from app.models import Document, DocumentStatus, FileType, SourceCategory

    from .corpus import THEMES

    admin = make_user("core_admin", role=Role.ADMIN)
    text = "CSC 301: Computer and Network Security\n\n" + "\n\n".join(THEMES["security"])
    document = Document(
        user_id=admin.user_id, title="CCMAS Computer Science Core", file_path="/nonexistent/core.txt",
        file_type=FileType.TXT, source_category=SourceCategory.NUC_CORE,
        processing_status=DocumentStatus.PARSED, extracted_text=text, content_hash="core-fixture",
    )
    db.session.add(document)
    db.session.commit()
    return document


@pytest.fixture()
def completed_session(client, make_user, login, core_document):
    """A planner-owned session that has run the full pipeline (hashing embeddings)."""
    import io

    from .corpus import theme_text

    make_user("planner", role=Role.PLANNER)
    login("planner")
    ids = []
    for theme in ("cloud", "security", "data"):
        resp = client.post("/api/documents", data={"file": (io.BytesIO(theme_text(theme, n=50).encode()), f"{theme}.txt"),
                                                   "source_category": "Job Market Data"}, content_type="multipart/form-data")
        ids.append(resp.json["document"]["document_id"])
    session_id = client.post("/api/sessions", json={
        "session_name": "review", "document_ids": ids,
        "parameter_config": {"similarity_threshold": 0.8, "max_recommendations": 20},
    }).json["session"]["session_id"]
    assert client.post(f"/api/sessions/{session_id}/run").status_code == 202
    assert client.get(f"/api/sessions/{session_id}").json["session"]["status"] == "Completed"
    return session_id
