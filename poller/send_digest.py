"""
Periodic "what's coming up" digest — runs every 2 hours (digest.yml),
separate from the more frequent new/due-soon poller (poll.yml).

Only sends a notification if something is actually upcoming — stays
completely silent otherwise, so the pet doesn't pop up for no reason.
"""

from datetime import datetime, timezone

import canvas_poller as cp

# Only include items due within this many days in the digest.
DIGEST_WINDOW_DAYS = 14
MAX_ITEMS_SHOWN = 8


def main():
    events = cp.fetch_events()
    now = datetime.now(timezone.utc)
    cutoff_hours = DIGEST_WINDOW_DAYS * 24

    upcoming = []
    for e in events:
        if not e["due_at"]:
            continue
        due = datetime.fromisoformat(e["due_at"])
        hrs = (due - now).total_seconds() / 3600.0
        if 0 < hrs <= cutoff_hours:
            upcoming.append((due, e))

    if not upcoming:
        print("Nothing upcoming — staying quiet.")
        return

    upcoming.sort(key=lambda pair: pair[0])

    lines = []
    for due, e in upcoming[:MAX_ITEMS_SHOWN]:
        lines.append(f"• {e['course']}: {e['name']} — {due.strftime('%a %b %d, %I:%M %p UTC')}")
    remaining = len(upcoming) - MAX_ITEMS_SHOWN
    if remaining > 0:
        lines.append(f"...and {remaining} more")

    cp.send_notification("🗓️ Upcoming due dates", "\n".join(lines), tags=["calendar"])
    print(f"Sent digest with {len(upcoming)} upcoming item(s).")


if __name__ == "__main__":
    main()
