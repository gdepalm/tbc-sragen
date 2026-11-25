"""Pemeriksaan hasil pemasangan aplikasi di server (production).

Pakai:  .venv\\Scripts\\python.exe tests\\periksa_produksi.py https://alamat-aplikasi
Tanpa argumen, memakai alamat produksi saat ini. Skrip ini hanya membaca (GET),
tidak mengubah data apa pun.

Yang diperiksa:
  A. halaman depan dan seluruh berkas frontend (harus 200, ukuran > 0, HTML dashboard)
  B. seluruh endpoint API (harus 200, memuat data dari database)
  C. rincian /api/kesehatan: sambungan database, folder halaman, folder unggahan
"""
import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://tbc-sragen-rosy.vercel.app"

HALAMAN = ["/", "/index.html", "/style.css", "/app.js", "/grafik_ppt.js",
           "/logo_dinkes.png", "/latar.png", "/latar2.jpg", "/vendor/chart.umd.js"]
API = ["/api/kesehatan", "/api/opsi-filter", "/api/ringkasan", "/api/rekap",
       "/api/tren-puskesmas", "/api/sukses-rate", "/api/tpt", "/api/database/ringkasan",
       "/api/batch", "/api/target", "/api/kontak", "/api/tren?indikator=penemuan",
       "/api/unduh/rekap.xlsx"]


def ambil(jalan):
    req = urllib.request.Request(BASE + jalan, headers={"User-Agent": "pemeriksa/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, r.headers.get("content-type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("content-type", ""), e.read()
    except Exception as e:
        return None, type(e).__name__, str(e).encode()


gagal = []

print("=" * 78)
print("A. HALAMAN & ASET FRONTEND")
print("=" * 78)
for u in HALAMAN:
    kode, tipe, isi = ambil(u)
    tanda = "OK " if kode == 200 and len(isi) > 0 else "GAGAL"
    if tanda == "GAGAL":
        gagal.append(u)
    print(f"  [{tanda}] {u:<24} HTTP {kode}  {tipe.split(';')[0]:<28} {len(isi):>8} byte")

kode, tipe, isi = ambil("/")
judul = b"<title>" in isi and b"TBC Monitoring Dashboard" in isi
json_salah = isi.lstrip().startswith(b'{"detail"')
print(f"  -> halaman depan berupa HTML dashboard: {judul} | JSON 'detail' (gejala lama) : {json_salah}")
if not judul or json_salah:
    gagal.append("/ (isi)")

print()
print("=" * 78)
print("B. ENDPOINT API (data dari PostgreSQL Supabase)")
print("=" * 78)
for u in API:
    kode, tipe, isi = ambil(u)
    tanda = "OK " if kode == 200 else "GAGAL"
    if kode != 200:
        gagal.append(u)
    contoh = isi[:60].decode("utf-8", "replace").replace("\n", " ")
    print(f"  [{tanda}] {u:<34} HTTP {kode}  {len(isi):>7} byte  {contoh}")

print()
print("=" * 78)
print("C. KESEHATAN LAYANAN")
print("=" * 78)
kode, _, isi = ambil("/api/kesehatan")
try:
    k = json.loads(isi)
    for nama in ("status", "halaman_depan", "folder_halaman", "jenis_database",
                 "database_terhubung", "jumlah_batch", "folder_unggahan", "pesan"):
        print(f"  {nama:<20}: {k.get(nama)}")
    if k.get("status") != "ok" or not k.get("database_terhubung"):
        gagal.append("kesehatan")
except Exception as e:
    print("  GAGAL membaca JSON kesehatan:", e, isi[:200])
    gagal.append("kesehatan")

print()
print("=" * 78)
print("HASIL:", "SEMUA PEMERIKSAAN LULUS" if not gagal else f"ADA MASALAH -> {gagal}")
print("=" * 78)