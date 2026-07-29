"""HTTP client helpers for the Streamlit frontend."""

from __future__ import annotations

import os
from typing import Any, Optional

import requests
import streamlit as st

API_BASE = os.getenv("SMARTCART_API_URL", "http://127.0.0.1:8904/api/v1")


class APIError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    token = st.session_state.get("access_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def api_request(
    method: str,
    path: str,
    *,
    json: Optional[dict[str, Any]] = None,
    params: Optional[dict[str, Any]] = None,
) -> Any:
    url = f"{API_BASE}{path}"
    try:
        resp = requests.request(
            method, url, json=json, params=params, headers=_headers(), timeout=30
        )
    except requests.RequestException as exc:
        raise APIError(f"Cannot reach API at {API_BASE}: {exc}") from exc

    if resp.status_code >= 400:
        detail = "Request failed"
        try:
            body = resp.json()
            detail = (
                body.get("error", {}).get("detail")
                or body.get("detail")
                or detail
            )
        except Exception:  # noqa: BLE001
            detail = resp.text or detail
        raise APIError(str(detail), resp.status_code)

    if resp.status_code == 204 or not resp.content:
        return None
    return resp.json()


def get(path: str, **kwargs: Any) -> Any:
    return api_request("GET", path, **kwargs)


def post(path: str, json: Optional[dict] = None, **kwargs: Any) -> Any:
    return api_request("POST", path, json=json, **kwargs)


def patch(path: str, json: Optional[dict] = None, **kwargs: Any) -> Any:
    return api_request("PATCH", path, json=json, **kwargs)


def delete(path: str, **kwargs: Any) -> Any:
    return api_request("DELETE", path, **kwargs)


def is_authenticated() -> bool:
    return bool(st.session_state.get("access_token"))


def is_admin() -> bool:
    user = st.session_state.get("user") or {}
    return user.get("role") == "admin"


def login_user(email: str, password: str) -> dict:
    data = post("/auth/login", {"email": email, "password": password})
    st.session_state["access_token"] = data["access_token"]
    st.session_state["refresh_token"] = data["refresh_token"]
    st.session_state["user"] = data["user"]
    return data


def register_user(email: str, password: str, full_name: str) -> dict:
    data = post(
        "/auth/register",
        {"email": email, "password": password, "full_name": full_name},
    )
    st.session_state["access_token"] = data["access_token"]
    st.session_state["refresh_token"] = data["refresh_token"]
    st.session_state["user"] = data["user"]
    return data


def logout_user() -> None:
    for key in ("access_token", "refresh_token", "user", "coupon_code"):
        st.session_state.pop(key, None)
