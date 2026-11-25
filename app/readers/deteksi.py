"""Mengenali jenis laporan dari ISI file (judul laporan di dalam sheet), bukan hanya nama file."""
import re
from dataclasses import dataclass
from typing import Optional

from .umum import FormatTidakDikenali, baca_periode, buka, head_lembar, teks, BULAN
from datetime import date

PENANDA = [  # (jenis, kata kunci judul laporan)
    ("skrining", "LAPORAN INDIVIDU HASIL SKRINING"),
    ("tb06", "REGISTER TERDUGA TBC"),
    ("tb03so", "REGISTER PASIEN TBC"),
    ("tb16rk", "INVESTIGASI KONTAK"),
    ("tb15", "PENCEGAHAN TBC"),
]
NAMA_JENIS = {"skrining": "Laporan Skrining", "tb06": "TB.06 (Register Terduga TBC)",
              "tb03so": "TB.03SO (Register Pasien TBC)", "tb16rk": "TB.16RK (Investigasi Kontak)",
              "tb15": "TB.15 (Pengobatan Pencegahan TBC)", "zoom": "Data Zoom (Capaian Program)"}


@dataclass
class Deteksi:
    jenis: str
    sheet: str
    periode: Optional[tuple]


def deteksi(path) -> Deteksi:
    wb = buka(path)
    nama_sheet = [s.title for s in wb.worksheets]
    if any(s.strip().upper() == "CAPAIAN PROGRAM" for s in nama_sheet):
        sh = next(s for s in nama_sheet if s.strip().upper() == "CAPAIAN PROGRAM")
        head = head_lembar(wb[sh], 3)
        m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", " ".join(teks(v) for r in head for v in r if v))
        per = None
        if m and m.group(2).lower() in BULAN:
            d = date(int(m.group(3)), BULAN[m.group(2).lower()], int(m.group(1)))
            per = (f"Tarikan {d.day} {m.group(2).title()} {d.year}", d, d)
        return Deteksi("zoom", sh, per)
    for ws in wb.worksheets:
        head = head_lembar(ws, 14)
        judul = " ".join(teks(v).upper() for r in head[:9] for v in r if isinstance(v, str))
        for jenis, kunci in PENANDA:
            if kunci in judul:
                return Deteksi(jenis, ws.title, baca_periode(head))
    raise FormatTidakDikenali("Jenis laporan tidak dikenali. Laporan yang didukung: " +
                              "; ".join(NAMA_JENIS.values()) + ". Sheet di file ini: " + ", ".join(nama_sheet) + ".")
