"""Data Zoom: angka rekap buatan manual (pembanding). Disimpan apa adanya, tidak dihitung ulang."""
import re
from datetime import date

from .umum import BULAN, FormatTidakDikenali, Hasil, angka, buka, g, head_lembar, teks

CAPAIAN = ["zoom_skrining", "zoom_terduga", "zoom_penemuan", "zoom_enrolment", "zoom_tb_anak", "zoom_diobati",
           "zoom_status_hiv", "zoom_status_dm"]
TSR = ["zoom_tsr_total", "zoom_tsr_gagal", "zoom_tsr_meninggal", "zoom_tsr_lengkap", "zoom_tsr_ltfu",
       "zoom_tsr_sembuh", "zoom_tsr_tidak_evaluasi"]


def _tgl(head):
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", " ".join(teks(v) for r in head for v in r if v))
    if m and m.group(2).lower() in BULAN:
        return date(int(m.group(3)), BULAN[m.group(2).lower()], int(m.group(1)))
    return None


def baca(path, sheet, progres=None):
    wb = buka(path)
    ws = wb[sheet]
    head = list(ws.iter_rows(max_row=3, values_only=True))
    tgl = _tgl(head)
    if tgl is None:
        raise FormatTidakDikenali("Tanggal tarikan pada judul sheet CAPAIAN PROGRAM tidak terbaca.")
    h = Hasil("zoom", sheet, (f"Tarikan {tgl.day}/{tgl.month}/{tgl.year}", tgl, tgl))
    for r in ws.iter_rows(min_row=3, values_only=True):
        nama = teks(g(r, 0))
        if not nama.lower().startswith("puskesmas"):
            continue
        h.baris += 1
        for k, ind in enumerate(CAPAIAN):
            h.fakta[(tgl, nama, ind)] += angka(g(r, 1 + k))
    sh_tsr = next((s.title for s in wb.worksheets if s.title.strip().upper().startswith("SUKSES RATE")), None)
    if sh_tsr:
        w2 = wb[sh_tsr]
        t2 = _tgl(list(w2.iter_rows(max_row=3, values_only=True))) or tgl
        for r in w2.iter_rows(min_row=3, values_only=True):
            nama = teks(g(r, 0))
            if nama.lower().startswith("puskesmas"):
                for k, ind in enumerate(TSR):
                    h.fakta[(t2, nama, ind)] += angka(g(r, 1 + k))
    return h
