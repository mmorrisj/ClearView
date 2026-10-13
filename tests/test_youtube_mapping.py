from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from lt.db.models import MeetingStatus
from lt.discovery.sources import BodyOverride, SourceConfig
from lt.discovery.youtube.api import VideoInfo, parse_videos
from lt.discovery.youtube.classify import classify_body
from lt.discovery.youtube.mapping import Accepted, NeedsReview, Skipped, map_video
from tests.youtube_fakes import CHANNEL_ID, load

ET = ZoneInfo("America/New_York")


def _config(**overrides: object) -> SourceConfig:
    fields: dict[str, object] = {
        "jurisdiction_name": "Town of Haymarket",
        "state": "VA",
        "timezone": "America/New_York",
        "youtube_channel_id": CHANNEL_ID,
        "bodies": [
            "Town Council",
            "Planning Commission",
            "Architectural Review Board",
            "Board of Zoning Appeals",
        ],
    }
    fields.update(overrides)
    return SourceConfig.model_validate(fields)


def _video(**overrides: object) -> VideoInfo:
    fields: dict[str, object] = {
        "video_id": "abc123def45",
        "channel_id": CHANNEL_ID,
        "title": "Planning Commission Meeting 091526",
        "published_at": datetime(2026, 9, 15, 23, 1, tzinfo=UTC),
        "duration_s": 3776,
        "actual_start": datetime(2026, 9, 15, 23, 1, 55, tzinfo=UTC),
    }
    fields.update(overrides)
    return VideoInfo(**fields)  # type: ignore[arg-type]


# Real titles from the channel (fixtures/youtube/api/videos.json).
@pytest.mark.parametrize(
    ("title", "body"),
    [
        ("Planning Commission Meeting 091526", "Planning Commission"),
        ("Planning Commission  Meeting 060926", "Planning Commission"),
        ("Architectural Review Board Meeting 9.30.2026", "Architectural Review Board"),
        ("ARB Meeting 061726", "Architectural Review Board"),
        ("Town Council Work Session 092826", "Town Council"),
        ("Town Council Meeting -8/3/2026", "Town Council"),
        ("Town Council Public Hearing/Regular Meeting 050426", "Town Council"),
        ("Jun 17 2024 0700 PM Mayor and Council Special Meeting SD 480", "Town Council"),
        (
            "Mar 27 2024 0600 PM Board of Zoning Appeals Informational Meeting SD 480",
            "Board of Zoning Appeals",
        ),
        # No body named: a person must decide.
        ("Regular Meeting/Closed Session 091626", None),
        ("Public Hearing/Regular Monthly Meeting", None),
        ("Closed Session 082626", None),
        ("Monthly Work Session", None),
        ("Continuation Meeting 060226", None),
        # "arb" inside another word must not match.
        ("Harbor Committee Meeting", None),
    ],
)
def test_classify_body(title: str, body: str | None) -> None:
    assert classify_body(title) == body


def test_livestream_is_accepted_with_eastern_date_and_verbatim_title() -> None:
    result = map_video(_video(), _config())

    assert isinstance(result, Accepted)
    assert result.body_name == "Planning Commission"
    m = result.meeting
    assert m.external_id == "youtube:abc123def45"
    assert m.title == "Planning Commission Meeting 091526"
    assert m.meeting_date == date(2026, 9, 15)
    assert m.starts_at == datetime(2026, 9, 15, 19, 1, 55, tzinfo=ET)
    assert m.status is MeetingStatus.HELD
    assert m.media[0].url == "https://www.youtube.com/watch?v=abc123def45"
    assert m.media[0].duration_s == 3776


def test_meeting_date_uses_local_time_not_utc() -> None:
    # 00:30 UTC on Sep 16 is 8:30 PM Sep 15 in Virginia.
    result = map_video(_video(actual_start=datetime(2026, 9, 16, 0, 30, tzinfo=UTC)), _config())

    assert isinstance(result, Accepted)
    assert result.meeting.meeting_date == date(2026, 9, 15)


def test_zero_length_stream_is_skipped() -> None:
    result = map_video(_video(duration_s=0), _config())

    assert isinstance(result, Skipped)
    assert "zero-length" in result.reason


def test_title_without_body_needs_review() -> None:
    result = map_video(_video(title="Regular Meeting/Closed Session 091626"), _config())

    assert isinstance(result, NeedsReview)
    assert "body" in result.reason


def test_reviewed_override_assigns_body() -> None:
    config = _config(
        body_overrides={"abc123def45": BodyOverride(body="Town Council", note="checked agenda")}
    )

    result = map_video(_video(title="Regular Meeting/Closed Session 091626"), config)

    assert isinstance(result, Accepted)
    assert result.body_name == "Town Council"


def test_skip_list_wins() -> None:
    result = map_video(_video(), _config(skip={"abc123def45": "duplicate stream"}))

    assert isinstance(result, Skipped)
    assert result.reason == "duplicate stream"


def test_legacy_upload_takes_date_from_title_not_upload_date() -> None:
    video = _video(
        title="Jun 17 2024 0700 PM Planning Commission Regular Meeting SD 480",
        published_at=datetime(2024, 8, 2, 15, 0, tzinfo=UTC),  # uploaded weeks later
        actual_start=None,
    )

    result = map_video(video, _config())

    assert isinstance(result, Accepted)
    assert result.meeting.meeting_date == date(2024, 6, 17)
    assert result.meeting.starts_at == datetime(2024, 6, 17, 19, 0, tzinfo=ET)


def test_upload_without_stream_time_or_dated_title_needs_review() -> None:
    video = _video(title="Copy of Town Council regular meeting continued", actual_start=None)

    result = map_video(video, _config())

    assert isinstance(result, NeedsReview)
    assert "date" in result.reason


def test_override_body_must_be_a_known_body() -> None:
    with pytest.raises(ValueError, match="Parks Board"):
        _config(body_overrides={"x": {"body": "Parks Board", "note": ""}})


def test_every_real_video_in_fixture_gets_a_decision() -> None:
    results = [map_video(v, _config()) for v in parse_videos(load("videos.json"))]

    assert len(results) == 50
    assert all(isinstance(r, Accepted | Skipped | NeedsReview) for r in results)
    assert any(isinstance(r, Skipped) for r in results)  # the P0D streams
