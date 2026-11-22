"""`@pytest.mark.real_slicer`: the test runs the real Bambu Studio, so it is slow and skipped without it."""

import pytest

from printlab import profiles, slicing

FILAMENT = "Overture PETG transparent @Bambu Lab X1 Carbon 0.4 nozzle"


def _bambu_ready() -> bool:
    try:
        slicing.bambu_studio()
        profiles.filament_preset(FILAMENT)
    except (slicing.SliceError, profiles.ProfileError):
        return False
    return profiles.SYSTEM.is_dir()


def pytest_configure(config):
    config.addinivalue_line("markers", "real_slicer: runs the real Bambu Studio; slow, skipped where absent")


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    """Before `-m` selects tests, so a real-slicer test counts as slow."""
    ready = None
    for item in items:
        if item.get_closest_marker("real_slicer"):
            item.add_marker(pytest.mark.slow)
            if ready is None:
                ready = _bambu_ready()
            if not ready:
                item.add_marker(pytest.mark.skip(reason="Bambu Studio, its profiles or the preset absent"))
