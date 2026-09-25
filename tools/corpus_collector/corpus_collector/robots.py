"""robots.txt rules, checked before every request.

``urllib.robotparser`` is used as asked, but it compares paths literally and does not
understand the ``*`` and ``$`` wildcards that sites such as MyJobMag use (``Disallow: /*?``).
A URL is therefore only allowed when both robotparser *and* a wildcard-aware matcher allow it.
URLs with a query string are never requested at all.
"""

from __future__ import annotations

import re
import urllib.robotparser
from dataclasses import dataclass, field
from urllib.parse import urlsplit


def _rule_regex(path: str) -> re.Pattern[str]:
    """Google-style robots path pattern: ``*`` matches anything, a final ``$`` anchors."""
    anchored = path.endswith("$")
    body = path[:-1] if anchored else path
    regex = "".join(".*" if char == "*" else re.escape(char) for char in body)
    return re.compile("^" + regex + ("$" if anchored else ""))


@dataclass
class RobotsRules:
    """Allow/Disallow rules of the ``User-agent: *`` group (and a matching named group)."""

    user_agent: str
    parser: urllib.robotparser.RobotFileParser = field(init=False)
    allows: list[str] = field(default_factory=list)
    disallows: list[str] = field(default_factory=list)

    @classmethod
    def parse(cls, text: str, user_agent: str) -> RobotsRules:
        rules = cls(user_agent)
        rules.parser = urllib.robotparser.RobotFileParser()
        rules.parser.parse(text.splitlines())
        applies = False
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, value = (part.strip() for part in line.split(":", 1))
            key = key.lower()
            if key == "user-agent":
                applies = value == "*" or value.lower() in user_agent.lower()
            elif applies and key == "disallow" and value:
                rules.disallows.append(value)
            elif applies and key == "allow" and value:
                rules.allows.append(value)
        return rules

    def allowed(self, url: str, allow_query: bool = False) -> bool:
        """True only if no rule (literal or wildcard) forbids the URL.

        URLs with a query string are refused unless ``allow_query`` is set, which is only done
        for a documented public API (Remotive); rules are then checked against the full path
        and query, so ``Disallow: /*?`` still blocks it.
        """
        parts = urlsplit(url)
        if (parts.query or "?" in url) and not allow_query:
            return False
        if not self.parser.can_fetch(self.user_agent, url):
            return False
        path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        # Longest matching rule wins; on a tie Allow wins (as Google specifies).
        best: tuple[int, bool] | None = None
        for pattern, allow in [(p, True) for p in self.allows] + [
            (p, False) for p in self.disallows
        ]:
            if _rule_regex(pattern).match(path):
                candidate = (len(pattern), allow)
                if best is None or candidate[0] > best[0] or (candidate[0] == best[0] and allow):
                    best = candidate
        return best is None or best[1]
