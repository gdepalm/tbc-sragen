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
    if url.startswith("postgresql+psycopg://"):
        url = url.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql+psycopg2://"):
        pass
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    # alamat sqlite relatif (mis. sqlite:///data/tbc.db) selalu dihitung dari folder project,
    # sehingga tidak error walaupun terminal dibuka di folder lain
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        p = url[len("sqlite:///"):]
        if p and p != ":memory:" and not Path(p).is_absolute():
            url = f"sqlite:///{(BASE / p).as_posix()}"
    return url


DATABASE_URL = _db_url()

# Platform serverless (Vercel) menandai dirinya lewat variabel lingkungan VERCEL=1.
# Di sana hanya folder /tmp yang bisa ditulis, sehingga berkas unggahan sementara
# diarahkan ke sana (dan pengolahan dijalankan di dalam permintaan yang sama).
SERVERLESS = bool(os.getenv("VERCEL"))


def _bisa_ditulis(p: Path) -> bool:
    """Pastikan folder benar-benar bisa ditulis, bukan hanya berhasil dibuat."""
    try:
        p.mkdir(parents=True, exist_ok=True)
        uji = p / ".uji_tulis"
        uji.write_text("ok", encoding="utf-8")
        uji.unlink()
        return True
    except OSError:
        return False


def _folder_unggah() -> Path:
    import tempfile

    diminta = os.getenv("UPLOAD_DIR", "").strip()
    if not diminta:
        diminta = "/tmp/tbc/upload" if SERVERLESS else "data/upload"
    p = Path(diminta)
    p = p if p.is_absolute() else BASE / p
    if _bisa_ditulis(p):
        return p
    # folder yang diminta tidak bisa ditulis (mis. sistem berkas hanya-baca) -> pakai folder sementara
    cadangan = Path(tempfile.gettempdir()) / "tbc-upload"
    cadangan.mkdir(parents=True, exist_ok=True)
    print(f"[peringatan] {p} tidak bisa ditulis, berkas unggahan dialihkan ke {cadangan}")
    return cadangan


UPLOAD_DIR = _folder_unggah()
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "200"))
# File Excel asli berisi nama/NIK pasien. Default: DIHAPUS setelah diolah (hanya angka agregat disimpan).
SIMPAN_BERKAS_ASLI = os.getenv("SIMPAN_BERKAS_ASLI", "false").lower() == "true"
# Di serverless, utas latar (thread) dibekukan begitu balasan dikirim, jadi pengolahan
# berkas harus selesai di dalam permintaan. Set PROSES_SINKRON=1 untuk memaksa perilaku itu.
PROSES_SINKRON = SERVERLESS or os.getenv("PROSES_SINKRON", "").lower() in ("1", "true", "ya", "yes")
