"""
Canvas assignment poller — reads your private Canvas calendar feed (.ics).

No API token needed: the calendar feed is a separate Canvas feature (meant
for subscribing Canvas to Google/Apple Calendar) that most schools don't
lock down even when personal access tokens are restricted.

Runs on a schedule (via GitHub Actions). Compares the feed against
previously-seen state, and posts a push notification (via ntfy.sh)
whenever:
  - a brand new assignment/event with a due date appears
  - an assignment's due date changes
  - an assignment is newly within a reminder threshold (48h / 24h / 3h)

State is kept in state.json (committed back to the repo by the workflow)
so the poller remembers what it already told you about.
"""

import json
import os
import re
import sys
from datetime import date, datetime, time, timezone
from pathlib import Path

import requests
from icalendar import Calendar

CANVAS_ICS_URL = os.environ["CANVAS_ICS_URL"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]

STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"

# Hours-before-due thresholds to send a reminder at.
REMINDER_THRESHOLDS_HOURS = [48, 24, 3]

# How many days after the due date to stop tracking an item (keeps
# state.json from growing forever).
PRUNE_AFTER_DAYS = 14

COURSE_TAG_RE = re.compile(r"\[(.+?)\]\s*$")


def to_utc_iso(dt_value):
    """Normalize an icalendar dtstart value (date or datetime) to an
    aware UTC ISO8601 string."""
    if dt_value is None:
        return None
    if isinstance(dt_value, datetime):
        dt = dt_value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    if isinstance(dt_value, date):
        # All-day event with no time component; treat as end-of-day UTC.
        dt = datetime.combine(dt_value, time(23, 59), tzinfo=timezone.utc)
        return dt.isoformat()
    return None


def fetch_events():
    resp = requests.get(CANVAS_ICS_URL, timeout=30)
    resp.raise_for_status()
    cal = Calendar.from_ical(resp.text)

    events = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        uid = str(component.get("uid"))
        summary = str(component.get("summary") or "Untitled item")
        dtstart = component.get("dtstart")
        due_at = to_utc_iso(dtstart.dt) if dtstart else None
        url = str(component.get("url") or "")

        course_match = COURSE_TAG_RE.search(summary)
        course = course_match.group(1) if course_match else "Canvas"
        name = COURSE_TAG_RE.sub("", summary).strip()

        events.append(
            {
                "id": uid,
                "name": name,
                "course": course,
                "due_at": due_at,
                "url": url,
            }
        )
    return events


def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {}


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True))


def send_notification(title, message, priority="default", tags=None):
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": priority,
            **({"Tags": ",".join(tags)} if tags else {}),
        },
        timeout=15,
    )


def hours_until(due_at_iso):
    due = datetime.fromisoformat(due_at_iso)
    now = datetime.now(timezone.utc)
    return (due - now).total_seconds() / 3600.0


def main():
    events = fetch_events()
    state = load_state()
    changed = False
    seen_ids = set()

    for e in events:
        eid = e["id"]
        seen_ids.add(eid)
        entry = state.get(eid)

        if entry is None:
            # Brand new item.
            if e["due_at"]:
                msg = f"{e['course']}\n\"{e['name']}\"\nDue: {e['due_at']}"
            else:
                msg = f"{e['course']}\n\"{e['name']}\""
            send_notification("📚 New Canvas item", msg, priority="default", tags=["memo"])
            state[eid] = {
                "name": e["name"],
                "course": e["course"],
                "due_at": e["due_at"],
                "notified_thresholds": [],
            }
            changed = True
            continue

        # Due date changed (set for the first time, or moved).
        if e["due_at"] != entry.get("due_at"):
            if e["due_at"]:
                msg = f"{e['course']}\n\"{e['name']}\"\nNew due date: {e['due_at']}"
                send_notification("📅 Canvas due date changed", msg, priority="default", tags=["calendar"])
            entry["due_at"] = e["due_at"]
            entry["notified_thresholds"] = []
            changed = True

        # Approaching-deadline reminders.
        if entry.get("due_at"):
            hrs = hours_until(entry["due_at"])
            if hrs > 0:
                already = set(entry.get("notified_thresholds", []))
                for threshold in REMINDER_THRESHOLDS_HOURS:
                    if hrs <= threshold and threshold not in already:
                        msg = f"{e['course']}\n\"{e['name']}\"\nDue in about {threshold}h ({entry['due_at']})"
                        send_notification(
                            f"⏰ Assignment due in {threshold}h",
                            msg,
                            priority="high" if threshold <= 24 else "default",
                            tags=["warning"],
                        )
                        already.add(threshold)
                        entry["notified_thresholds"] = sorted(already)
                        changed = True

    # Prune old / no-longer-listed entries so state.json doesn't grow forever.
    for eid in list(state.keys()):
        entry = state[eid]
        due_at = entry.get("due_at")
        stale = eid not in seen_ids
        old = due_at is not None and hours_until(due_at) < -PRUNE_AFTER_DAYS * 24
        if stale or old:
            del state[eid]
            changed = True

    if changed:
        save_state(state)
        print(f"State updated ({len(state)} tracked items).")
    else:
        print("No changes.")


if __name__ == "__main__":
    main()
