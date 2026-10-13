"""Decide, per video, whether it is a meeting we can record, a skip, or a human-review item."""

from dataclasses import dataclass
from datetime import datetime

from lt.db.models import MeetingStatus
from lt.discovery.sources import SourceConfig
from lt.discovery.types import DiscoveredMedia, DiscoveredMeeting
from lt.discovery.youtube.api import VideoInfo
from lt.discovery.youtube.classify import classify_body
from lt.discovery.youtube.legacy_titles import parse_title


@dataclass(frozen=True, slots=True)
class Accepted:
    body_name: str
    meeting: DiscoveredMeeting


@dataclass(frozen=True, slots=True)
class Skipped:
    video: VideoInfo
    reason: str


@dataclass(frozen=True, slots=True)
class NeedsReview:
    video: VideoInfo
    reason: str


Decision = Accepted | Skipped | NeedsReview


def map_video(video: VideoInfo, config: SourceConfig) -> Decision:
    if video.video_id in config.skip:
        return Skipped(video, config.skip[video.video_id])
    if video.duration_s == 0:
        return Skipped(video, "zero-length stream (scheduled but nothing recorded)")

    legacy = parse_title(video.title)

    # Meeting time: the livestream's actual start is authoritative. For old uploads the
    # templated title carries the meeting time; the upload date would be wrong.
    starts_at: datetime | None = None
    if video.actual_start is not None:
        starts_at = video.actual_start.astimezone(config.tz)
    elif legacy is not None:
        starts_at = datetime.combine(legacy.meeting_date, legacy.start_time, tzinfo=config.tz)
    if starts_at is None:
        return NeedsReview(video, "no reliable meeting date (not a livestream, undated title)")

    override = config.body_overrides.get(video.video_id)
    body = override.body if override else classify_body(video.title)
    if body is None:
        return NeedsReview(video, "title does not name a body")

    meeting = DiscoveredMeeting(
        # The video id is stable even when staff edit the title later.
        external_id=f"youtube:{video.video_id}",
        title=video.title,
        meeting_date=starts_at.date(),
        starts_at=starts_at,
        source_url=video.url,
        status=MeetingStatus.HELD,
        media=[DiscoveredMedia(video.url, duration_s=float(video.duration_s))],
    )
    return Accepted(body, meeting)
