from .umum import Hasil, angka, baca_periode, buka, g, head_lembar, ke_tanggal, teks, wajib, jumlah_baris_perkiraan


def baca(path, sheet, progres=None):
    ws = buka(path)[sheet]
    head = head_lembar(ws, 14)
    c = wajib(head, {"no": ("No.", True, 6), "faskes": ("Nama Fasyankes", True, 7), "status": ("Status IK", True, 6),
                     "tgl": ("Tanggal Hasil Diagnosis", True, 6), "kontak": ("Total Kontak", True, 6),
                     "investigasi": ("Jumlah kontak diinvestigasi", False, 6),
                     "diperiksa": ("Jumlah kontak yang diperiksa", False, 6),
                     "sakit": ("Jumlah kontak yang sakit TBC", False, 6),
                     "eligible": ("Jumlah kontak yang memenuhi syarat TPT", False, 6),
                     "tpt": ("Jumlah Penerima TPT", True, 6)})
    h = Hasil("tb16rk", sheet, baca_periode(head))
    tgl_cadangan = h.periode[2] if h.periode else None
    total = jumlah_baris_perkiraan(ws)
    for i, r in enumerate(ws.iter_rows(values_only=True), start=1):
        if not isinstance(g(r, c["no"]), int):
            continue
        h.baris += 1
        faskes = teks(g(r, c["faskes"]))
        if not faskes:
            h.tolak(i, "Nama fasyankes kosong"); continue
        tgl = ke_tanggal(g(r, c["tgl"])) or tgl_cadangan
        if tgl is None:
            h.tolak(i, "Tanggal hasil diagnosis kosong dan periode laporan tidak terbaca"); continue
        f = h.fakta
        f[(tgl, faskes, "ik_indeks")] += 1
        if teks(g(r, c["status"])).lower() == "sudah ik":
            f[(tgl, faskes, "ik_sudah")] += 1
        f[(tgl, faskes, "ik_kontak_total")] += angka(g(r, c["kontak"]))
        f[(tgl, faskes, "ik_kontak_diinvestigasi")] += angka(g(r, c["investigasi"]))
        f[(tgl, faskes, "ik_kontak_diperiksa")] += angka(g(r, c["diperiksa"]))
        f[(tgl, faskes, "ik_kontak_sakit")] += angka(g(r, c["sakit"]))
        f[(tgl, faskes, "ik_kontak_eligible_tpt")] += angka(g(r, c["eligible"]))
        f[(tgl, faskes, "ik_tpt_terima")] += angka(g(r, c["tpt"])) + angka(g(r, c["tpt"] + 1))
        if progres and h.baris % 500 == 0:
            progres(h.baris, total)
    return h
