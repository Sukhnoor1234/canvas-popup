"""
Tiny hand-drawn pixel-art owl pet (with a graduation cap), as plain text grids.

'.' = transparent
Any other character is looked up in PALETTE for its color.
"""

PALETTE = {
    "O": "#8b5e3c",  # feathers (body)
    "W": "#6b4423",  # folded wings (darker feathers)
    "F": "#d9b382",  # face disc (lighter feathers around the eyes)
    "Y": "#f4a942",  # eye (amber)
    "P": "#1a1410",  # pupil
    "L": "#a67c52",  # closed-eye line (blink)
    "B": "#e8891c",  # beak
    "C": "#1a1a1a",  # graduation cap
    "T": "#ffd23f",  # cap tassel
    "Q": "#e8891c",  # feet/talons
    "S": "#ffe066",  # sparkle (excited)
    "K": "#ffb6c1",  # blush (excited)
}


def _row(*parts):
    """Build a 16-char row from (char, count) pairs, e.g. _row(('.', 3), ('O', 4))."""
    s = "".join(ch * n for ch, n in parts)
    assert len(s) == 16, f"row is {len(s)} chars, expected 16: {s!r}"
    return s


# 16x16 base shape: graduation cap + tassel, ear tufts, face disc, beak,
# folded wings, feet. Eyes are overlaid per-frame below (owls don't get
# eyebrows -- their whole expression lives in the eyes and beak).
_BASE = [
    _row((".", 2), ("C", 12), (".", 2)),                                    # 0 mortarboard top
    _row((".", 3), ("C", 10), (".", 3)),                                    # 1 cap brim
    _row((".", 4), ("C", 6), (".", 1), ("T", 1), (".", 4)),                 # 2 cap band + dangling tassel
    _row((".", 5), ("O", 2), (".", 2), ("O", 2), (".", 5)),                 # 3 ear tufts
    _row(("O", 3), ("F", 10), ("O", 3)),                                    # 4 head top / face disc begins
    _row(("O", 2), ("F", 12), ("O", 2)),                                    # 5 (eyes, excited only)
    _row(("O", 1), ("F", 14), ("O", 1)),                                    # 6 eyes (top half)
    _row(("O", 1), ("F", 14), ("O", 1)),                                    # 7 eyes (bottom half + pupils)
    _row(("O", 2), ("F", 12), ("O", 2)),                                    # 8 below eyes
    _row(("O", 3), ("F", 4), ("B", 2), ("F", 4), ("O", 3)),                 # 9 beak
    _row(("O", 2), ("F", 12), ("O", 2)),                                    # 10 chin / face disc bottom
    _row(("W", 2), ("O", 12), ("W", 2)),                                    # 11 folded wings + chest
    _row(("W", 2), ("O", 12), ("W", 2)),                                    # 12
    _row(("W", 1), ("O", 14), ("W", 1)),                                    # 13 belly widening
    _row((".", 3), ("Q", 4), (".", 2), ("Q", 4), (".", 3)),                 # 14 feet
    _row((".", 4), ("Q", 3), (".", 2), ("Q", 3), (".", 4)),                 # 15 talons
]


def _apply(overrides):
    """Return a copy of the base grid with (row, col) -> char overrides applied."""
    grid = [list(row) for row in _BASE]
    for (r, c), ch in overrides.items():
        grid[r][c] = ch
    return ["".join(row) for row in grid]


def idle_frame(blink=False):
    if blink:
        eyes = {(7, c): "L" for c in (3, 4, 5, 6, 9, 10, 11, 12)}
    else:
        eyes = {(6, c): "Y" for c in (3, 4, 5, 6, 9, 10, 11, 12)}
        eyes.update(
            {
                (7, 3): "Y", (7, 4): "P", (7, 5): "P", (7, 6): "Y",
                (7, 9): "Y", (7, 10): "P", (7, 11): "P", (7, 12): "Y",
            }
        )
    return _apply(eyes)


def excited_frame():
    overrides = {(5, c): "Y" for c in (3, 4, 5, 6, 9, 10, 11, 12)}
    overrides.update({(6, c): "Y" for c in (3, 4, 5, 6, 9, 10, 11, 12)})
    overrides.update(
        {
            (7, 3): "Y", (7, 4): "P", (7, 5): "P", (7, 6): "Y",
            (7, 9): "Y", (7, 10): "P", (7, 11): "P", (7, 12): "Y",
            # sparkle
            (5, 2): "S", (5, 13): "S",
            # blush
            (8, 2): "K", (8, 13): "K",
            # wide-open beak (surprised)
            (9, 6): "B", (9, 9): "B",
        }
    )
    return _apply(overrides)


GRID_SIZE = (len(_BASE), len(_BASE[0]))
