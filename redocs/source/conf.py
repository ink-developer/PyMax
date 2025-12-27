# Configuration file for the Sphinx documentation builder.
import os
import sys

# -- Project information -----------------------------------------------------
project = "PyMax"
author = "ink-developer"
copyright = "2025, ink-developer"
release = "1.2.3"

# -- Path setup ---------------------------------------------------------------
sys.path.insert(0, os.path.abspath("../../src"))

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",  # Автодокументация классов/функций
    "sphinx.ext.napoleon",  # Поддержка Google/NumPy docstrings
    "sphinx.ext.viewcode",  # Ссылка на исходный код
]

templates_path = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

language = "python"


autodoc_default_options = {
    "members": True,
    "inherited-members": True,
    "undoc-members": False,
    "show-inheritance": False,
}

autodoc_typehints = "description"

html_theme = "furo"
html_static_path = ["_static"]

pygments_style = "friendly"
pygments_dark_style = "monokai"

html_theme_options = {
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
}
