"""TB.03SO (Register Pasien TBC SO).

Aturan (dicocokkan dengan pivot petugas di file TB.03SO, Data Zoom 7 Okt 2026, dan slide Rakor 8 Okt 2026):
  jumlah pasien TB (TB yang diobati) = semua baris pasien per fasyankes
  mengetahui status HIV = "Hasil Tes" pada Kolaborasi Kegiatan TBC-HIV berisi ODHIV / Bukan ODHIV,
                          ATAU kolom "Status HIV" berisi ODHIV / Bukan ODHIV
  mengetahui status DM  = kolom "DM" pada Kegiatan TBC-DM berisi Positif / Negatif
Catatan: dashboard versi sebelumnya hanya memakai kolom "Status HIV" sehingga angka HIV jauh terlalu kecil.
"""
from .umum import FormatTidakDikenali, Hasil, baca_periode, buka, cari_kolom, g, head_lembar, ke_tanggal, slug, teks, wajib, \
    jumlah_baris_perkiraan

HIV_TAHU = {"odhiv", "bukan odhiv", "positif", "negatif", "reaktif", "non reaktif", "nonreaktif"}
DM_TAHU = {"positif", "negatif"}


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
    c = wajib(head, {"no": ("No. Urut", True, 8), "faskes": ("Nama Fasyankes", True, 10),
                     "tgl": ("Tanggal Mulai Pengobatan", False, 8), "status_hiv": ("Status HIV", True, 8),
                     "akhir": ("Hasil Akhir Pengobatan", True, 8)})
    # sub-kolom: "Hasil Tes" (Kolaborasi TBC-HIV), "DM" (Kegiatan TBC-DM), "Hasil" (Hasil Akhir Pengobatan)
    j_kolab = cari_kolom(head, "Kolaborasi Kegiatan TBC-HIV", False, 8)
    j_tes = _cari_setelah(head, "Hasil Tes", j_kolab)
    j_keg_dm = cari_kolom(head, "Kegiatan TBC-DM", False, 8)
    j_dm = _cari_setelah(head, "DM", j_keg_dm)
    j_hasil = _cari_setelah(head, "Hasil", c["akhir"])
    if j_tes is None or j_dm is None or j_hasil is None:
        hilang = [n for n, j in (("Hasil Tes HIV", j_tes), ("DM (Kegiatan TBC-DM)", j_dm), ("Hasil (Hasil Akhir Pengobatan)", j_hasil)) if j is None]
        raise FormatTidakDikenali("Kolom TB.03SO tidak ditemukan: " + "; ".join(hilang) +
                                  ". Pastikan file diunduh langsung dari SITB tanpa mengubah judul kolom.")
    h = Hasil("tb03so", sheet, baca_periode(head))
    tgl_cadangan = h.periode[2] if h.periode else None
    tgl_kosong = 0
    total = jumlah_baris_perkiraan(ws)
    for i, r in enumerate(ws.iter_rows(values_only=True), start=1):
        if i < 15 or _angka(g(r, c["no"])) is None:
            continue
        h.baris += 1
        faskes = teks(g(r, c["faskes"]))
        if not faskes:
            h.tolak(i, "Nama fasyankes kosong"); continue
        tgl = ke_tanggal(g(r, c["tgl"]))
        if tgl is None:
            tgl = tgl_cadangan
            tgl_kosong += 1
            if tgl is None:
                h.tolak(i, "Tanggal mulai pengobatan kosong dan periode laporan tidak terbaca"); continue
        f = h.fakta
        f[(tgl, faskes, "tb03so_kasus")] += 1
        tes, st = teks(g(r, j_tes)).lower(), teks(g(r, c["status_hiv"])).lower()
        if tes in HIV_TAHU or st in HIV_TAHU:
            f[(tgl, faskes, "tb03so_hiv_tahu")] += 1
        if "odhiv" == tes or "odhiv" == st or tes in ("positif", "reaktif"):
            f[(tgl, faskes, "tb03so_hiv_positif")] += 1
        dm = teks(g(r, j_dm)).lower()
        if dm in DM_TAHU:
            f[(tgl, faskes, "tb03so_dm_tahu")] += 1
            if dm == "positif":
                f[(tgl, faskes, "tb03so_dm_positif")] += 1
        hasil = teks(g(r, j_hasil))
        if hasil:
            f[(tgl, faskes, "tb03so_hasil_" + slug(hasil))] += 1
        if progres and h.baris % 500 == 0:
            progres(h.baris, total)
    if tgl_kosong:
        h.masalah.append((None, f"{tgl_kosong} baris tanpa tanggal mulai pengobatan dihitung pada tanggal akhir periode."))
    return h


def _cari_setelah(head, label, mulai):
    """Cari sub-judul `label` (persis) pada baris sub-judul, di kolom >= `mulai` (kolom induknya)."""
    if mulai is None:
        return None
    t = label.lower()
    for r in head[8:]:
        for j, v in enumerate(r):
            if j >= mulai and isinstance(v, str) and teks(v).lower() == t:
                return j
    return None
