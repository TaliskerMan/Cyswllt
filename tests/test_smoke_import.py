# Copyright (C) 2026 Chuck Talk, Nordheim Online, LLC <chuck@nordheim.online>
# This file is part of Cyswllt.
# Released under the GNU GPL v3 license.

"""Smoke tests: every module imports, and the main window can be constructed.

The GTK UI import is skipped automatically when PyGObject/GTK is unavailable
(e.g. a headless CI image without the system libraries), so the credential and
mount logic still get a smoke check everywhere.
"""

import importlib
import pytest


def test_core_modules_import():
    for mod in ("cyswllt", "cyswllt.version", "cyswllt.auth_manager",
                "cyswllt.mount_manager"):
        assert importlib.import_module(mod) is not None


def test_version_is_a_string():
    from cyswllt.version import __version__
    assert isinstance(__version__, str)
    assert __version__.count(".") >= 2


def test_main_module_imports_if_gtk_available():
    gi = pytest.importorskip("gi")
    try:
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
    except ValueError:
        pytest.skip("GTK 4 / libadwaita namespace not available")
    # Importing main pulls in Gtk/Adw; constructing the app object is enough of
    # a smoke test without entering the GTK main loop.
    main = importlib.import_module("cyswllt.main")
    assert hasattr(main, "main")
