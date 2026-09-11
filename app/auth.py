"""One gate in front of everything, for deployments that are not localhost.

`main.py` opens with a decision: local only, on 127.0.0.1, because the pages
display verbatim quotes from licensed bank research and that is the same thing
that has kept the production console undeployed. Putting this app on a hosted
URL crosses exactly that line, so the line needs a door with a lock on it.

The rule here is therefore **fail closed**, not fail open:

  * `MIMIR_BASIC` set (as "user:password")  -> every request must present it.
  * `MIMIR_BASIC` unset, request from loopback -> allowed. This is what keeps
    `run.ps1` / `run.sh` working unchanged on a laptop.
  * `MIMIR_BASIC` unset, request from anywhere else -> 503, refused.

So a forgotten environment variable on the host locks the app, rather than
publishing licensed research. `/healthz` is the one exempt path, because a
platform health check cannot log in.

Basic auth over HTTPS is adequate for a gated demo among colleagues. It is not
an identity system: there is one shared credential, no per-user record, and
nothing here tells the journal who made a decision. When this needs to be more
than a demo, the answer is the organisation's own identity provider in front of
it (Entra ID / Easy Auth on Azure, or Cloudflare Access), not a longer password.
"""

import base64
import os
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

OPEN_PATHS = {"/healthz"}
LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _expected() -> str:
    return (os.environ.get("MIMIR_BASIC") or "").strip()


def _is_loopback(request) -> bool:
    client = request.client
    return bool(client) and client.host in LOOPBACK


def _challenge() -> Response:
    return Response(
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="Mimir", charset="UTF-8"'},
    )


class BasicAuth(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path in OPEN_PATHS:
            return await call_next(request)

        expected = _expected()

        if not expected:
            if _is_loopback(request):
                return await call_next(request)
            return JSONResponse(
                {"error": "MIMIR_BASIC is not configured on this host",
                 "reason": "This build refuses to serve licensed research "
                           "without a credential. Set MIMIR_BASIC to "
                           "'user:password' and restart."},
                status_code=503,
            )

        header = request.headers.get("authorization", "")
        if not header.startswith("Basic "):
            return _challenge()
        try:
            given = base64.b64decode(header[6:], validate=True).decode("utf-8")
        except Exception:
            return _challenge()
        if not secrets.compare_digest(given, expected):
            return _challenge()

        return await call_next(request)
