"""Map free-form recording titles to a public body using explicit keyword rules.

Deliberately conservative: a title that names no body returns ``None`` and goes to human
review. "Regular Monthly Meeting" is very likely Town Council, but publishing a guess as
fact is exactly the failure this project exists to prevent.
"""

import re

# Acronyms are case-sensitive so "arb" inside a word like "harbor" never matches.
_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bplanning commission\b", re.I), "Planning Commission"),
    (re.compile(r"(?i:\barchitectural review board\b)|\bARB\b"), "Architectural Review Board"),
    (re.compile(r"(?i:\bboard of zoning appeals\b)|\bBZA\b"), "Board of Zoning Appeals"),
    (re.compile(r"\btown council\b|\bmayor and council\b", re.I), "Town Council"),
]


def classify_body(title: str) -> str | None:
    matches = {body for pattern, body in _RULES if pattern.search(title)}
    # Two bodies in one title (e.g. a joint session) is ambiguous: let a person decide.
    return matches.pop() if len(matches) == 1 else None
