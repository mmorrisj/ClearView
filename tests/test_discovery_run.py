from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from lt.db.models import Body, Meeting
from lt.discovery.run import DiscoveryReport, discover_youtube
from lt.discovery.sources import SourceConfig
from lt.discovery.youtube.api import YouTubeClient
from tests.youtube_fakes import fake_youtube_transport

pytestmark = pytest.mark.db

CONFIG = SourceConfig.load(Path("config/sources/haymarket.json"))
SEPTEMBER = (date(2026, 9, 1), date(2026, 9, 30))


def _run(session: Session, config: SourceConfig = CONFIG) -> DiscoveryReport:
    client = YouTubeClient(api_key="k", transport=fake_youtube_transport())
    return discover_youtube(session, client, config, start=SEPTEMBER[0], end=SEPTEMBER[1])


def _meetings(session: Session) -> list[tuple[str, date, str]]:
    rows = session.execute(
        select(Body.name, Meeting.meeting_date, Meeting.title)
        .join(Meeting.body)
        .order_by(Meeting.meeting_date)
    )
    return [(b, d, t) for b, d, t in rows]


def test_september_2026_loads_classified_meetings_and_queues_the_rest(session: Session) -> None:
    report = _run(session)

    assert _meetings(session) == [
        ("Planning Commission", date(2026, 9, 15), "Planning Commission Meeting 091526"),
        ("Town Council", date(2026, 9, 28), "Town Council Work Session 092826"),
        (
            "Architectural Review Board",
            date(2026, 9, 30),
            "Architectural Review Board Meeting 9.30.2026",
        ),
    ]
    assert [r.video.title for r in report.needs_review] == ["Regular Meeting/Closed Session 091626"]
    assert report.accepted == 3


def test_rerunning_discovery_is_idempotent(session: Session) -> None:
    _run(session)
    first = _meetings(session)

    _run(session)

    assert _meetings(session) == first


def test_review_override_brings_queued_meeting_in(session: Session) -> None:
    config = SourceConfig.model_validate(
        {
            **CONFIG.model_dump(),
            "body_overrides": {"ha3Yl263mZA": {"body": "Town Council", "note": "test"}},
        }
    )

    report = _run(session, config)

    assert report.needs_review == []
    assert ("Town Council", date(2026, 9, 16), "Regular Meeting/Closed Session 091626") in (
        _meetings(session)
    )
