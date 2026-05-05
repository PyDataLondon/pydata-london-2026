"""Build recommender.md and qr.svg from the live pretalx schedule.

Run:  python scripts/build_recommender.py
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import qrcode
import qrcode.image.svg
import requests
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parent.parent
SCHEDULE_URL = "https://pretalx.com/pydata-london-2026/schedule/export/schedule.json"
# When the short domain `pydata.london` is registered, swap both URLs below to:
#   RECOMMENDER_URL = "https://pydata.london/recommender.md"
#   LANDING_URL = "https://pydata.london/"
# and update the same two strings in `index.html`.
RECOMMENDER_URL = "https://london.pydata.org/pydata-london-2026/recommender.md"
LANDING_URL = "https://london.pydata.org/pydata-london-2026/"
MIN_SESSIONS = 30  # below this, something is wrong — fail loudly

ABSTRACT_MAX = 600
BIO_MAX = 220
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def trim(text: str | None, limit: int) -> str:
    if not text:
        return ""
    text = " ".join(text.split())  # collapse whitespace, drop \r\n
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def normalise_session(raw: dict) -> dict:
    speakers = [p["public_name"] or p["name"] for p in raw.get("persons", [])]
    bios = [
        f"{p['public_name'] or p['name']} — {trim(p.get('biography'), BIO_MAX)}"
        for p in raw.get("persons", [])
        if p.get("biography")
    ]
    return {
        "title": raw["title"].strip(),
        "speakers": ", ".join(speakers) if speakers else "TBA",
        "speaker_bios": " · ".join(bios),
        "start_time": raw["start"],
        "duration": raw["duration"],
        "room": raw["room"],
        "type": raw["type"],
        "track": raw.get("track"),
        "url": raw["url"],
        "abstract": trim(raw.get("abstract"), ABSTRACT_MAX),
        "is_tutorial": raw["type"].lower() == "tutorial",
    }


def fetch_schedule() -> dict:
    print(f"Fetching {SCHEDULE_URL} …")
    resp = requests.get(SCHEDULE_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def build_context(payload: dict) -> dict:
    conf = payload["schedule"]["conference"]

    days = []
    total_sessions = 0
    talk_count = 0
    tutorial_count = 0
    keynote_names: list[str] = []

    for day in conf["days"]:
        date = dt.date.fromisoformat(day["date"])
        sessions: list[dict] = []
        for room_sessions in day["rooms"].values():
            for raw in room_sessions:
                sessions.append(normalise_session(raw))
        sessions.sort(key=lambda s: (s["start_time"], s["room"]))
        for s in sessions:
            total_sessions += 1
            if s["is_tutorial"]:
                tutorial_count += 1
            else:
                talk_count += 1
            if "keynote" in s["title"].lower():
                keynote_names.extend(n.strip() for n in s["speakers"].split(","))

        days.append(
            {
                "date": day["date"],
                "date_pretty": date.strftime("%-d %B %Y"),
                "weekday": WEEKDAYS[date.weekday()],
                "sessions": sessions,
            }
        )

    if total_sessions < MIN_SESSIONS:
        raise RuntimeError(
            f"Only {total_sessions} sessions parsed (expected ≥ {MIN_SESSIONS}). "
            "Refusing to overwrite recommender.md with what looks like a bad fetch."
        )

    # Dedupe keynote names while preserving order
    seen: set[str] = set()
    unique_keynotes = []
    for name in keynote_names:
        if name and name not in seen:
            seen.add(name)
            unique_keynotes.append(name)

    if not unique_keynotes:
        keynote_phrase = "world-class speakers"
    elif len(unique_keynotes) == 1:
        keynote_phrase = unique_keynotes[0]
    else:
        keynote_phrase = ", ".join(unique_keynotes[:-1]) + " and " + unique_keynotes[-1]

    return {
        "days": days,
        "session_count": total_sessions,
        "talk_count": talk_count,
        "tutorial_count": tutorial_count,
        "keynote_names": keynote_phrase,
        "schedule_version": payload["schedule"]["version"],
        "source_url": SCHEDULE_URL,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def render_recommender(context: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        undefined=StrictUndefined,
        trim_blocks=False,
        lstrip_blocks=False,
        keep_trailing_newline=True,
    )
    template = env.get_template("recommender.md.j2")
    return template.render(**context)


def write_qr(target: Path, payload_url: str) -> None:
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(payload_url, image_factory=factory, box_size=10, border=2)
    img.save(target)


def main() -> int:
    payload = fetch_schedule()
    (ROOT / "schedule.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    context = build_context(payload)
    rendered = render_recommender(context)
    (ROOT / "recommender.md").write_text(rendered)

    write_qr(ROOT / "qr.svg", LANDING_URL)

    print(
        f"Wrote recommender.md ({len(rendered):,} chars) "
        f"with {context['session_count']} sessions across {len(context['days'])} days."
    )
    print(f"Wrote qr.svg pointing at {LANDING_URL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
