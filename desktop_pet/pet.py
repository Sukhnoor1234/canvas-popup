"""
Desktop pixel pet that pops up with Canvas assignment reminders.

Stays completely hidden until the cloud side (poll.yml every 15 min, or
digest.yml every 2 hours) pushes a message to your ntfy.sh topic — then it
appears in the bottom-right corner with a speech bubble, and hides itself
again after a bit. It never sits idle on screen.

Setup:
  1. pip install -r requirements.txt
  2. Copy config.json.example to config.json and fill in your ntfy topic
     (the same NTFY_TOPIC you set as a GitHub secret).
  3. Run:  pythonw pet.py   (pythonw = no console window)

Left-click the pet or its bubble to dismiss early.
Right-click the pet for a Quit option (only available while it's visible).
"""

import json
import queue
import threading
import time
import tkinter as tk
from pathlib import Path

import requests

import sprites

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
PIXEL_SIZE = 8
TRANSPARENT_KEY = "#ff00ff"
BUBBLE_SECONDS = 20


def load_config():
    if not CONFIG_PATH.exists():
        raise SystemExit(
            f"Missing {CONFIG_PATH}.\n"
            "Copy config.json.example to config.json and set your ntfy topic."
        )
    return json.loads(CONFIG_PATH.read_text())


class ListenerThread(threading.Thread):
    """Long-lived background connection to ntfy.sh's SSE stream."""

    def __init__(self, topic, out_queue):
        super().__init__(daemon=True)
        self.topic = topic
        self.out_queue = out_queue

    def run(self):
        url = f"https://ntfy.sh/{self.topic}/sse"
        while True:
            try:
                with requests.get(url, stream=True, timeout=(10, 90)) as resp:
                    for line in resp.iter_lines(decode_unicode=True):
                        if not line or not line.startswith("data:"):
                            continue
                        payload = line[len("data:"):].strip()
                        try:
                            data = json.loads(payload)
                        except json.JSONDecodeError:
                            continue
                        if data.get("event") != "message":
                            continue
                        self.out_queue.put(
                            {
                                "title": data.get("title") or "Canvas",
                                "message": data.get("message") or "",
                            }
                        )
            except requests.RequestException:
                pass
            time.sleep(5)  # reconnect backoff


class Pet:
    def __init__(self, root, topic):
        self.root = root
        self.msg_queue = queue.Queue()
        self.bubble = None
        self.bubble_after_id = None
        self._drag_offset = None
        self._dragged = False
        self.visible = False

        rows, cols = sprites.GRID_SIZE
        w, h = cols * PIXEL_SIZE, rows * PIXEL_SIZE

        root.overrideredirect(True)
        root.wm_attributes("-topmost", True)
        root.wm_attributes("-transparentcolor", TRANSPARENT_KEY)
        root.config(bg=TRANSPARENT_KEY)

        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        margin = 60
        self.base_x = sw - w - margin
        self.base_y = sh - h - margin
        root.geometry(f"{w}x{h}+{self.base_x}+{self.base_y}")

        self.canvas = tk.Canvas(
            root, width=w, height=h, bg=TRANSPARENT_KEY, highlightthickness=0
        )
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.show_menu)

        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="Dismiss", command=self.hide)
        self.menu.add_command(label="Quit pet", command=root.destroy)

        self.draw(sprites.excited_frame())
        root.withdraw()  # start hidden — nothing to say yet

        ListenerThread(topic, self.msg_queue).start()
        self.root.after(300, self.poll_queue)

    # -- drawing --------------------------------------------------------

    def draw(self, grid):
        self.canvas.delete("all")
        for r, row in enumerate(grid):
            for c, ch in enumerate(row):
                if ch == ".":
                    continue
                color = sprites.PALETTE.get(ch, TRANSPARENT_KEY)
                x0, y0 = c * PIXEL_SIZE, r * PIXEL_SIZE
                self.canvas.create_rectangle(
                    x0, y0, x0 + PIXEL_SIZE, y0 + PIXEL_SIZE, fill=color, outline=""
                )

    # -- reminders --------------------------------------------------------

    def poll_queue(self):
        try:
            while True:
                item = self.msg_queue.get_nowait()
                self.show_bubble(item["title"], item["message"])
        except queue.Empty:
            pass
        self.root.after(300, self.poll_queue)

    def show_bubble(self, title, message):
        if self.bubble_after_id:
            self.root.after_cancel(self.bubble_after_id)
        if self.bubble:
            self.bubble.destroy()
            self.bubble = None

        self.root.deiconify()
        self.root.geometry(f"+{self.base_x}+{self.base_y}")
        self.draw(sprites.excited_frame())
        self.visible = True

        self.bubble = tk.Toplevel(self.root)
        self.bubble.overrideredirect(True)
        self.bubble.wm_attributes("-topmost", True)
        frame = tk.Frame(self.bubble, bg="#fffbe6", highlightbackground="#8b6fd1",
                          highlightthickness=2, padx=10, pady=8)
        frame.pack()
        tk.Label(
            frame, text=title, bg="#fffbe6", fg="#2b2b3a",
            font=("Segoe UI", 10, "bold"), justify="left", anchor="w",
        ).pack(anchor="w")
        tk.Label(
            frame, text=message, bg="#fffbe6", fg="#2b2b3a",
            font=("Segoe UI", 9), justify="left", anchor="w", wraplength=260,
        ).pack(anchor="w")

        self.bubble.update_idletasks()
        bw = self.bubble.winfo_width()
        bx = self.base_x + (sprites.GRID_SIZE[1] * PIXEL_SIZE) // 2 - bw // 2
        by = self.base_y - self.bubble.winfo_height() - 12
        self.bubble.geometry(f"+{bx}+{by}")
        self.bubble.bind("<Button-1>", lambda e: self.hide())

        self.bubble_after_id = self.root.after(BUBBLE_SECONDS * 1000, self.hide)

    def hide(self):
        if self.bubble_after_id:
            self.root.after_cancel(self.bubble_after_id)
            self.bubble_after_id = None
        if self.bubble:
            self.bubble.destroy()
            self.bubble = None
        self.root.withdraw()
        self.visible = False

    # -- dragging / menu ----------------------------------------------------

    def on_press(self, event):
        self._drag_offset = (event.x, event.y)
        self._dragged = False

    def on_drag(self, event):
        if self._drag_offset is None:
            return
        self._dragged = True
        dx, dy = event.x - self._drag_offset[0], event.y - self._drag_offset[1]
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.base_x, self.base_y = x, y
        self.root.geometry(f"+{x}+{y}")

    def on_release(self, event):
        if not self._dragged:
            self.hide()
        self._drag_offset = None

    def show_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)


def main():
    config = load_config()
    root = tk.Tk()
    Pet(root, config["ntfy_topic"])
    root.mainloop()


if __name__ == "__main__":
    main()
