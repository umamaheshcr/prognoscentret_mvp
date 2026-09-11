"""The deployment gate. Run with:  .venv/Scripts/python -m pytest -q

`app/main.py` is local-only by decision, because the driver pages carry
verbatim quotes from licensed bank research. `app/auth.py` is what lets it be
hosted anyway, so the property that matters is not "it has a password" — it is
**it fails closed**: an unconfigured credential must refuse everything a
non-local client asks for, rather than serve it.

That is a claim about what happens when someone forgets an environment
variable, which is exactly the kind of claim that rots silently. So it is
asserted here, next to the ones about guard and the decomposition.
"""

import base64
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402

REMOTE = ("203.0.113.7", 50000)      # TEST-NET-3, never a real client
LOCAL = ("127.0.0.1", 50000)

# Every kind of thing the app serves: a page, an API route, and the static
# mount — which an app-level dependency would have missed.
PATHS = ["/", "/api/panel", "/static/app.js"]


def _client(peer):
    from fastapi.testclient import TestClient
    try:
        return TestClient(app, client=peer)
    except TypeError:                 # pragma: no cover - older starlette
        pytest.skip("this starlette's TestClient cannot set the peer address")


def _basic(user, password):
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@pytest.fixture
def unset(monkeypatch):
    monkeypatch.delenv("MIMIR_BASIC", raising=False)


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("MIMIR_BASIC", "mimir:a-long-shared-password")
    return _basic("mimir", "a-long-shared-password")


# ── fails closed ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("path", PATHS)
def test_no_credential_refuses_a_remote_client(unset, path):
    """The important one. A forgotten env var must not publish the research."""
    r = _client(REMOTE).get(path)
    assert r.status_code == 503
    assert "MIMIR_BASIC" in r.text


def test_no_credential_still_answers_the_health_check(unset):
    """A platform probe cannot log in, so /healthz stays open — and only it."""
    r = _client(REMOTE).get("/healthz")
    assert r.status_code == 200 and r.json()["ok"] is True


@pytest.mark.parametrize("path", PATHS)
def test_no_credential_leaves_localhost_working(unset, path):
    """run.ps1 and run.sh must keep working with no configuration at all."""
    assert _client(LOCAL).get(path).status_code == 200


# ── with a credential ──────────────────────────────────────────────────────
@pytest.mark.parametrize("path", PATHS)
def test_a_credential_is_demanded_and_the_browser_is_told_how(configured, path):
    r = _client(REMOTE).get(path)
    assert r.status_code == 401
    assert r.headers["www-authenticate"].startswith("Basic")


@pytest.mark.parametrize("path", PATHS)
def test_the_right_credential_is_let_through(configured, path):
    assert _client(REMOTE).get(path, headers=configured).status_code == 200


def test_the_static_mount_is_behind_the_gate_too(configured):
    """Middleware rather than a dependency, because mounts bypass dependencies."""
    c = _client(REMOTE)
    assert c.get("/static/app.js").status_code == 401
    assert c.get("/static/app.js", headers=configured).status_code == 200


@pytest.mark.parametrize("header", [
    {},
    {"Authorization": "Basic "},
    {"Authorization": "Basic !!!not-base64!!!"},
    {"Authorization": "Bearer a-token"},
])
def test_nothing_else_gets_in_and_nothing_raises(configured, header):
    assert _client(REMOTE).get("/", headers=header).status_code == 401


@pytest.mark.parametrize("user,password", [
    ("mimir", "wrong"),
    ("someone", "a-long-shared-password"),
    ("", ""),
])
def test_the_wrong_credential_is_refused(configured, user, password):
    assert _client(REMOTE).get("/", headers=_basic(user, password)).status_code == 401


def test_localhost_does_not_bypass_a_configured_credential(configured):
    """Loopback is a fallback for no configuration, not an exemption from it."""
    assert _client(LOCAL).get("/").status_code == 401


def test_only_the_first_colon_separates_user_from_password(monkeypatch):
    """A password may contain colons; the split must not mangle it."""
    monkeypatch.setenv("MIMIR_BASIC", "mimir:pa:ss:word")
    c = _client(REMOTE)
    assert c.get("/", headers=_basic("mimir", "pa:ss:word")).status_code == 200
    assert c.get("/", headers=_basic("mimir", "pa")).status_code == 401


# ── the cache that makes a 512 MB host viable ──────────────────────────────
def test_the_pickled_snapshot_is_the_same_data_as_the_workbook():
    """tools/precache.py exists for memory, not for convenience — so it may not
    change a single value on the way through."""
    import pandas as pd
    from app import data as appdata

    for book in [appdata.DATA / "master_endogenous.xlsx", appdata.EXO_FILE]:
        cache = book.with_suffix(".pkl")
        if not cache.exists():
            pytest.skip("no cache written; run python tools/precache.py")
        fresh = pd.read_excel(book)
        cached = pd.read_pickle(cache)
        assert fresh.equals(cached)
        assert list(fresh.dtypes) == list(cached.dtypes)


def test_a_cache_older_than_its_workbook_is_ignored():
    """A refreshed snapshot must never be served from a stale pickle."""
    import os
    from app import data as appdata

    book = appdata.DATA / "master_endogenous.xlsx"
    cache = book.with_suffix(".pkl")
    if not cache.exists():
        pytest.skip("no cache written; run python tools/precache.py")

    stat = cache.stat()
    try:
        os.utime(cache, (stat.st_atime, book.stat().st_mtime - 60))
        frame = appdata._read(book)          # must fall back to the workbook
        assert len(frame) > 0
    finally:
        os.utime(cache, (stat.st_atime, stat.st_mtime))
