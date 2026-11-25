cat << 'EOF' > vercel.json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "api/index.py": {
      "includeFiles": "frontend/**",
      "maxDuration": 60
    }
  },
  "routes": [
    { "src": "/(.*)", "dest": "/api/index.py?_vc_path=/$1" }
  ]
}
EOF

cat << 'EOF' > api/index.py
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
EOF

git add .gitignore vercel.json api/index.py && git commit -m "Pass and restore original route path via query parameter" && git push origin main