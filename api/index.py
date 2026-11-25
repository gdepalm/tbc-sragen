"""Titik masuk fungsi serverless Vercel.

Vercel mengganti path permintaan menjadi lokasi berkas fungsi ini, sehingga path asli
tidak lagi terlihat oleh FastAPI. Karena itu path asli dititipkan sebagai parameter kueri
`_vc_path` (lihat "routes" pada vercel.json) lalu dipulihkan di sini sebelum permintaan
diteruskan ke aplikasi FastAPI di app/main.py.

Uji lokal: uvicorn api.index:app --reload  (sama dengan uvicorn app.main:app --reload)
"""
import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode

import app.main as _modul
from starlette.responses import JSONResponse

_fastapi_app = _modul.app


def _keterangan_lokasi():
    """Daftar isi folder penting, dipakai untuk menelusuri masalah pemasangan."""
    keterangan = {}
    for a in (Path.cwd(), Path(__file__).resolve().parent, Path("/var/task")):
        try:
            keterangan[str(a)] = sorted(p.name for p in a.iterdir())[:30]
        except OSError as e:
            keterangan[str(a)] = f"tidak terbaca: {e}"
    keterangan["frontend_ditemukan"] = _modul._fe is not None
    keterangan["folder_frontend"] = str(_modul._fe) if _modul._fe is not None else None
    return keterangan


async def _diagnostik(scope, receive, send, pesan):
    isi = {
        "diagnostik": pesan,
        "path_diterima": str(scope.get("path")),
        "raw_path": (scope.get("raw_path") or b"").decode("utf-8", "replace"),
        "query_string": scope.get("query_string", b"").decode("utf-8", "replace"),
        "cwd": os.getcwd(),
        "vercel": bool(os.getenv("VERCEL")),
        "skema_database": (os.getenv("DATABASE_URL", "").split(":", 1)[0] or "(tidak diset)"),
        "folder_unggahan": str(_modul.config.UPLOAD_DIR),
        "lokasi": _keterangan_lokasi(),
        "header": {k.decode(): v.decode("utf-8", "replace")[:150] for k, v in scope.get("headers", [])},
    }
    await JSONResponse(isi)(scope, receive, send)


async def app(scope, receive, send):
    if scope["type"] != "http":
        await _fastapi_app(scope, receive, send)
        return

    qs = parse_qs(scope.get("query_string", b"").decode("utf-8", errors="ignore"), keep_blank_values=True)

    if "_vc_path" in qs:
        raw_path = unquote(qs.pop("_vc_path")[0])
        if "$" in raw_path:   # substitusi pada vercel.json gagal -> laporkan apa adanya
            await _diagnostik(scope, receive, send, "path asli tidak terkirim (_vc_path tidak disubstitusi)")
            return
        restored = "/" + raw_path.lstrip("/")
        scope = {
            **scope,
            "path": restored,
            "raw_path": restored.encode("utf-8"),
            "query_string": urlencode(qs, doseq=True).encode("utf-8"),
        }
    elif qs.get("diagnostik") or scope.get("path", "").rstrip("/").endswith(("/index", "/index.py")):
        await _diagnostik(scope, receive, send, "path permintaan menunjuk ke berkas fungsi, bukan alamat asli")
        return

    await _fastapi_app(scope, receive, send)
