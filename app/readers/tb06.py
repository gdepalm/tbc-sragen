from .umum import Hasil, baca_periode, buka, cari_kolom, g, head_lembar, ke_tanggal, teks, wajib, jumlah_baris_perkiraan

# Aturan indikator (dicocokkan dengan pivot di file TB.06, Data Zoom 7 Okt 2026, dan slide Rakor 8 Okt 2026):
#  terduga   = Status Diagnosis "Sesuai standar"
#  penemuan  = kolom "Terkonfirmasi TBC" terisi (TBC SO / TBC RO)
#  enrolment = penemuan yang SUDAH memulai pengobatan:
#              Tindak Lanjut "Akan diobati/Dirujuk" DAN "Tanggal Mulai Pengobatan TBC" terisi,
#              ATAU Tindak Lanjut "Melanjutkan pengobatan sebelumnya".
#              (Sama dengan kolom bantu "Inisiasi pengobatan = Sudah Pengobatan" buatan petugas.)
#  tb_anak   = penemuan dengan umur <= 14 tahun


def _angka(v):
    if isinstance(v, (int, float)):
        return v
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def baca(path, sheet, progres=None):
    ws = buka(path)[sheet]
    head = head_lembar(ws)
    c = wajib(head, {"no": ("No. Urut", True, 6), "tgl": ("Tanggal Didaftar", False, 6), "status": ("Status Diagnosis", False, 6),
                     "umur": ("Umur (Tahun)", False, 6), "faskes": ("Nama Fasyankes", True, 10),
                     "konf": ("Terkonfirmasi TBC", False, 6), "tl": ("Tindak Lanjut", True, 6)})
    j_mulai = cari_kolom(head, "Tanggal Mulai Pengobatan", False, 6)   # opsional (file lama mungkin tidak punya)
    h = Hasil("tb06", sheet, baca_periode(head))
    total = jumlah_baris_perkiraan(ws)
    for i, r in enumerate(ws.iter_rows(values_only=True), start=1):
        if i < 13 or _angka(g(r, c["no"])) is None:
            continue
        h.baris += 1
        faskes, tgl = teks(g(r, c["faskes"])), ke_tanggal(g(r, c["tgl"]))
        if not faskes:
            h.tolak(i, "Nama fasyankes kosong"); continue
        if tgl is None:
            h.tolak(i, "Tanggal didaftar kosong atau formatnya tidak dikenali"); continue
        f = h.fakta
        if teks(g(r, c["status"])).lower() == "sesuai standar":
            f[(tgl, faskes, "terduga")] += 1
        if teks(g(r, c["konf"])):
            f[(tgl, faskes, "penemuan")] += 1
            tl = teks(g(r, c["tl"])).lower()
            mulai = teks(g(r, j_mulai)) if j_mulai is not None else "ada"
            if (tl.startswith("akan diobati") and mulai) or tl.startswith("melanjutkan"):
                f[(tgl, faskes, "enrolment")] += 1
            u = _angka(g(r, c["umur"]))
            if u is not None and u <= 14:
                f[(tgl, faskes, "tb_anak")] += 1
        if progres and h.baris % 2000 == 0:
            progres(h.baris, total)
    return h
