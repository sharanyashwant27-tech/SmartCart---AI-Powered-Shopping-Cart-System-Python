"""Admin page module."""

from __future__ import annotations

from frontend.lib import page_admin_catalog, page_admin_dashboard, page_analytics


def render_dashboard() -> None:
    page_admin_dashboard()


def render_catalog() -> None:
    page_admin_catalog()


def render_analytics() -> None:
    page_analytics()
