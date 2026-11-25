"""Penerimaan file: validasi, deteksi jenis, cek file sama, cek periode bentrok, lalu antre pengolahan."""
import os
from collections import defaultdict

from sqlalchemy import select

from .. import config
from ..models import Batch, Berkas
from ..readers import NAMA_JENIS, deteksi
from ..readers.umum import FormatTidakDikenali
from . import pengolah


def _hapus(path):
    try:
        os.remove(path)
    except OSError:
        pass


def terima(db, daftar, mode="tambah", konfirmasi_ganti=False):
    """daftar: [(nama_asli, path_sementara, ukuran, sha256, error_awal)]"""
    keluar, per_jenis = [], defaultdict(list)
    for nama, path, ukuran, sha, err in daftar:
        b = Berkas(nama_asli=nama, ukuran=ukuran, sha256=sha, path=path)
        db.add(b); db.flush()
        keluar.append(b)
        if err:
            b.status, b.pesan = "ditolak", err; _hapus(path); continue
        if not nama.lower().endswith((".xlsx", ".xlsm")):
            b.status = "ditolak"
            b.pesan = "Format file tidak didukung. Gunakan .xlsx (jika file .xls, buka di Excel lalu Simpan Sebagai .xlsx)."
            _hapus(path); continue
        sama = db.scalar(select(Berkas).join(Batch, Berkas.batch_id == Batch.id)
                         .where(Berkas.sha256 == sha, Batch.aktif.is_(True)).limit(1))
        if sama:
            b.status = "duplikat"
            b.pesan = f"File yang sama persis sudah diunggah pada {sama.dibuat:%d/%m/%Y %H:%M} dan masih aktif. Tidak diproses ulang."
            _hapus(path); continue
        try:
            d = deteksi(path)
        except FormatTidakDikenali as e:
            b.status, b.pesan = "tidak_dikenali", str(e); _hapus(path); continue
        b.jenis, b.sheet = d.jenis, d.sheet
        per_jenis[d.jenis].append((b, d))

    batches = []
    for jenis, items in per_jenis.items():
        kelompok_file = [items] if jenis == "skrining" else [[x] for x in items]  # skrining 1-3 digabung
        for grup in kelompok_file:
            per = grup[0][1].periode
            bt = Batch(jenis=jenis, mode="tambah", status="menunggu",
                       periode_label=per[0] if per else None, periode_awal=per[1] if per else None,
                       periode_akhir=per[2] if per else None)
            db.add(bt); db.flush()
            for b, _ in grup:
                b.batch_id = bt.id
            batches.append(bt)
            bentrok = []
            if bt.periode_awal:
                bentrok = [a for a in db.scalars(select(Batch).where(Batch.jenis == jenis, Batch.aktif.is_(True)))
                           if a.periode_awal and a.periode_awal <= bt.periode_akhir and a.periode_akhir >= bt.periode_awal]
            if mode == "batal":
                bt.status, bt.pesan = "dibatalkan", "Dibatalkan oleh pengguna."
                for b, _ in grup:
                    b.status = "dibatalkan"; _hapus(b.path)
            elif bentrok and not (mode == "ganti" and konfirmasi_ganti):
                bt.status = "menunggu_konfirmasi"
                a = bentrok[0]
                bt.pesan = (f"Sudah ada data {NAMA_JENIS[jenis]} aktif dengan periode yang bertumpuk "
                            f"({a.periode_label or 'tanpa label'}, diunggah {a.dibuat:%d/%m/%Y %H:%M}). "
                            "Pilih: GANTI data lama (data lama tetap tersimpan sebagai riwayat) atau BATALKAN.")
            else:
                bt.mode = "ganti" if (mode == "ganti" and bentrok) else "tambah"
    db.commit()
    for bt in batches:
        if bt.status == "menunggu":
            pengolah.kirim(bt.id)
    return batches, keluar


def konfirmasi(db, batch_id, aksi):
    bt = db.get(Batch, batch_id)
    if bt is None or bt.status != "menunggu_konfirmasi":
        raise ValueError("Batch tidak ditemukan atau tidak sedang menunggu konfirmasi.")
    if aksi == "batal":
        bt.status, bt.pesan = "dibatalkan", "Dibatalkan oleh pengguna."
        for b in bt.berkas:
            b.status = "dibatalkan"; _hapus(b.path)
    elif aksi == "ganti":
        bt.mode, bt.status = "ganti", "menunggu"
        db.commit(); pengolah.kirim(bt.id); return bt
    else:
        raise ValueError("Aksi harus 'ganti' atau 'batal'.")
    db.commit()
    return bt
