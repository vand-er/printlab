"""The labels' font: a file every machine has, so labels match in CI and on the user's PC."""

from pathlib import Path

import matplotlib
from build123d import Sketch, Text

# DejaVu Sans ships inside matplotlib, a dependency; a system font name (Arial) is missing in CI.
FONT_FILE = Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf"


def text(txt: str, size: float) -> Sketch:
    """`txt` at `size` mm, centred on the origin."""
    return Text(txt, size, font_path=str(FONT_FILE))
