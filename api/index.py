from urllib.parse import parse_qs, unquote, urlencode
from app.main import app as _fastapi_app


async def app(scope, receive, send):
    if scope["type"] == "http":
        qs = parse_qs(scope.get("query_string", b"").decode("utf-8", errors="ignore"), keep_blank_values=True)
        if "_vc_path" in qs:
            raw_path = unquote(qs.pop("_vc_path")[0])
            restored = "/" + raw_path.lstrip("/")
            clean_qs = urlencode(qs, doseq=True).encode("utf-8")
            scope = {
                **scope,
                "path": restored,
                "raw_path": restored.encode("utf-8"),
                "query_string": clean_qs,
            }
    await _fastapi_app(scope, receive, send)
