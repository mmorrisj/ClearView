"""Per-jurisdiction source configuration, stored as reviewed JSON in ``config/sources/``.

Human review decisions (which body an ambiguous recording belongs to, which videos to
skip) live here, in version control, so every published record traces back to a
reviewed, attributable change.
"""

from pathlib import Path
from typing import Self
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, model_validator


class BodyOverride(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    body: str
    note: str


class SourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    jurisdiction_name: str
    state: str
    timezone: str
    youtube_channel_id: str
    bodies: list[str]
    body_overrides: dict[str, BodyOverride] = {}
    skip: dict[str, str] = {}

    @model_validator(mode="after")
    def _check(self) -> Self:
        ZoneInfo(self.timezone)  # raises for an unknown zone
        unknown = {o.body for o in self.body_overrides.values()} - set(self.bodies)
        if unknown:
            raise ValueError(f"body_overrides reference unknown bodies: {sorted(unknown)}")
        return self

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @classmethod
    def load(cls, path: Path) -> "SourceConfig":
        return cls.model_validate_json(path.read_text())
