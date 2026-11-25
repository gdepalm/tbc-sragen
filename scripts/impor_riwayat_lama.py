"""Memasukkan riwayat dari database lama (tbc.db) ke database baru. Data lama TIDAK diubah/dihapus.
Pakai:  python scripts/impor_riwayat_lama.py  C:\\lokasi\\dashboard-tbc\\tbc.db"""
import sqlite3, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import date
from sqlalchemy import select, func
from app.db import SessionLocal, init_db
from app.models import RekapHistoris
from app.services.nama import key

if len(sys.argv) < 2:
    sys.exit("Isi lokasi file tbc.db lama. Contoh: python scripts/impor_riwayat_lama.py dashboard-tbc/tbc.db")
init_db()
lama = sqlite3.connect(sys.argv[1]); lama.row_factory = sqlite3.Row
baris = lama.execute("select * from rekap").fetchall()
with SessionLocal() as db:
    if db.scalar(select(func.count()).select_from(RekapHistoris)):
        sys.exit("Riwayat sudah pernah diimpor. Tidak ada yang diubah.")
    for r in baris:
        d = dict(r)
        db.add(RekapHistoris(tanggal=date.fromisoformat(str(d["tanggal"])[:10]), key=key(d.get("key") or d["puskesmas"]),
                             puskesmas=d["puskesmas"], skrining=d.get("skrining"), terduga=d.get("terduga"),
                             penemuan=d.get("penemuan"), enrolment=d.get("enrolment"), tb_anak=d.get("tb_anak"),
                             ik_total=d.get("ik_total"), ik_sudah=d.get("ik_sudah"), sumber=d.get("sumber") or "slide"))
    db.commit()
print(f"Selesai: {len(baris)} baris riwayat diimpor.")
