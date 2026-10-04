"""Streamlit wrapper for the drag-and-drop schematic editor."""

import os

import streamlit.components.v1 as components

_FRONTEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
_component = components.declare_component("circuit_builder", path=_FRONTEND)


def circuit_builder(initial=None, load_token=0, height=640, key=None):
    """
    Render the editor and return the current schematic dict
    ({"components": [...], "wires": [...]}) or None before the first edit.

    initial     schematic to load when `load_token` changes (e.g. an example)
    load_token  change this value to make the editor replace its content
    """
    return _component(
        initial=initial, load_token=load_token, height=height, key=key, default=None
    )
