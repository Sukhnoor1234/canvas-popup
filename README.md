# CanvasPet

A pixel-art desktop pet that watches your Canvas courses and pops up with a
speech bubble whenever a new assignment is posted or a due date is coming up.

**How it works:** a small script runs every 15 minutes for free on GitHub's
servers, checks Canvas for new/upcoming assignments, and pushes a
notification through [ntfy.sh](https://ntfy.sh) (free, no account needed).
The pet on your PC listens for those notifications and reacts to them live.
The cloud side keeps working even when your PC is off; the pet just needs
your PC on to actually show anything.

Your generated ntfy topic (already filled into `desktop_pet/config.json`):
`canvaspet-564c7302-0cd`
This name is your private channel — keep the repo private and don't share
this topic name publicly, since anyone who knows it can read (or send to) it.

---

## 1. Get a Canvas API token

1. Log into Canvas, go to **Account → Settings**.
2. Scroll to **Approved Integrations** and click **+ New Access Token**.
3. Purpose: "CanvasPet reminders" (or anything). Leave expiry blank, or set
   a far-future date. Click **Generate Token**.
4. Copy the token immediately — Canvas only shows it once.
5. Also note your Canvas base URL — the part before `/courses` in your
   browser, e.g. `https://yourschool.instructure.com`.

**Don't paste this token into any chat.** You'll enter it directly into
GitHub's encrypted secrets in step 3 below.

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
New repository secret**. Add three:

| Name | Value |
|---|---|
| `CANVAS_URL` | e.g. `https://yourschool.instructure.com` |
| `CANVAS_TOKEN` | the token from step 1 |
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

You should see a little purple blob settle into the bottom-right corner of
your screen. It'll blink occasionally and hop every so often. When a
reminder comes through, it lights up and shows a speech bubble for ~14
seconds (click it to dismiss early). Left-click-drag to move it anywhere;
right-click for a Quit option.

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
- **Pet look:** edit `desktop_pet/sprites.py` — it's just a 12x12 grid of
  letters mapped to colors, easy to redraw or recolor.

## Privacy note

`state.json` (assignment names/due dates) gets committed back to your repo
by the workflow, which is why the repo should be **private**. Your Canvas
token and Canvas URL live only in GitHub's encrypted secrets — never in the
repo itself.
