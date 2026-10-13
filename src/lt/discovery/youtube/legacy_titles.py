"""Parse Haymarket's YouTube recording titles into meetings.

Titles follow the town's recording-system template, e.g.::

    Jun 17 2024 0700 PM Planning Commission Regular Meeting SD 480

The trailing ``SD 480`` is the video resolution. Titles that don't match (e.g. a manual
upload named "Copy of Town Council regular meeting continued") return ``None`` so they
can be triaged by a person instead of guessed at.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, time

from lt.db.models import MeetingStatus
from lt.discovery.types import DiscoveredMedia, DiscoveredMeeting

# Title prefix -> canonical Body.name. Longest prefixes first so matching is unambiguous.
BODY_ALIASES: dict[str, str] = {
    "Architectural Review Board": "Architectural Review Board",
    "Board of Zoning Appeals": "Board of Zoning Appeals",
    "Planning Commission": "Planning Commission",
    "Mayor and Council": "Town Council",
    "Town Council": "Town Council",
}

_TITLE_RE = re.compile(
    r"^(?P<mon>[A-Z][a-z]{2}) (?P<day>\d{1,2}) (?P<year>\d{4}) "
    r"(?P<hhmm>\d{4}) (?P<ampm>AM|PM) (?P<rest>.+?)(?: (?:SD|HD) \d{3,4})?$"
)


@dataclass(frozen=True, slots=True)
class ParsedTitle:
    body_name: str
    meeting_type: str
    meeting_date: date
    start_time: time


def parse_title(title: str) -> ParsedTitle | None:
    m = _TITLE_RE.match(title.strip())
    if not m:
        return None
    try:
        when = datetime.strptime(
            f"{m['mon']} {m['day']} {m['year']} {m['hhmm']} {m['ampm']}", "%b %d %Y %I%M %p"
        )
    except ValueError:
        return None

    rest = m["rest"]
    for prefix in sorted(BODY_ALIASES, key=len, reverse=True):
        if rest.startswith(prefix + " "):
            return ParsedTitle(
                body_name=BODY_ALIASES[prefix],
                meeting_type=rest[len(prefix) + 1 :].strip(),
                meeting_date=when.date(),
                start_time=when.time(),
            )
    return None


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def meeting_from_video(video_id: str, title: str) -> tuple[str, DiscoveredMeeting] | None:
    """Return ``(body_name, meeting)`` for a recording, or ``None`` if the title is unparseable.

    The external id is derived from the meeting (date, start time, type), not the video, so a
    re-upload or a second part of the same meeting maps to the same row.
    """
    parsed = parse_title(title)
    if parsed is None:
        return None
    url = f"https://www.youtube.com/watch?v={video_id}"
    external_id = (
        f"{parsed.meeting_date.isoformat()}T{parsed.start_time:%H%M}-{_slug(parsed.meeting_type)}"
    )
    meeting = DiscoveredMeeting(
        external_id=external_id,
        title=f"{parsed.body_name} {parsed.meeting_type}",
        meeting_date=parsed.meeting_date,
        source_url=url,
        status=MeetingStatus.HELD,
        media=[DiscoveredMedia(url)],
    )
    return parsed.body_name, meeting
