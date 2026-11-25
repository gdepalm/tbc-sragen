"""Pengaturan aplikasi. Semua nilai bisa diubah lewat file .env (lihat .env.example)."""
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")
except ImportError:  # python-dotenv tidak wajib
    pass


def _db_url():
    url = os.getenv("DATABASE_URL", "").strip() or f"sqlite:///{(BASE / 'data' / 'tbc.db').as_posix()}"
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    # alamat sqlite relatif (mis. sqlite:///data/tbc.db) selalu dihitung dari folder project,
    # sehingga tidak error walaupun terminal dibuka di folder lain
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        p = url[len("sqlite:///"):]
        if p and p != ":memory:" and not Path(p).is_absolute():
            url = f"sqlite:///{(BASE / p).as_posix()}"
    return url


DATABASE_URL = _db_url()
_up = Path(os.getenv("UPLOAD_DIR", "data/upload"))
UPLOAD_DIR = _up if _up.is_absolute() else BASE / _up
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "200"))
# File Excel asli berisi nama/NIK pasien. Default: DIHAPUS setelah diolah (hanya angka agregat disimpan).
SIMPAN_BERKAS_ASLI = os.getenv("SIMPAN_BERKAS_ASLI", "false").lower() == "true"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
