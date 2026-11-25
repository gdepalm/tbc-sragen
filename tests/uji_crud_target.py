"""Uji CRUD Target Puskesmas. Memakai database sementara, database asli TIDAK tersentuh.

Cara menjalankan (dari folder proyek):  python tests/uji_crud_target.py
"""
import os
import sys
import tempfile
from pathlib import Path

tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{Path(tmp) / 'uji.db'}"
os.environ["UPLOAD_DIR"] = str(Path(tmp) / "upload")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

gagal = []


def cek(nama, kondisi, info=""):
    print(("  OK    " if kondisi else "  GAGAL ") + nama + (f"  [{info}]" if info and not kondisi else ""))
    if not kondisi:
        gagal.append(nama)


with TestClient(app) as c:
    # READ
    r = c.get("/api/target")
    cek("Read: daftar awal 25 puskesmas", r.status_code == 200 and len(r.json()) == 25, r.text[:80])
    r = c.get("/api/target", params={"q": "tanon"})
    cek("Read: pencarian 'tanon' menemukan 2", len(r.json()) == 2, r.text[:80])
    cek("Read: pencarian tanpa hasil kosong", c.get("/api/target", params={"q": "zzzz"}).json() == [])

    # CREATE
    data = dict(nama="Puskesmas Uji Coba", terduga_tahunan=100, penemuan_tahunan=20, tb_anak_tahunan=5)
    r = c.post("/api/target", json=data)
    cek("Create: berhasil (201)", r.status_code == 201, r.text[:100])
    kunci = r.json().get("key")
    cek("Create: key otomatis 'ujicoba'", kunci == "ujicoba", str(kunci))
    cek("Create: muncul di daftar", len(c.get("/api/target").json()) == 26)
    r = c.post("/api/target", json=dict(data, nama="uji coba"))
    cek("Create: nama sama ditolak (409)", r.status_code == 409, r.text[:100])
    cek("Create: nama kosong ditolak (400)", c.post("/api/target", json=dict(data, nama="  ")).status_code == 400)
    cek("Create: hanya kata 'Puskesmas' ditolak", c.post("/api/target", json=dict(data, nama="Puskesmas ")).status_code == 400)
    cek("Create: angka kosong ditolak", c.post("/api/target", json=dict(data, nama="X1", terduga_tahunan=None)).status_code == 400)
    cek("Create: angka negatif ditolak", c.post("/api/target", json=dict(data, nama="X2", penemuan_tahunan=-1)).status_code == 400)
    cek("Create: teks bukan angka ditolak (422)", c.post("/api/target", json=dict(data, nama="X3", tb_anak_tahunan="abc")).status_code == 422)
    cek("Create: data gagal tidak tersimpan", len(c.get("/api/target").json()) == 26)

    # opsi filter ikut terbarui (dipakai filter dashboard)
    opsi = c.get("/api/opsi-filter").json()
    cek("Filter dashboard memuat puskesmas baru", any(p["key"] == kunci for p in opsi["puskesmas"]))

    # UPDATE
    r = c.put(f"/api/target/{kunci}", json=dict(nama="Uji Coba Baru", terduga_tahunan=150, penemuan_tahunan=30, tb_anak_tahunan=7))
    cek("Update: berhasil", r.status_code == 200 and r.json()["terduga_tahunan"] == 150, r.text[:100])
    g = c.get(f"/api/target/{kunci}").json()
    cek("Update: tersimpan di database", g["nama"] == "Puskesmas Uji Coba Baru" and g["penemuan_tahunan"] == 30)
    cek("Update: key tidak berubah", g["key"] == kunci)
    cek("Update: nilai tidak valid ditolak", c.put(f"/api/target/{kunci}", json=dict(nama="A", terduga_tahunan=-5, penemuan_tahunan=1, tb_anak_tahunan=1)).status_code == 400)
    cek("Update: key tidak ada (404)", c.put("/api/target/tidakada", json=data).status_code == 404)

    # dashboard tetap jalan setelah ada perubahan
    cek("Dashboard /api/rekap tetap berjalan", c.get("/api/rekap").status_code == 200)
    cek("Dashboard /api/ringkasan tetap berjalan", c.get("/api/ringkasan").status_code == 200)

    # DELETE
    r = c.delete(f"/api/target/{kunci}")
    cek("Delete: berhasil", r.status_code == 200, r.text[:100])
    cek("Delete: hilang dari daftar", len(c.get("/api/target").json()) == 25)
    cek("Delete: ulangi -> 404", c.delete(f"/api/target/{kunci}").status_code == 404)
    cek("Halaman utama (frontend) tetap terbuka", c.get("/").status_code == 200)

print()
print("SEMUA UJI LULUS" if not gagal else f"{len(gagal)} UJI GAGAL: {gagal}")
sys.exit(1 if gagal else 0)
