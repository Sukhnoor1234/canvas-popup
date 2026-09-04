# CanvasPet

A pixel-art desktop pet that watches your Canvas courses and pops up with a
speech bubble whenever a new assignment is posted or a due date is coming up.

**How it works:** a small script runs every 15 minutes for free on GitHub's
servers, checks your Canvas calendar feed for new/upcoming assignments, and
pushes a notification through [ntfy.sh](https://ntfy.sh) (free, no account
needed). The pet on your PC listens for those notifications and reacts to
them live. The cloud side keeps working even when your PC is off; the pet
just needs your PC on to actually show anything.

**No Canvas API token required.** This uses Canvas's private calendar feed
(the same feature that lets you subscribe Canvas to Google/Apple Calendar)
instead of the API — it works even if your school has disabled personal
access tokens, since it's a completely separate Canvas feature.

Your generated ntfy topic (already filled into `desktop_pet/config.json`):
`canvaspet-564c7302-0cd`
This name is your private channel — keep the repo private and don't share
this topic name publicly, since anyone who knows it can read (or send to) it.

---

## 1. Get your Canvas calendar feed URL

1. Log into Canvas, go to **Account → Settings**.
2. Scroll down the right-hand sidebar to **Calendar Feed (?)**.
3. Right-click it → **Copy Link Address** (or click it and copy the URL
   from your browser's address bar — either way, don't just visually copy
   it, since it's long).
4. It'll look like:
   `https://yourschool.instructure.com/feeds/calendars/user_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX.ics`

That long random string in the URL *is* your access control — anyone with
this exact URL can read your assignment due dates, so treat it like a
password: don't post it publicly. You'll paste it into GitHub's encrypted
secrets (private, never in code) in step 3 below.

If you don't see "Calendar Feed" in Settings, some schools rename or hide
it slightly differently — search your Canvas help docs for "calendar
feed" or "subscribe to calendar" if you can't find it.

## 2. Create a private GitHub repo and push this folder

```bash
cd CanvasPet
git init
git add .
git commit -m "Initial CanvasPet setup"
```

Then on github.com: **New repository** → name it (e.g. `canvas-pet`) →
**Private** → create it (don't initialize with a README). GitHub will show
you push commands like:

```bash
git remote add origin https://github.com/<your-username>/canvas-pet.git
git branch -M main
git push -u origin main
```

## 3. Add repo secrets

In your new GitHub repo: **Settings → Secrets and variables → Actions →
New repository secret**. Add two:

| Name | Value |
|---|---|
| `CANVAS_ICS_URL` | the calendar feed URL from step 1 |
| `NTFY_TOPIC` | `canvaspet-564c7302-0cd` |

## 4. Test the poller manually

Go to the **Actions** tab in your repo → **Canvas Poller** workflow →
**Run workflow**. Check the run log — it should say "State updated" or
"No changes." If it errors, the log will show why (bad token, wrong URL,
etc.). After this first run it'll fire automatically every 15 minutes.

## 5. Run the desktop pet

```bash
cd desktop_pet
pip install -r requirements.txt
pythonw pet.py
```

(`pythonw` instead of `python` so no console window stays open. On first
run, Windows may ask about firewall access for Python — allow it.)

Nothing appears on screen at first — it's running quietly in the background,
listening for reminders. When one comes through, a little pixel-art owl in
a graduation cap pops up in the bottom-right corner with a speech bubble
for ~20 seconds, then disappears again on its own (click it, or its bubble,
to dismiss early). Left-click-drag to move it anywhere while it's visible;
right-click for a Dismiss/Quit menu.

## 6. Make it start automatically when you log in

Press `Win+R`, type `shell:startup`, hit Enter — this opens your Startup
folder. Create a shortcut there that points to:

```
pythonw.exe "C:\Users\msekh\Documents\CanvasPet\desktop_pet\pet.py"
```

(Right-click in the Startup folder → New → Shortcut → paste the target
above, adjusting the path to `pythonw.exe` if it's not on your PATH — you
can find it with `where pythonw` in a terminal.)

---

## Tuning it

- **Reminder timing:** edit `REMINDER_THRESHOLDS_HOURS` in
  `poller/canvas_poller.py` (currently 48h / 24h / 3h before due).
- **Poll frequency:** edit the `cron` line in
  `.github/workflows/poll.yml` (currently every 15 minutes).
- **Pet look:** edit `desktop_pet/sprites.py` — it's just a 16x16 grid of
  letters mapped to colors, easy to redraw or recolor. Open
  `desktop_pet/preview.html` in a browser (or run
  `python -m http.server` from `desktop_pet/` and visit it) to preview
  edits instantly without restarting the live pet — much faster than
  guessing blind.

## Privacy note

`state.json` (assignment names/due dates) gets committed back to your repo
by the workflow, which is why the repo should be **private**. Your Canvas
calendar feed URL lives only in GitHub's encrypted secrets — never in the
repo itself. If you ever think that URL leaked, go back to Canvas →
Account → Settings and click **"reset"** next to the calendar feed to get
a fresh one (then update the `CANVAS_ICS_URL` secret).
