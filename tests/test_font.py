"""Labels come out the same on every machine: one font file, shipped with a dependency."""

from printlab import font


def test_labels_use_a_font_file_every_machine_has():
    # Windows has Arial and CI doesn't, so a named system font draws different labels in CI.
    assert font.FONT_FILE.name == "DejaVuSans.ttf"
    assert font.FONT_FILE.is_file()


def test_text_draws_glyphs_from_that_file():
    a = font.text("0.30", 3.5).bounding_box()
    assert a.size.X > 0 and a.size.Y > 0
