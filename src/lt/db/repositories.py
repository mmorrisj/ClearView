"""Idempotent persistence for discovery output."""

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from lt.db.models import Body, Document, Jurisdiction, MediaAsset, Meeting
from lt.discovery.types import DiscoveredMeeting


def get_or_create_jurisdiction(
    session: Session, *, name: str, state: str, fips_code: str | None = None
) -> Jurisdiction:
    session.execute(
        insert(Jurisdiction)
        .values(name=name, state=state, fips_code=fips_code)
        .on_conflict_do_nothing(index_elements=["state", "name"])
    )
    return session.execute(
        select(Jurisdiction).where(Jurisdiction.state == state, Jurisdiction.name == name)
    ).scalar_one()


def get_or_create_body(
    session: Session, *, jurisdiction: Jurisdiction, name: str, source_urls: list[str] | None = None
) -> Body:
    session.execute(
        insert(Body)
        .values(jurisdiction_id=jurisdiction.id, name=name, source_urls=source_urls or [])
        .on_conflict_do_nothing(index_elements=["jurisdiction_id", "name"])
    )
    return session.execute(
        select(Body).where(Body.jurisdiction_id == jurisdiction.id, Body.name == name)
    ).scalar_one()


def upsert_meeting(session: Session, *, body: Body, discovered: DiscoveredMeeting) -> Meeting:
    """Insert or update a meeting and add any newly seen documents/media.

    Additive by design: links that disappear from the source are kept, because a public
    record we already captured should not vanish when a website is reorganized.
    """
    values = {
        "title": discovered.title,
        "meeting_date": discovered.meeting_date,
        "starts_at": discovered.starts_at,
        "status": discovered.status,
        "source_url": discovered.source_url,
    }
    stmt = insert(Meeting).values(body_id=body.id, external_id=discovered.external_id, **values)
    meeting_id = session.execute(
        stmt.on_conflict_do_update(
            index_elements=["body_id", "external_id"],
            set_={**values, "updated_at": func.now()},
        ).returning(Meeting.id)
    ).scalar_one()

    if discovered.documents:
        session.execute(
            insert(Document)
            .values(
                [
                    {
                        "meeting_id": meeting_id,
                        "doc_type": d.doc_type,
                        "url": d.url,
                        "title": d.title,
                    }
                    for d in discovered.documents
                ]
            )
            .on_conflict_do_nothing(index_elements=["meeting_id", "url"])
        )
    if discovered.media:
        media_stmt = insert(MediaAsset).values(
            [
                {"meeting_id": meeting_id, "url": m.url, "duration_s": m.duration_s}
                for m in discovered.media
            ]
        )
        session.execute(
            media_stmt.on_conflict_do_update(
                index_elements=["meeting_id", "url"],
                # Never overwrite a known duration with an unknown one.
                set_={
                    "duration_s": func.coalesce(
                        media_stmt.excluded.duration_s, MediaAsset.duration_s
                    )
                },
            )
        )

    meeting = session.get_one(Meeting, meeting_id, populate_existing=True)
    session.refresh(meeting, ["documents", "media_assets"])
    return meeting
