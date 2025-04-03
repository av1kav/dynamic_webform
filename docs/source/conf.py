# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Offerings to the Sphinx gods
for abspath in [
    os.path.abspath('..'),
    os.path.abspath('../..'),
    os.path.abspath('../../..')
]:
    print(f"Adding {abspath} to abspath.")
    sys.path.insert(0, abspath)

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Dynamic Webforms'
copyright = '2025, Avinash Venugopal'
author = 'Avinash Venugopal'
release = '0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.extlinks'
]
extlinks = {
    "git_tag": ("https://github.com/av1kav/dynamic_webform/tree/%s", "%s"),
}

autodoc_default_options = {
    'members': True,
    'inherited-members': True,
    'show-inheritance': True
}
templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']
html_sidebars = {
    '**': [
        'about.html',
        'searchfield.html',
        'navigation.html',
        'relations.html',
    ]
}

html_theme_options = {
    "description": "Information, guides and API references for the SCAN Data Platform Dynamic Webform.",
    "github_user": "av1kav",
    "github_repo": "dynamic_webform",
    "fixed_sidebar": True,
    "github_banner": True,
    #'logo':'img/logo.png',
    'page_width': '90%',
    'sidebar_width': '250px',
    'extra_nav_links': {
        'Back to Dashboard': "/dashboard"
    },
    'show_powered_by': True,
}