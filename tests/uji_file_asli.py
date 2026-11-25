"""Uji menyeluruh memakai file SITB asli. Jalankan: python tests/uji_file_asli.py <folder_excel>"""
import glob, os, sys, time, tempfile, json
folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "contoh_excel")
tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{tmp}/uji.db"
os.environ["UPLOAD_DIR"] = f"{tmp}/upload"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from app.main import app

LULUS, GAGAL = [], []
def cek(nama, kondisi, info=""):
    (LULUS if kondisi else GAGAL).append(nama)
    print(("  ✅ " if kondisi else "  ❌ ") + nama + (f"  [{info}]" if info else ""), flush=True)

def tunggu(c, ids, batas=900):
    t = time.time()
    while time.time() - t < batas:
        st = [c.get(f"/api/batch/{i}").json() for i in ids]
        if all(s["status"] in ("selesai", "gagal", "dibatalkan", "menunggu_konfirmasi") for s in st):
            return st
        time.sleep(3)
    raise TimeoutError

berkas = [f for f in sorted(glob.glob(f"{folder}/*.xlsx"))]
with TestClient(app) as c:
    print(f"1. Unggah {len(berkas)} file sekaligus"); t0 = time.time()
    r = c.post("/api/upload", files=[("files", (os.path.basename(f), open(f, "rb"))) for f in berkas], data={"mode": "tambah"}).json()
    jenis = sorted(b["jenis"] for b in r["batch"])
    cek("jenis laporan terdeteksi semua", jenis == ["skrining", "tb03so", "tb06", "tb15", "tb16rk", "zoom"], jenis)
    sk = [b for b in r["batch"] if b["jenis"] == "skrining"][0]
    cek("3 file skrining digabung dalam 1 batch", len(sk["berkas"]) == 3)
    st = tunggu(c, [b["id"] for b in r["batch"]])
    print(f"   selesai dalam {time.time()-t0:.0f} detik")
    for s in st:
        print(f"   - {s['nama_jenis']}: {s['status']} | dibaca {s['baris_dibaca']:,} berhasil {s['baris_berhasil']:,} ditolak {s['baris_ditolak']:,} ganda {s['baris_ganda']:,}")
    cek("semua batch selesai", all(s["status"] == "selesai" for s in st), [s["pesan"] for s in st if s["status"] != "selesai"])
    d = {s["jenis"]: s for s in st}
    cek("skrining: 111.534 baris unik, bagian 2 dan 3 tidak menggandakan", d["skrining"]["baris_berhasil"] == 111534, d["skrining"]["baris_berhasil"])
    cek("TB.06 terbaca 13.278 baris", d["tb06"]["baris_dibaca"] == 13278, d["tb06"]["baris_dibaca"])
    cek("TB.16RK terbaca 1.348 baris", d["tb16rk"]["baris_dibaca"] == 1348, d["tb16rk"]["baris_dibaca"])

    print("2. Akurasi vs Data Zoom (7 Okt 2026)")
    v = c.get("/api/verifikasi-zoom").json()
    for k, x in v["total"].items():
        print(f"   {k:10s} sistem={x['sistem']:.0f}  zoom={x['zoom']:.0f}")
    t = v["total"]
    for k in t:
        cek(f"total {k} = Data Zoom", t[k]["sistem"] == t[k]["zoom"], f"{t[k]['sistem']:.0f} vs {t[k]['zoom']:.0f}")
    cek("semua puskesmas sama persis dengan Data Zoom (tanpa selisih)", not v["baris"], v["baris"][:5])
    ts = c.get("/api/sukses-rate").json()
    cek("sukses rate kabupaten 94,5% (sama dengan slide)", ts["total"].get("pct") == 94.5, ts["total"])
    tp = c.get("/api/tpt").json()
    cek("TPT terbaca 25 puskesmas", len(tp["data"]) == 25, len(tp["data"]))
    print("   selisih per puskesmas:", [(b["puskesmas"], b["indikator"], b["selisih"]) for b in v["baris"]])

    print("3. Dashboard & filter")
    rk = c.get("/api/ringkasan").json()
    print("  ", json.dumps(rk["total"]), rk["persen"])
    cek("ringkasan memuat 25 puskesmas", rk["jumlah_faskes"] == 25, rk["jumlah_faskes"])
    jan = c.get("/api/ringkasan", params={"dari": "2026-01-01", "sampai": "2026-01-31"}).json()
    cek("filter rentang tanggal mengubah angka", jan["total"]["skrining"] < rk["total"]["skrining"], jan["total"]["skrining"])
    one = c.get("/api/ringkasan", params={"puskesmas": "gemolong"}).json()
    cek("filter puskesmas Gemolong: skrining 2.965 (sama dgn Zoom)", one["total"]["skrining"] == 2965, one["total"]["skrining"])
    tr = c.get("/api/tren", params={"indikator": "penemuan"}).json()
    cek("tren bulanan penemuan tersedia", len(tr) >= 9, len(tr))
    sem = c.get("/api/rekap", params={"kelompok": "semua"}).json()
    cek("kelompok 'semua' memuat klinik/RS juga", len(sem["data"]) > 25, len(sem["data"]))

    print("4. Download")
    x = c.get("/api/unduh/rekap.xlsx", params={"sampai": "2026-10-07"})
    import io, openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(x.content))
    cek("Rekap Excel bisa dibuka", x.status_code == 200 and "Rekap" in wb.sheetnames, wb.sheetnames)
    cek("Rekap Excel berisi 25 baris", wb["Rekap"].max_row == 26, wb["Rekap"].max_row)

    print("5. Deteksi duplikat & konflik periode")
    kecil = [f for f in berkas if "ZOOM" in f.upper() or "16RK" in f.upper()]
    r2 = c.post("/api/upload", files=[("files", (os.path.basename(f), open(f, "rb"))) for f in kecil]).json()
    cek("file yang sama persis ditolak sebagai duplikat", all(b["status"] == "duplikat" for b in r2["berkas"]), [b["status"] for b in r2["berkas"]])
    r3 = c.post("/api/upload", files=[("files", ("salah.txt", b"halo"))]).json()
    cek("file bukan Excel ditolak dengan alasan", r3["berkas"][0]["status"] == "ditolak", r3["berkas"][0]["pesan"])
    r4 = c.post("/api/upload", files=[("files", ("palsu.xlsx", b"bukan excel sungguhan"))]).json()
    cek("file palsu berekstensi .xlsx ditolak", r4["berkas"][0]["status"] == "ditolak", r4["berkas"][0]["pesan"])
    # salinan file TB.16RK dengan satu byte berbeda -> bukan duplikat -> periode bertumpuk -> minta konfirmasi
    p = [f for f in berkas if "16RK" in f.upper()][0]
    isi = open(p, "rb").read() + b"\0"
    r5 = c.post("/api/upload", files=[("files", ("ik_versi_baru.xlsx", isi))], data={"mode": "tambah"}).json()
    cek("periode bentrok -> menunggu konfirmasi (tidak otomatis menimpa)", r5["batch"][0]["status"] == "menunggu_konfirmasi", r5["batch"][0]["pesan"])
    bid = r5["batch"][0]["id"]
    b = c.post(f"/api/batch/{bid}/konfirmasi", data={"aksi": "batal"}).json()
    cek("batal -> tidak ada yang berubah", b["status"] == "dibatalkan")
    r6 = c.post("/api/upload", files=[("files", ("ik_versi_baru2.xlsx", isi))], data={"mode": "tambah"}).json()
    bid = r6["batch"][0]["id"]
    c.post(f"/api/batch/{bid}/konfirmasi", data={"aksi": "ganti"})
    s = tunggu(c, [bid])[0]
    cek("ganti -> selesai", s["status"] == "selesai", s["pesan"])
    semua = c.get("/api/batch").json()["data"]
    lama = [b for b in semua if b["jenis"] == "tb16rk" and not b["aktif"] and b["diganti_oleh"]]
    cek("data lama tetap tersimpan sebagai riwayat (tidak dihapus)", len(lama) == 1 and lama[0]["diganti_oleh"] == bid)
    rk2 = c.get("/api/ringkasan").json()
    cek("angka IK tidak berlipat ganda setelah ganti", rk2["total"]["ik_indeks"] == rk["total"]["ik_indeks"], rk2["total"]["ik_indeks"])
    cek("tidak ada file Excel asli tersisa di server", not [f for f in os.listdir(f"{tmp}/upload")], os.listdir(f"{tmp}/upload"))

# 6. Mulai ulang server: data harus tetap ada
with TestClient(app) as c2:
    rk3 = c2.get("/api/ringkasan").json()
    cek("data bertahan setelah server dimulai ulang", rk3["total"]["skrining"] == rk["total"]["skrining"] and rk3["total"]["skrining"] > 0)
print(f"\nHASIL: {len(LULUS)} lulus, {len(GAGAL)} gagal", GAGAL)
sys.exit(1 if GAGAL else 0)
