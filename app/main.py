"""API TBC Monitoring Dashboard Kabupaten Sragen."""
import hashlib
import logging
import math
import os
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

import pandas as pd
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select, text

from . import config
from .api_kontak import router as router_kontak
from .api_target import router as router_target
from .db import get_db, init_db
from .models import Batch, Berkas, Masalah
from .readers import NAMA_JENIS
from .services import rekap as R, unggah

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


_GALAT_MULAI: Optional[str] = None


def _mulai():
    """Siapkan database saat layanan menyala.

    Kegagalan di sini (mis. DATABASE_URL salah) TIDAK menghentikan seluruh layanan:
    galatnya disimpan untuk ditampilkan pada /api/kesehatan supaya mudah didiagnosis.
    """
    global _GALAT_MULAI
    try:
        init_db()
        from .db import SessionLocal
        with SessionLocal() as db:
            for b in db.scalars(select(Batch).where(Batch.status.in_(("diproses", "menunggu")))):
                b.status, b.pesan = "gagal", "Pengolahan terhenti karena server dimulai ulang. Silakan unggah ulang."
            db.commit()
        _GALAT_MULAI = None
    except Exception as e:  # noqa: BLE001 - dilaporkan lewat /api/kesehatan, bukan mematikan layanan
        _GALAT_MULAI = f"{type(e).__name__}: {e}"
        logging.getLogger("tbc").exception("Gagal menyiapkan database saat mulai")


@asynccontextmanager
async def _lifespan(_app):
    _mulai()
    yield


app = FastAPI(title="TBC Monitoring Dashboard Kabupaten Sragen", lifespan=_lifespan)
app.include_router(router_target)
app.include_router(router_kontak)


@app.middleware("http")
async def _tanpa_cache(request, call_next):
    """Halaman & skrip website tidak disimpan di cache browser, supaya perubahan kode langsung terlihat
    (penyebab umum 'kode sudah diganti tapi tampilan tetap lama')."""
    resp = await call_next(request)
    if not request.url.path.startswith("/api/") and request.url.path.endswith(("/", ".html", ".js", ".css")):
        resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp


def bersih(o):
    """Ubah NaN/NaT menjadi None supaya valid sebagai JSON."""
    if isinstance(o, dict):
        return {k: bersih(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [bersih(v) for v in o]
    if type(o).__module__ == "numpy" and hasattr(o, "item"):   # angka numpy -> angka Python biasa
        o = o.item()
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    if isinstance(o, (date, pd.Timestamp)):
        return o.isoformat()
    return o


def _b(b: Batch):
    return dict(id=b.id, jenis=b.jenis, nama_jenis=NAMA_JENIS.get(b.jenis, b.jenis), periode=b.periode_label,
                status=b.status, aktif=b.aktif, progres=b.progres, pesan=b.pesan, baris_dibaca=b.baris_dibaca,
                baris_berhasil=b.baris_berhasil, baris_ditolak=b.baris_ditolak, baris_ganda=b.baris_ganda,
                dibuat=b.dibuat.isoformat() if b.dibuat else None, selesai=b.selesai_pada.isoformat() if b.selesai_pada else None,
                diganti_oleh=b.diganti_oleh,
                berkas=[dict(nama=x.nama_asli, ukuran=x.ukuran, status=x.status, baris=x.baris, pesan=x.pesan) for x in b.berkas])


def _x(x: Berkas):
    return dict(nama=x.nama_asli, ukuran=x.ukuran, jenis=x.jenis, nama_jenis=NAMA_JENIS.get(x.jenis), status=x.status, pesan=x.pesan, batch_id=x.batch_id)


@app.get("/api/kesehatan")
def kesehatan(request: Request, db=Depends(get_db)):
    """Pemeriksaan kondisi layanan: sambungan database, halaman depan, dan folder unggahan.

    Dipakai untuk memastikan hasil pemasangan di server berjalan wajar. Tidak menampilkan
    isi kredensial, hanya jenis database yang dipakai.
    """
    info = {
        "status": "ok",
        "waktu": datetime.now().isoformat(timespec="seconds"),
        "alamat_diminta": request.url.path,
        "halaman_depan": _fe is not None,
        "folder_halaman": str(_fe) if _fe is not None else None,
        "folder_unggahan": str(config.UPLOAD_DIR),
        "jenis_database": "postgresql" if config.DATABASE_URL.startswith(("postgresql", "postgres")) else "sqlite",
        "database_terhubung": False,
        "jumlah_batch": None,
        "pesan": None,
    }
    try:
        db.execute(text("select 1"))
        info["jumlah_batch"] = db.scalar(select(func.count()).select_from(Batch))
        info["database_terhubung"] = True
    except Exception as e:  # noqa: BLE001
        info["status"] = "bermasalah"
        info["pesan"] = f"{type(e).__name__}: {e}"[:300]
    if _GALAT_MULAI:
        info["status"] = "bermasalah"
        info["pesan"] = info["pesan"] or _GALAT_MULAI
    return info


@app.post("/api/upload")
async def upload(files: List[UploadFile] = File(...), mode: str = Form("tambah"), konfirmasi_ganti: bool = Form(False),
                 db=Depends(get_db)):
    if mode not in ("tambah", "ganti", "batal"):
        raise HTTPException(400, "Mode harus 'tambah', 'ganti', atau 'batal'.")
    daftar, batas = [], config.MAX_UPLOAD_MB * 1024 * 1024
    for f in files:
        nama = Path(f.filename or "tanpa_nama").name
        path = str(config.UPLOAD_DIR / f"{uuid4().hex}.xlsx")
        h, ukuran, err, awal = hashlib.sha256(), 0, None, b""
        with open(path, "wb") as out:
            while chunk := await f.read(1 << 20):
                if not awal:
                    awal = chunk[:4]
                ukuran += len(chunk)
                if ukuran > batas:
                    err = f"Ukuran file melebihi batas {config.MAX_UPLOAD_MB} MB."
                    break
                h.update(chunk); out.write(chunk)
        if not err and awal != b"PK\x03\x04":
            err = "Isi file bukan Excel .xlsx yang valid."
        daftar.append((nama, path, ukuran, h.hexdigest(), err))
    batches, berkas = unggah.terima(db, daftar, mode, konfirmasi_ganti)
    return bersih(dict(batch=[_b(b) for b in batches], berkas=[_x(x) for x in berkas]))


@app.get("/api/batch")
def daftar_batch(q: Optional[str] = None, jenis: Optional[str] = None, status: Optional[str] = None,
                 halaman: int = 1, per_halaman: int = 20, db=Depends(get_db)):
    sel = select(Batch).order_by(Batch.id.desc())
    if jenis:
        sel = sel.where(Batch.jenis == jenis)
    if status:
        sel = sel.where(Batch.status == status)
    if q:
        sel = sel.join(Berkas, Berkas.batch_id == Batch.id).where(Berkas.nama_asli.ilike(f"%{q}%")).distinct()
    semua = db.scalars(sel).unique().all()
    mulai = (max(halaman, 1) - 1) * per_halaman
    return bersih(dict(total=len(semua), halaman=halaman, data=[_b(b) for b in semua[mulai:mulai + per_halaman]]))


@app.get("/api/batch/{batch_id}")
def satu_batch(batch_id: int, db=Depends(get_db)):
    b = db.get(Batch, batch_id)
    if not b:
        raise HTTPException(404, "Batch tidak ditemukan.")
    return bersih(_b(b))


@app.get("/api/batch/{batch_id}/masalah")
def masalah(batch_id: int, db=Depends(get_db)):
    rows = db.scalars(select(Masalah).where(Masalah.batch_id == batch_id).order_by(Masalah.id)).all()
    return [dict(berkas=m.berkas, baris=m.baris, pesan=m.pesan) for m in rows]


@app.get("/api/batch/{batch_id}/masalah.xlsx")
def masalah_excel(batch_id: int, db=Depends(get_db)):
    import io
    rows = db.scalars(select(Masalah).where(Masalah.batch_id == batch_id).order_by(Masalah.id)).all()
    df = pd.DataFrame([dict(File=m.berkas, Baris=m.baris, Alasan=m.pesan) for m in rows] or [dict(File="", Baris=None, Alasan="Tidak ada masalah validasi.")])
    buf = io.BytesIO(); df.to_excel(buf, index=False, sheet_name="Validasi")
    return Response(buf.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="validasi_batch_{batch_id}.xlsx"'})


@app.post("/api/batch/{batch_id}/konfirmasi")
def konfirmasi(batch_id: int, aksi: str = Form(...), db=Depends(get_db)):
    try:
        return bersih(_b(unggah.konfirmasi(db, batch_id, aksi)))
    except ValueError as e:
        raise HTTPException(400, str(e))


def _daftar(s):
    return [x for x in s.split(",") if x] if s else None


@app.get("/api/opsi-filter")
def opsi(db=Depends(get_db)):
    return bersih(R.opsi_filter(db))


@app.get("/api/ringkasan")
def ringkasan(dari: Optional[date] = None, sampai: Optional[date] = None, kelompok: str = "puskesmas",
              puskesmas: Optional[str] = None, db=Depends(get_db)):
    return bersih(R.ringkasan(db, dari, sampai, kelompok, _daftar(puskesmas)))


@app.get("/api/rekap")
def rekap(dari: Optional[date] = None, sampai: Optional[date] = None, kelompok: str = "puskesmas",
          puskesmas: Optional[str] = None, db=Depends(get_db)):
    d, bulan = R.rekap(db, dari, sampai, kelompok, _daftar(puskesmas))
    return bersih(dict(bulan_target=bulan, data=d.astype(object).where(d.notna(), None).to_dict("records")))


@app.get("/api/tren")
def tren(indikator: str, dari: Optional[date] = None, sampai: Optional[date] = None, puskesmas: Optional[str] = None,
         per: str = "bulan", db=Depends(get_db)):
    return bersih(R.tren(db, indikator, dari, sampai, _daftar(puskesmas), per))


@app.get("/api/tren-puskesmas")
def tren_puskesmas(indikator: str = "penemuan", dari: Optional[date] = None, sampai: Optional[date] = None,
                   puskesmas: Optional[str] = None, kumulatif: bool = True, db=Depends(get_db)):
    return bersih(R.tren_puskesmas(db, indikator, dari, sampai, _daftar(puskesmas), kumulatif))


@app.get("/api/sukses-rate")
def sukses_rate(puskesmas: Optional[str] = None, db=Depends(get_db)):
    return bersih(R.sukses_rate(db, _daftar(puskesmas)))


@app.get("/api/tpt")
def tpt(puskesmas: Optional[str] = None, db=Depends(get_db)):
    return bersih(R.tpt(db, _daftar(puskesmas)))


@app.get("/api/verifikasi-zoom")
def verifikasi(db=Depends(get_db)):
    return bersih(R.bandingkan_zoom(db))


@app.get("/api/unduh/rekap.xlsx")
def unduh_rekap(dari: Optional[date] = None, sampai: Optional[date] = None, kelompok: str = "puskesmas",
                puskesmas: Optional[str] = None, db=Depends(get_db)):
    isi = R.ke_excel(db, dari, sampai, kelompok, _daftar(puskesmas))
    return Response(isi, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="rekap_tbc_sragen.xlsx"'})


@app.get("/api/database/ringkasan")
def info_database(db=Depends(get_db)):
    """Ringkasan isi database untuk halaman Database (tanpa data pasien)."""
    from .models import Fakta, Faskes, RekapHistoris, Target
    n = lambda m: db.scalar(select(func.count()).select_from(m))
    per_jenis = [dict(jenis=j, nama=NAMA_JENIS.get(j, j), baris_agregat=c, batch_aktif=a)
                 for j, c, a in db.execute(select(Fakta.jenis, func.count(), func.count(func.distinct(Fakta.batch_id)))
                                           .join(Batch, Batch.id == Fakta.batch_id).where(Batch.aktif.is_(True)).group_by(Fakta.jenis))]
    return bersih(dict(batch=n(Batch), batch_aktif=db.scalar(select(func.count()).select_from(Batch).where(Batch.aktif.is_(True))),
                       fakta=n(Fakta), faskes=n(Faskes), target=n(Target), riwayat_lama=n(RekapHistoris), per_jenis=per_jenis))


def _cari_folder_halaman():
    """Temukan folder frontend (berisi index.html).

    Lokasi berkas berbeda antara dijalankan lokal (folder proyek) dan di server serverless
    (berkas dikemas ke folder fungsi), jadi beberapa kandidat dicoba berurutan sebelum
    pencarian cadangan yang lebih dangkal.
    """
    kandidat = []
    diminta = os.getenv("FRONTEND_DIR", "").strip()
    if diminta:
        kandidat.append(Path(diminta))
    akar = [Path(__file__).resolve().parent, Path(__file__).resolve().parent.parent,
            Path.cwd(), config.BASE, Path("/var/task")]
    for a in akar:
        for nama in ("frontend", "public", "static", "api/frontend", "api/public"):
            kandidat.append(a / nama)
    for k in kandidat:
        try:
            if (k / "index.html").is_file():
                return k.resolve()
        except OSError:
            continue
    for a in akar:   # cadangan: cari index.html maksimal 3 tingkat di bawah tiap akar
        for pola in ("*/index.html", "*/*/index.html", "*/*/*/index.html"):
            try:
                for f in a.glob(pola):
                    if f.parent.name in ("frontend", "public", "static"):
                        return f.parent.resolve()
            except OSError:
                continue
    return None


_fe = _cari_folder_halaman()
if _fe is not None:
    _folder_halaman = _fe

    @app.get("/", include_in_schema=False)
    def _halaman_depan():
        """Halaman utama dashboard (bukan JSON) supaya alamat utama langsung menampilkan UI."""
        return FileResponse(_folder_halaman / "index.html", media_type="text/html")

    # seluruh berkas frontend (gaya, skrip, gambar) dilayani dari folder yang sama
    app.mount("/", StaticFiles(directory=str(_folder_halaman), html=True), name="frontend")
else:
    logging.getLogger("tbc").warning(
        "Folder frontend tidak ditemukan; halaman utama tidak akan tampil. "
        "Set variabel lingkungan FRONTEND_DIR bila berkas berada di lokasi lain."
    )
