"""
Tiny hand-drawn pixel-art blob pet, as plain text grids.

'.' = transparent
Any other character is looked up in PALETTE for its color.
"""

PALETTE = {
    "B": "#8b6fd1",  # body (soft purple)
    "E": "#ffffff",  # eye white
    "P": "#2b2b3a",  # pupil
    "L": "#5a4499",  # closed-eye line (blink)
    "M": "#2b2b3a",  # mouth
    "H": "#ffb6c1",  # excited blush
    "S": "#ffe066",  # sparkle (excited)
}

# 12x12 base blob shape, no face yet.
_BASE = [
    "....BBBB....",
    "...BBBBBB...",
    "..BBBBBBBB..",
    ".BBBBBBBBBB.",
    ".BBBBBBBBBB.",
    "BBBBBBBBBBBB",
    "BBBBBBBBBBBB",
    "BBBBBBBBBBBB",
    "BBBBBBBBBBBB",
    ".BBBBBBBBBB.",
    ".BBBBBBBBBB.",
    "..BBBBBBBB..",
]
# (rows above are 13 chars long by mistake in a couple places if edited by
# hand later -- keep every row exactly 12 characters.)


def _apply(overrides):
    """Return a copy of the base grid with (row, col) -> char overrides applied."""
    grid = [list(row) for row in _BASE]
    for (r, c), ch in overrides.items():
        grid[r][c] = ch
    return ["".join(row) for row in grid]


def idle_frame(blink=False):
    if blink:
        return _apply({(5, 3): "L", (5, 8): "L"})
    return _apply(
        {
            (4, 3): "E", (5, 3): "P",
            (4, 8): "E", (5, 8): "P",
        }
    )


def excited_frame():
    return _apply(
        {
            (3, 3): "S", (4, 3): "E", (5, 3): "P",
            (3, 8): "S", (4, 8): "E", (5, 8): "P",
            (7, 5): "M", (7, 6): "M",
            (6, 1): "H", (6, 10): "H",
        }
    )


GRID_SIZE = (len(_BASE), len(_BASE[0]))
