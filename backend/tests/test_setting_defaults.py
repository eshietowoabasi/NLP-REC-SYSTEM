"""Tests for raising old setting defaults on existing installations."""

from app.extensions import db


def test_an_old_default_follows_the_raised_default_but_an_admin_choice_stays(app):
    """Synthetic: a stored 50 (the old default) becomes 1000; a value an admin chose is kept."""
    from app.models.configuration import Setting
    from app.settings import get_setting, upgrade_raised_defaults

    db.session.merge(Setting(key="max_documents_per_session", value=50))
    db.session.commit()
    assert upgrade_raised_defaults() == ["max_documents_per_session"]
    assert get_setting("max_documents_per_session") == 1000

    db.session.merge(Setting(key="max_documents_per_session", value=200))
    db.session.commit()
    assert upgrade_raised_defaults() == []
    assert get_setting("max_documents_per_session") == 200
