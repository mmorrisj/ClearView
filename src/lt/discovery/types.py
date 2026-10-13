"""Source-agnostic records that every scraper emits.

Scrapers only parse; persistence happens in ``lt.db.repositories``. That split keeps
scrapers testable against saved HTML fixtures with no database.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol

from lt.db.models import DocumentType, MeetingStatus


@dataclass(frozen=True, slots=True)
class DiscoveredDocument:
    doc_type: DocumentType
    url: str
    title: str | None = None


@dataclass(frozen=True, slots=True)
class DiscoveredMedia:
    url: str
    duration_s: float | None = None


@dataclass(frozen=True, slots=True)
class DiscoveredMeeting:
    external_id: str
    title: str
    meeting_date: date
    source_url: str
    starts_at: datetime | None = None
    status: MeetingStatus = MeetingStatus.SCHEDULED
    documents: list[DiscoveredDocument] = field(default_factory=list)
    media: list[DiscoveredMedia] = field(default_factory=list)


class MeetingListParser(Protocol):
    """Parses one fetched listing page into meetings. Must be pure: no network, no DB."""

    def parse(self, html: str, *, page_url: str) -> list[DiscoveredMeeting]: ...
