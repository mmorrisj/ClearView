"""Run YouTube discovery for one jurisdiction over a date range."""

import logging
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from lt.db.repositories import get_or_create_body, get_or_create_jurisdiction, upsert_meeting
from lt.discovery.sources import SourceConfig
from lt.discovery.youtube.api import VideoInfo, YouTubeClient
from lt.discovery.youtube.mapping import Accepted, NeedsReview, Skipped, map_video

log = logging.getLogger(__name__)


@dataclass
class DiscoveryReport:
    accepted: int = 0
    skipped: list[Skipped] = field(default_factory=list)
    needs_review: list[NeedsReview] = field(default_factory=list)


def _approx_local_date(video: VideoInfo, config: SourceConfig) -> date:
    when = video.actual_start or video.published_at
    return when.astimezone(config.tz).date()


def discover_youtube(
    session: Session,
    client: YouTubeClient,
    config: SourceConfig,
    *,
    start: date,
    end: date,
) -> DiscoveryReport:
    """Upsert meetings dated within ``[start, end]`` and report what needs a person.

    Lists the full uploads playlist (about 30 quota units for ~740 videos) rather than
    stopping early, because old meetings are sometimes uploaded long after they happen.
    """
    jurisdiction = get_or_create_jurisdiction(
        session, name=config.jurisdiction_name, state=config.state
    )
    bodies = {
        name: get_or_create_body(session, jurisdiction=jurisdiction, name=name)
        for name in config.bodies
    }

    playlist = client.uploads_playlist_id(config.youtube_channel_id)
    videos = list(client.get_videos(client.list_upload_ids(playlist)))
    log.info("listed %d videos from %s", len(videos), config.youtube_channel_id)

    report = DiscoveryReport()
    for video in videos:
        decision = map_video(video, config)
        if isinstance(decision, Accepted):
            if start <= decision.meeting.meeting_date <= end:
                body = bodies[decision.body_name]
                upsert_meeting(session, body=body, discovered=decision.meeting)
                report.accepted += 1
        elif start <= _approx_local_date(video, config) <= end:
            if isinstance(decision, Skipped):
                report.skipped.append(decision)
            else:
                report.needs_review.append(decision)
    session.commit()
    return report
