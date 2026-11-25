"""Halaman Contact Us: baca & ubah informasi kontak pengelola dashboard (tabel `kontak`)."""
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .db import get_db
from .models import Kontak

router = APIRouter(prefix="/api/kontak", tags=["Contact Us"])

# (kunci, nilai bawaan, panjang maksimal)
KOLOM = [
    ("instansi", "Dinas Kesehatan Kabupaten Sragen", 150),
    ("unit", "Bidang Pencegahan dan Pengendalian Penyakit (P2P)", 150),
    ("pengelola", "", 120),
    ("email", "", 120),
    ("telepon", "", 40),
    ("alamat", "", 300),
    ("website", "", 200),
    ("jam_layanan", "Senin - Jumat, 07.30 - 15.30 WIB", 120),
]


class KontakIn(BaseModel):
    instansi: Optional[str] = None
    unit: Optional[str] = None
    pengelola: Optional[str] = None
    email: Optional[str] = None
    telepon: Optional[str] = None
    alamat: Optional[str] = None
    website: Optional[str] = None
    jam_layanan: Optional[str] = None


def _semua(db):
    simpan = {k.kunci: k.nilai for k in db.query(Kontak).all()}
    return {k: (simpan[k] if k in simpan and simpan[k] is not None else bawaan) for k, bawaan, _ in KOLOM}


@router.get("")
def baca(db=Depends(get_db)):
    return _semua(db)


@router.put("")
def ubah(p: KontakIn, db=Depends(get_db)):
    data = p.model_dump()
    for k, _, maks in KOLOM:
        if data.get(k) is None:      # kolom yang tidak dikirim tidak diubah
            continue
        v = " ".join(str(data.get(k)).split())
        if len(v) > maks:
            raise HTTPException(400, f"Isian '{k}' terlalu panjang (maksimal {maks} karakter).")
        if k == "email" and v and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
            raise HTTPException(400, "Format email tidak valid. Contoh: p2p.dinkes@sragenkab.go.id")
        if k == "telepon" and v and not re.fullmatch(r"[0-9+()\-\s]{6,}", v):
            raise HTTPException(400, "Nomor telepon hanya boleh berisi angka, spasi, +, -, atau tanda kurung.")
        if k == "website" and v and not re.match(r"^https?://", v, re.I):
            v = "https://" + v
        baris = db.get(Kontak, k)
        if baris:
            baris.nilai = v
        else:
            db.add(Kontak(kunci=k, nilai=v))
    db.commit()
    return _semua(db)
