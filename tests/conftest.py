import tkinter as tk

import pytest


@pytest.fixture(scope="session")
def tk_master():
    """Share a Tcl interpreter; create a fresh toplevel for each Tk UI test."""
    root = tk.Tk()
    root.withdraw()
    try:
        yield root
    finally:
        root.destroy()
