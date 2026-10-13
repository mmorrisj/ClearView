from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lt.db.models import Body, Document, DocumentType, Jurisdiction, MediaAsset, Meeting
from lt.db.repositories import get_or_create_body, get_or_create_jurisdiction, upsert_meeting
from lt.discovery.types import DiscoveredDocument, DiscoveredMedia, DiscoveredMeeting

pytestmark = pytest.mark.db


def _body(session: Session) -> Body:
    jur = get_or_create_jurisdiction(session, name="Town of Haymarket", state="VA")
    return get_or_create_body(session, jurisdiction=jur, name="Town Council")


def _meeting(**overrides: object) -> DiscoveredMeeting:
    fields: dict[str, object] = {
        "external_id": "11445",
        "title": "Regular Meeting",
        "meeting_date": date(2026, 9, 8),
        "source_url": "https://example.test/meetings/11445",
        "documents": [
            DiscoveredDocument(DocumentType.AGENDA, "https://example.test/a.pdf"),
            DiscoveredDocument(DocumentType.MINUTES, "https://example.test/m.pdf"),
        ],
        "media": [DiscoveredMedia("https://example.test/video/11445")],
    }
    fields.update(overrides)
    return DiscoveredMeeting(**fields)  # type: ignore[arg-type]


def _count(session: Session, model: type[object]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_get_or_create_is_idempotent(session: Session) -> None:
    first = _body(session)
    second = _body(session)

    assert first.id == second.id
    assert _count(session, Jurisdiction) == 1
    assert _count(session, Body) == 1


def test_upsert_meeting_creates_meeting_documents_and_media(session: Session) -> None:
    body = _body(session)

    meeting = upsert_meeting(session, body=body, discovered=_meeting())

    assert meeting.meeting_date == date(2026, 9, 8)
    assert {d.doc_type for d in meeting.documents} == {DocumentType.AGENDA, DocumentType.MINUTES}
    assert [m.url for m in meeting.media_assets] == ["https://example.test/video/11445"]


def test_upsert_meeting_twice_does_not_duplicate(session: Session) -> None:
    body = _body(session)

    upsert_meeting(session, body=body, discovered=_meeting())
    upsert_meeting(session, body=body, discovered=_meeting())

    assert _count(session, Meeting) == 1
    assert _count(session, Document) == 2
    assert _count(session, MediaAsset) == 1


def test_upsert_meeting_updates_changed_fields_and_adds_new_documents(session: Session) -> None:
    body = _body(session)
    upsert_meeting(session, body=body, discovered=_meeting(documents=[]))

    meeting = upsert_meeting(
        session,
        body=body,
        discovered=_meeting(
            title="Regular Meeting (Rescheduled)",
            documents=[DiscoveredDocument(DocumentType.AGENDA, "https://example.test/a.pdf")],
        ),
    )

    assert meeting.title == "Regular Meeting (Rescheduled)"
    assert [d.url for d in meeting.documents] == ["https://example.test/a.pdf"]
    assert _count(session, Meeting) == 1


def test_upsert_never_deletes_documents_missing_from_a_later_scrape(session: Session) -> None:
    """A source page dropping a link must not erase what we already recorded."""
    body = _body(session)
    upsert_meeting(session, body=body, discovered=_meeting())

    upsert_meeting(session, body=body, discovered=_meeting(documents=[], media=[]))

    assert _count(session, Document) == 2
    assert _count(session, MediaAsset) == 1
