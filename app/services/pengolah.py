"""Pipeline: baca -> validasi -> gabung/deduplikasi -> hitung -> simpan -> aktifkan."""
import logging
import os
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from sqlalchemy import insert, select

from .. import config
from ..db import SessionLocal
from ..models import Batch, Berkas, Fakta, Faskes, Masalah
from ..readers import PEMBACA
from ..readers.umum import FormatTidakDikenali
from .nama import key as kunci, kelompok

log = logging.getLogger("tbc")
antrean = ThreadPoolExecutor(max_workers=1)  # satu pengolahan pada satu waktu agar server tidak kehabisan memori


def kirim(batch_id: int):
    antrean.submit(proses, batch_id)


def _ubah(batch_id, **kw):
    with SessionLocal() as db:
        b = db.get(Batch, batch_id)
        for k, v in kw.items():
            setattr(b, k, v)
        db.commit()


def proses(batch_id: int):
    with SessionLocal() as db:
        b = db.get(Batch, batch_id)
        berkas = list(db.scalars(select(Berkas).where(Berkas.batch_id == batch_id).order_by(Berkas.baris.desc())))
        jenis, mode = b.jenis, b.mode
        info = [(x.id, x.nama_asli, x.path, x.sheet) for x in berkas]
        b.status, b.progres, b.pesan = "diproses", 1, "Membaca file…"
        db.commit()
    try:
        fakta, masalah = Counter(), []
        dibaca = ditolak = ganda = berhasil = 0
        sidik_sebelumnya: set = set()
        for n, (bid, nama, path, sheet) in enumerate(info):
            def prog(baris, total, n=n):
                p = 1 + int(85 * (n + min(baris / total if total else 0.5, 0.99)) / len(info))
                _ubah(batch_id, progres=p, baris_dibaca=dibaca + baris)
            h = PEMBACA[jenis](path, sheet, prog)
            for no, pesan in h.masalah:
                masalah.append((nama, no, pesan))
            dibaca += h.baris
            ditolak += h.ditolak
            if jenis == "skrining":
                # Data yang sama persis yang sudah muncul di FILE LAIN dalam unggahan ini dibuang (bagian 2 & 3 ternyata
                # tumpang tindih dengan bagian 1). Data kembar di dalam satu file yang sama tetap dihitung.
                baru = set()
                for tgl, unit, sidik, terduga, konf in h.baris_skrining:
                    if sidik in sidik_sebelumnya:
                        ganda += 1
                        continue
                    baru.add(sidik)
                    berhasil += 1
                    fakta[(tgl, unit, "skrining")] += 1
                    if terduga:
                        fakta[(tgl, unit, "skrining_terduga")] += 1
                    if konf:
                        fakta[(tgl, unit, "skrining_terkonfirmasi")] += 1
                sidik_sebelumnya |= baru
                h.baris_skrining.clear()
            else:
                berhasil += h.baris - h.ditolak
                fakta.update(h.fakta)
            with SessionLocal() as db:
                x = db.get(Berkas, bid); x.baris, x.status = h.baris, "selesai"; db.commit()
        _ubah(batch_id, progres=90, pesan="Menyimpan ke database…", baris_dibaca=dibaca)
        _simpan(batch_id, jenis, mode, fakta, masalah, dibaca, berhasil, ditolak, ganda)
    except FormatTidakDikenali as e:
        _gagal(batch_id, str(e))
    except Exception as e:  # jangan tulis isi baris ke log (bisa mengandung data pasien)
        log.error("Pengolahan batch %s gagal: %s", batch_id, type(e).__name__)
        _gagal(batch_id, f"Terjadi kesalahan saat mengolah file ({type(e).__name__}). Coba unggah ulang; jika berulang, hubungi pengembang.")
    finally:
        if not config.SIMPAN_BERKAS_ASLI:
            for _, _, path, _ in info:
                try:
                    os.remove(path)
                except OSError:
                    pass


def _gagal(batch_id, pesan):
    with SessionLocal() as db:
        b = db.get(Batch, batch_id)
        b.status, b.pesan, b.aktif, b.selesai_pada = "gagal", pesan, False, datetime.now()
        for x in db.scalars(select(Berkas).where(Berkas.batch_id == batch_id)):
            x.status, x.pesan = "gagal", pesan
        db.commit()


def _simpan(batch_id, jenis, mode, fakta, masalah, dibaca, berhasil, ditolak, ganda):
    with SessionLocal() as db:
        b = db.get(Batch, batch_id)
        baris = [dict(batch_id=batch_id, jenis=jenis, tanggal=t, faskes_key=kunci(n), indikator=i, nilai=v)
                 for (t, n, i), v in fakta.items()]
        nama_faskes = {kunci(n): n for (_, n, _) in fakta}
        for k, n in nama_faskes.items():
            if db.get(Faskes, k) is None:
                db.add(Faskes(key=k, nama=n, kelompok=kelompok(n)))
        for i in range(0, len(baris), 5000):
            db.execute(insert(Fakta), baris[i:i + 5000])
        for nama, no, pesan in masalah[:2000]:
            db.add(Masalah(batch_id=batch_id, berkas=nama, baris=no, pesan=pesan[:300]))
        if mode == "ganti" and b.periode_awal:
            for lama in db.scalars(select(Batch).where(Batch.jenis == jenis, Batch.aktif.is_(True), Batch.id != batch_id)):
                if _tumpang(lama, b):
                    lama.aktif, lama.diganti_oleh = False, batch_id   # data lama TIDAK dihapus, hanya dinonaktifkan
        b.aktif, b.status, b.progres = True, "selesai", 100
        b.baris_dibaca, b.baris_berhasil, b.baris_ditolak, b.baris_ganda = dibaca, berhasil, ditolak, ganda
        b.selesai_pada = datetime.now()
        b.pesan = f"Selesai. {berhasil:,} baris berhasil, {ditolak:,} ditolak" + (f", {ganda:,} dibuang karena sama dengan file lain." if ganda else ".")
        db.commit()


def _tumpang(a, b):
    if not (a.periode_awal and a.periode_akhir and b.periode_awal and b.periode_akhir):
        return False
    return a.periode_awal <= b.periode_akhir and a.periode_akhir >= b.periode_awal
