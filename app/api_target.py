"""CRUD Target Puskesmas (tabel target_puskesmas).

Tabel ini berisi angka target tahunan per puskesmas yang dipakai dashboard untuk
menghitung persentase capaian. Tidak ada data pasien di sini.

Catatan: kolom `key` (kunci pencocokan dengan laporan SITB) dibuat otomatis dari nama
puskesmas dan TIDAK diubah saat edit, supaya data laporan yang sudah masuk tetap cocok.
"""
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from .db import get_db
from .models import Target
from .services.nama import key as kunci_faskes

router = APIRouter(prefix="/api/target", tags=["Target Puskesmas"])


class TargetIn(BaseModel):
    nama: Optional[str] = None
    terduga_tahunan: Optional[float] = None
    penemuan_tahunan: Optional[float] = None
    tb_anak_tahunan: Optional[float] = None


def _baris(t: Target):
    return dict(key=t.key, nama=t.nama, terduga_tahunan=t.terduga_tahunan,
                penemuan_tahunan=t.penemuan_tahunan, tb_anak_tahunan=t.tb_anak_tahunan)


def _periksa(p: TargetIn):
    """Validasi isian. Mengembalikan (nama_lengkap, terduga, penemuan, tb_anak)."""
    inti = re.sub(r"^\s*puskesmas\s+", "", (p.nama or "").strip(), flags=re.I).strip()
    if not inti:
        raise HTTPException(400, "Nama puskesmas wajib diisi.")
    if len(inti) > 100:
        raise HTTPException(400, "Nama puskesmas terlalu panjang (maksimal 100 karakter).")
    angka = []
    for label, v in (("Target terduga", p.terduga_tahunan), ("Target penemuan", p.penemuan_tahunan),
                     ("Target TB anak", p.tb_anak_tahunan)):
        if v is None:
            raise HTTPException(400, f"{label} wajib diisi.")
        if v != v or v < 0 or v > 1_000_000:
            raise HTTPException(400, f"{label} harus berupa angka 0 sampai 1.000.000.")
        angka.append(float(v))
    return ("Puskesmas " + inti, *angka)


@router.get("")
def daftar(q: Optional[str] = None, db=Depends(get_db)):
    sel = select(Target).order_by(Target.nama)
    if q and q.strip():
        sel = sel.where(Target.nama.ilike(f"%{q.strip()}%"))
    return [_baris(t) for t in db.scalars(sel)]


@router.post("", status_code=201)
def tambah(p: TargetIn, db=Depends(get_db)):
    nama, td, pn, ta = _periksa(p)
    k = kunci_faskes(nama)
    if not k:
        raise HTTPException(400, "Nama puskesmas tidak valid.")
    if db.get(Target, k):
        raise HTTPException(409, f"{nama} sudah ada di daftar target.")
    t = Target(key=k, nama=nama, terduga_tahunan=td, penemuan_tahunan=pn, tb_anak_tahunan=ta)
    db.add(t)
    db.commit()
    return _baris(t)


@router.get("/{key}")
def satu(key: str, db=Depends(get_db)):
    t = db.get(Target, key)
    if not t:
        raise HTTPException(404, "Data target tidak ditemukan.")
    return _baris(t)


@router.put("/{key}")
def ubah(key: str, p: TargetIn, db=Depends(get_db)):
    t = db.get(Target, key)
    if not t:
        raise HTTPException(404, "Data target tidak ditemukan.")
    t.nama, t.terduga_tahunan, t.penemuan_tahunan, t.tb_anak_tahunan = _periksa(p)
    db.commit()
    return _baris(t)


@router.delete("/{key}")
def hapus(key: str, db=Depends(get_db)):
    t = db.get(Target, key)
    if not t:
        raise HTTPException(404, "Data target tidak ditemukan.")
    nama = t.nama
    db.delete(t)
    db.commit()
    return dict(terhapus=key, nama=nama)
