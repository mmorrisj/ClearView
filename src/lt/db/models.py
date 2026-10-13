"""ORM models for the discovery stage (brief §7). Later stages add their own tables."""

import enum
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lt.db.base import Base


class DocumentType(enum.StrEnum):
    AGENDA = "agenda"
    MINUTES = "minutes"
    PACKET = "packet"
    OTHER = "other"


class MeetingStatus(enum.StrEnum):
    SCHEDULED = "scheduled"
    HELD = "held"
    CANCELLED = "cancelled"


def _str_enum(cls: type[enum.StrEnum]) -> Enum:
    # Stored as VARCHAR + CHECK (not a native PG enum) so adding values is a simple migration.
    return Enum(
        cls,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Jurisdiction(TimestampMixin, Base):
    __tablename__ = "jurisdiction"
    __table_args__ = (UniqueConstraint("state", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    state: Mapped[str] = mapped_column(String(2))
    fips_code: Mapped[str | None] = mapped_column(String(10), unique=True)

    bodies: Mapped[list["Body"]] = relationship(back_populates="jurisdiction")


class Body(TimestampMixin, Base):
    __tablename__ = "body"
    __table_args__ = (UniqueConstraint("jurisdiction_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    jurisdiction_id: Mapped[int] = mapped_column(ForeignKey("jurisdiction.id"))
    name: Mapped[str] = mapped_column(String(200))
    source_urls: Mapped[list[str]] = mapped_column(JSONB, default=list)

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="bodies")
    meetings: Mapped[list["Meeting"]] = relationship(back_populates="body")


class Meeting(TimestampMixin, Base):
    __tablename__ = "meeting"
    # external_id is the source system's stable identifier; it is the idempotency key.
    __table_args__ = (UniqueConstraint("body_id", "external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    body_id: Mapped[int] = mapped_column(ForeignKey("body.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(500))
    meeting_date: Mapped[date] = mapped_column(Date, index=True)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[MeetingStatus] = mapped_column(
        _str_enum(MeetingStatus), default=MeetingStatus.SCHEDULED
    )
    source_url: Mapped[str] = mapped_column(Text)

    body: Mapped[Body] = relationship(back_populates="meetings")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="meeting", order_by="Document.id"
    )
    media_assets: Mapped[list["MediaAsset"]] = relationship(
        back_populates="meeting", order_by="MediaAsset.id"
    )


class Document(TimestampMixin, Base):
    __tablename__ = "document"
    __table_args__ = (UniqueConstraint("meeting_id", "url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meeting.id", ondelete="CASCADE"))
    doc_type: Mapped[DocumentType] = mapped_column(_str_enum(DocumentType))
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(String(500))
    # Populated by the fetch stage (M2).
    sha256: Mapped[str | None] = mapped_column(String(64))
    extracted_text: Mapped[str | None] = mapped_column(Text)

    meeting: Mapped[Meeting] = relationship(back_populates="documents")


class MediaAsset(TimestampMixin, Base):
    __tablename__ = "media_asset"
    __table_args__ = (UniqueConstraint("meeting_id", "url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meeting.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(Text)
    # Populated by the fetch stage (M2).
    duration_s: Mapped[float | None]
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64))
    local_path: Mapped[str | None] = mapped_column(Text)

    meeting: Mapped[Meeting] = relationship(back_populates="media_assets")
