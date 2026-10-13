"""Command-line entry point: ``lt discover youtube --source ... --month YYYY-MM``."""

import argparse
import calendar
import logging
import sys
from datetime import date
from pathlib import Path

from lt.config import get_settings
from lt.db.session import get_sessionmaker
from lt.discovery.run import discover_youtube
from lt.discovery.sources import SourceConfig
from lt.discovery.youtube.api import YouTubeClient


def _month(value: str) -> tuple[date, date]:
    try:
        year, month = (int(p) for p in value.split("-"))
        return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM, got {value!r}") from exc


def _discover_youtube(args: argparse.Namespace) -> int:
    settings = get_settings()
    if settings.youtube_api_key is None:
        print("YOUTUBE_API_KEY is not set", file=sys.stderr)
        return 2
    config = SourceConfig.load(args.source)
    start, end = args.month
    client = YouTubeClient(settings.youtube_api_key.get_secret_value())
    try:
        with get_sessionmaker()() as session:
            report = discover_youtube(session, client, config, start=start, end=end)
    finally:
        client.close()

    print(f"{config.jurisdiction_name} {start:%Y-%m}: {report.accepted} meetings upserted")
    for s in report.skipped:
        print(f"  skipped       {s.video.url}  {s.video.title!r}: {s.reason}")
    for r in report.needs_review:
        print(f"  NEEDS REVIEW  {r.video.url}  {r.video.title!r}: {r.reason}")
    if report.needs_review:
        print(f"Resolve review items via body_overrides or skip in {args.source}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lt")
    sub = parser.add_subparsers(dest="command", required=True)
    discover = sub.add_parser("discover", help="discover meetings from a source")
    dsub = discover.add_subparsers(dest="source_type", required=True)
    yt = dsub.add_parser("youtube", help="discover recorded meetings on a YouTube channel")
    yt.add_argument("--source", type=Path, required=True, help="config/sources/<name>.json")
    yt.add_argument("--month", type=_month, required=True, help="YYYY-MM")
    yt.set_defaults(func=_discover_youtube)

    args = parser.parse_args(argv)
    logging.basicConfig(level=get_settings().log_level, format="%(levelname)s %(name)s %(message)s")
    # One line per HTTP request is noise; our own loggers report progress.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    code: int = args.func(args)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
