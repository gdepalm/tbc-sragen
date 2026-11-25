from urllib.parse import unquote
from app.main import app as _fastapi_app


async def app(scope, receive, send):
    if scope["type"] == "http" and scope.get("path") in ("/api/index", "/api/index.py"):
        headers = dict(scope.get("headers", []))
        orig = headers.get(b"x-vercel-original-path", b"").decode("utf-8", errors="ignore")
        if orig:
            restored = "/" + orig.lstrip("/")
            scope = {**scope, "path": restored, "raw_path": restored.encode("utf-8")}
        else:
            raw_match = headers.get(b"x-now-route-matches", b"").decode("utf-8", errors="ignore")
            if "1=" in raw_match:
                restored = "/" + unquote(raw_match.split("1=", 1)[1].split("&", 1)[0]).lstrip("/")
                scope = {**scope, "path": restored, "raw_path": restored.encode("utf-8")}
    await _fastapi_app(scope, receive, send)