"""
Canvas assignment poller.

Runs on a schedule (via GitHub Actions). Checks all your active Canvas
courses for assignments, compares against previously-seen state, and
posts a push notification (via ntfy.sh) whenever:
  - a brand new assignment appears
  - an assignment's due date changes
  - an assignment is newly within a reminder threshold (48h / 24h / 3h)

State is kept in state.json (committed back to the repo by the workflow)
so the poller remembers what it already told you about.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

CANVAS_URL = os.environ["CANVAS_URL"].rstrip("/")
CANVAS_TOKEN = os.environ["CANVAS_TOKEN"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]

STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"

# Hours-before-due thresholds to send a reminder at.
REMINDER_THRESHOLDS_HOURS = [48, 24, 3]

# How many days after the due date to stop tracking an assignment (keeps
# state.json from growing forever).
PRUNE_AFTER_DAYS = 14

HEADERS = {"Authorization": f"Bearer {CANVAS_TOKEN}"}


def canvas_get_all(path, params=None):
    """GET a Canvas API endpoint, following pagination."""
    url = f"{CANVAS_URL}{path}"
    params = dict(params or {})
    params.setdefault("per_page", 100)
    results = []
    while url:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        results.extend(resp.json())
        # Canvas pagination is via the Link header; params only apply to the
        # first request, subsequent ones are full URLs from the Link header.
        params = None
        url = None
        for link in resp.links.values():
            if link.get("rel") == "next":
                url = link["url"]
    return results


def fetch_assignments():
    courses = canvas_get_all("/api/v1/courses", {"enrollment_state": "active"})
    assignments = []
    for course in courses:
        course_id = course.get("id")
        course_name = course.get("name") or course.get("course_code") or f"Course {course_id}"
        try:
            course_assignments = canvas_get_all(
                f"/api/v1/courses/{course_id}/assignments",
                {"order_by": "due_at"},
            )
        except requests.HTTPError as e:
            print(f"  (skipping course {course_name}: {e})", file=sys.stderr)
            continue
        for a in course_assignments:
            assignments.append(
                {
                    "id": str(a["id"]),
                    "name": a.get("name", "Untitled assignment"),
                    "course": course_name,
                    "due_at": a.get("due_at"),  # ISO8601 string or None
                    "html_url": a.get("html_url"),
                }
            )
    return assignments


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
    due = datetime.fromisoformat(due_at_iso.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    return (due - now).total_seconds() / 3600.0


def main():
    assignments = fetch_assignments()
    state = load_state()
    now = datetime.now(timezone.utc)
    changed = False

    seen_ids = set()

    for a in assignments:
        aid = a["id"]
        seen_ids.add(aid)
        entry = state.get(aid)

        if entry is None:
            # Brand new assignment.
            if a["due_at"]:
                due_local = a["due_at"]
                msg = f"{a['course']}\n\"{a['name']}\"\nDue: {due_local}"
            else:
                msg = f"{a['course']}\n\"{a['name']}\"\n(no due date set yet)"
            send_notification("📚 New Canvas assignment", msg, priority="default", tags=["memo"])
            state[aid] = {
                "name": a["name"],
                "course": a["course"],
                "due_at": a["due_at"],
                "notified_thresholds": [],
            }
            changed = True
            continue

        # Due date changed (set for the first time, or moved).
        if a["due_at"] != entry.get("due_at"):
            if a["due_at"]:
                msg = f"{a['course']}\n\"{a['name']}\"\nNew due date: {a['due_at']}"
                send_notification("📅 Canvas due date changed", msg, priority="default", tags=["calendar"])
            entry["due_at"] = a["due_at"]
            entry["notified_thresholds"] = []
            changed = True

        # Approaching-deadline reminders.
        if entry.get("due_at"):
            try:
                hrs = hours_until(entry["due_at"])
            except ValueError:
                hrs = None
            if hrs is not None and hrs > 0:
                already = set(entry.get("notified_thresholds", []))
                for threshold in REMINDER_THRESHOLDS_HOURS:
                    if hrs <= threshold and threshold not in already:
                        msg = f"{a['course']}\n\"{a['name']}\"\nDue in about {threshold}h ({entry['due_at']})"
                        send_notification(
                            f"⏰ Assignment due in {threshold}h",
                            msg,
                            priority="high" if threshold <= 24 else "default",
                            tags=["warning"],
                        )
                        already.add(threshold)
                        entry["notified_thresholds"] = sorted(already)
                        changed = True

    # Prune old entries so state.json doesn't grow forever.
    for aid in list(state.keys()):
        entry = state[aid]
        due_at = entry.get("due_at")
        stale = aid not in seen_ids
        old = False
        if due_at:
            try:
                old = hours_until(due_at) < -PRUNE_AFTER_DAYS * 24
            except ValueError:
                old = False
        if stale or old:
            del state[aid]
            changed = True

    if changed:
        save_state(state)
        print(f"State updated ({len(state)} tracked assignments).")
    else:
        print("No changes.")


if __name__ == "__main__":
    main()
