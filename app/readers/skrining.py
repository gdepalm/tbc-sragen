import hashlib
from .umum import Hasil, FormatTidakDikenali, baca_periode, buka, g, head_lembar, ke_tanggal, teks, wajib, jumlah_baris_perkiraan


def baca(path, sheet, progres=None):
    ws = buka(path)[sheet]
    head = head_lembar(ws)
    c = wajib(head, {"no": ("No", True, 6), "tgl": ("Tanggal Pelaksanaan", False, 6), "unit": ("Unit Pelaksana", True, 6),
                     "nama": ("Nama Peserta", True, 6), "nik": ("NIK", True, 6),
                     "terduga": ("Terduga TBC", True, 6), "konf": ("Terkonfirmasi TBC", True, 6)})
    h = Hasil("skrining", sheet, baca_periode(head))
    total = jumlah_baris_perkiraan(ws)
    for i, r in enumerate(ws.iter_rows(values_only=True), start=1):
        if not isinstance(g(r, c["no"]), int):
            continue
        h.baris += 1
        tgl, unit = ke_tanggal(g(r, c["tgl"])), teks(g(r, c["unit"]))
        if tgl is None:
            h.tolak(i, "Tanggal pelaksanaan kosong atau formatnya tidak dikenali"); continue
        if not unit:
            h.tolak(i, "Unit pelaksana kosong"); continue
        # sidik jari untuk mendeteksi data yang sama di file lain; TIDAK disimpan ke database
        sidik = hashlib.blake2b(f"{tgl}|{g(r, c['nik'])}|{g(r, c['nama'])}|{unit}".encode(), digest_size=8).digest()
        h.baris_skrining.append((tgl, unit, sidik, teks(g(r, c["terduga"])) == "Ya", bool(teks(g(r, c["konf"])))))
        if progres and h.baris % 5000 == 0:
            progres(h.baris, total)
    return h
