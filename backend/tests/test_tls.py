"""The opt-in switch to the operating system's certificate store."""

from __future__ import annotations

import sys
import types

import pytest

from app.utils import tls


def test_system_certificates_are_injected_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    fake = types.SimpleNamespace(inject_into_ssl=lambda: calls.append("injected"))
    monkeypatch.setitem(sys.modules, "truststore", fake)
    monkeypatch.setattr(tls, "_injected", False)

    tls.use_system_certificates()
    tls.use_system_certificates()

    assert calls == ["injected"]


def test_create_app_honours_the_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import create_app
    from app.config import TestingConfig

    called: list[bool] = []
    monkeypatch.setattr("app.use_system_certificates", lambda: called.append(True))

    monkeypatch.setattr(TestingConfig, "USE_SYSTEM_CERTS", False)
    create_app("testing")
    monkeypatch.setattr(TestingConfig, "USE_SYSTEM_CERTS", True)
    create_app("testing")

    assert called == [True]
