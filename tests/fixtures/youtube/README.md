Real, public data from the Town of Haymarket YouTube channel
(https://www.youtube.com/@TownofHaymarket, channel UCtqtz4Sjo9chgA38RttUbdw),
captured 2026-10-13. Tests never hit the network.

- `legacy_titles.json`: titles of 2021-2024 uploads, which use a fixed template.
- `api/`: unmodified YouTube Data API v3 responses (`channels.list`, the first and
  last pages of `playlistItems.list` for the uploads playlist, and `videos.list` for
  the first page's 50 videos). Responses contain no API key.
