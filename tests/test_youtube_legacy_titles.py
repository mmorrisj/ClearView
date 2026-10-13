import json
from datetime import date, time
from pathlib import Path

import pytest

from lt.discovery.youtube.legacy_titles import parse_title

FIXTURES = Path(__file__).parent / "fixtures" / "youtube" / "legacy_titles.json"


def _videos() -> list[dict[str, str]]:
    data: list[dict[str, str]] = json.loads(FIXTURES.read_text())
    return data


@pytest.mark.parametrize(
    ("title", "body", "meeting_type", "on", "at"),
    [
        (
            "Jun 17 2024 0700 PM Planning Commission Regular Meeting SD 480",
            "Planning Commission",
            "Regular Meeting",
            date(2024, 6, 17),
            time(19, 0),
        ),
        (
            "May 6 2024 0600 PM Mayor and Council Budget Work Session SD 480",
            "Town Council",
            "Budget Work Session",
            date(2024, 5, 6),
            time(18, 0),
        ),
        (
            "May 6 2024 0700 PM Mayor and Council Public Hearing Regular Meeting SD 480",
            "Town Council",
            "Public Hearing Regular Meeting",
            date(2024, 5, 6),
            time(19, 0),
        ),
        (
            "Mar 27 2024 0600 PM Board of Zoning Appeals Informational Meeting SD 480",
            "Board of Zoning Appeals",
            "Informational Meeting",
            date(2024, 3, 27),
            time(18, 0),
        ),
        (
            "Dec 15 2021 0700 PM Architectural Review Board Regular Meeting SD 480",
            "Architectural Review Board",
            "Regular Meeting",
            date(2021, 12, 15),
            time(19, 0),
        ),
    ],
)
def test_parse_title(title: str, body: str, meeting_type: str, on: date, at: time) -> None:
    parsed = parse_title(title)

    assert parsed is not None
    assert parsed.body_name == body
    assert parsed.meeting_type == meeting_type
    assert parsed.meeting_date == on
    assert parsed.start_time == at


@pytest.mark.parametrize(
    "title",
    [
        "Copy of Town Council regular meeting continued",  # real, no date: needs human triage
        "Jun 17 2024 0700 PM Parks Committee Regular Meeting SD 480",  # unknown body
        "Feb 30 2024 0700 PM Planning Commission Regular Meeting SD 480",  # impossible date
        "",
    ],
)
def test_unparseable_titles_return_none(title: str) -> None:
    assert parse_title(title) is None


def test_every_real_title_but_the_untitled_copy_parses() -> None:
    unparsed = [v["title"] for v in _videos() if parse_title(v["title"]) is None]

    assert unparsed == ["Copy of Town Council regular meeting continued"]
