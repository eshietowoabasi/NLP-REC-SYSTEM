"""Keep docs/API.md in step with the code: every API route must be documented."""
import re
from pathlib import Path

API_DOC = Path(__file__).resolve().parents[2] / "docs" / "API.md"


def test_every_api_route_is_documented(app):
    documented = set()
    for method, path in re.findall(r"\|\s*([A-Z/]+)\s*\|\s*`(/api/[^`]+)`", API_DOC.read_text()):
        for m in method.split("/"):
            documented.add((m, re.sub(r"\{[^}]+\}", "{}", path)))
    missing = []
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api"):
            continue
        path = re.sub(r"<[^>]+>", "{}", rule.rule)
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            if (method, path) not in documented:
                missing.append(f"{method} {rule.rule}")
    assert not missing, f"Routes missing from docs/API.md: {missing}"
