from .umum import FormatTidakDikenali, Hasil, angka, baca_periode, buka, g, head_lembar, teks

KATEGORI = ["anak_lt5", "anak_5_14", "dewasa_ge15", "risiko_lain"]
HASIL = ["lengkap", "gagal", "meninggal", "putus", "tidak_evaluasi"]


def baca(path, sheet, progres=None):
    ws = buka(path)[sheet]
    head = head_lembar(ws, 16)
    judul = " ".join(teks(v).lower() for r in head for v in r if v)
    if "hasil akhir" not in judul or "puskesmas" in judul and False:
        raise FormatTidakDikenali("Susunan kolom TB.15 tidak sesuai yang diharapkan (tidak ada 'Hasil Akhir').")
    h = Hasil("tb15", sheet, baca_periode(head))
    if h.periode is None:
        raise FormatTidakDikenali("Periode laporan TB.15 tidak terbaca dari judul file.")
    tgl = h.periode[2]
    for i, r in enumerate(ws.iter_rows(values_only=True), start=1):
        if not (isinstance(g(r, 2), int) and isinstance(g(r, 3), str)):
            continue
        h.baris += 1
        faskes = teks(g(r, 3))
        for k, kat in enumerate(KATEGORI):
            h.fakta[(tgl, faskes, f"tpt_{kat}")] += angka(g(r, 4 + k))
            for m, hs in enumerate(HASIL):
                h.fakta[(tgl, faskes, f"tpt_{hs}_{kat}")] += angka(g(r, 8 + 4 * m + k))
    return h
