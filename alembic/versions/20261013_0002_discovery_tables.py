"""Discovery tables: jurisdiction, body, meeting, document, media_asset.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jurisdiction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("fips_code", sa.String(length=10), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jurisdiction")),
        sa.UniqueConstraint("fips_code", name=op.f("uq_jurisdiction_fips_code")),
        sa.UniqueConstraint("state", "name", name=op.f("uq_jurisdiction_state_name")),
    )
    op.create_table(
        "body",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jurisdiction_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("source_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["jurisdiction_id"],
            ["jurisdiction.id"],
            name=op.f("fk_body_jurisdiction_id_jurisdiction"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_body")),
        sa.UniqueConstraint("jurisdiction_id", "name", name=op.f("uq_body_jurisdiction_id_name")),
    )
    op.create_table(
        "meeting",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("body_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("meeting_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "scheduled",
                "held",
                "cancelled",
                name="meetingstatus",
                native_enum=False,
                create_constraint=False,  # explicit CheckConstraint below
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('scheduled', 'held', 'cancelled')", name=op.f("ck_meeting_meetingstatus")
        ),
        sa.ForeignKeyConstraint(["body_id"], ["body.id"], name=op.f("fk_meeting_body_id_body")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meeting")),
        sa.UniqueConstraint("body_id", "external_id", name=op.f("uq_meeting_body_id_external_id")),
    )
    op.create_index(op.f("ix_meeting_body_id"), "meeting", ["body_id"], unique=False)
    op.create_index(op.f("ix_meeting_meeting_date"), "meeting", ["meeting_date"], unique=False)
    op.create_table(
        "document",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("meeting_id", sa.Integer(), nullable=False),
        sa.Column(
            "doc_type",
            sa.Enum(
                "agenda",
                "minutes",
                "packet",
                "other",
                name="documenttype",
                native_enum=False,
                create_constraint=False,  # explicit CheckConstraint below
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "doc_type IN ('agenda', 'minutes', 'packet', 'other')",
            name=op.f("ck_document_documenttype"),
        ),
        sa.ForeignKeyConstraint(
            ["meeting_id"],
            ["meeting.id"],
            name=op.f("fk_document_meeting_id_meeting"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document")),
        sa.UniqueConstraint("meeting_id", "url", name=op.f("uq_document_meeting_id_url")),
    )
    op.create_table(
        "media_asset",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("meeting_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("duration_s", sa.Double(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("local_path", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["meeting_id"],
            ["meeting.id"],
            name=op.f("fk_media_asset_meeting_id_meeting"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_asset")),
        sa.UniqueConstraint("meeting_id", "url", name=op.f("uq_media_asset_meeting_id_url")),
    )


def downgrade() -> None:
    op.drop_table("media_asset")
    op.drop_table("document")
    op.drop_index(op.f("ix_meeting_meeting_date"), table_name="meeting")
    op.drop_index(op.f("ix_meeting_body_id"), table_name="meeting")
    op.drop_table("meeting")
    op.drop_table("body")
    op.drop_table("jurisdiction")
