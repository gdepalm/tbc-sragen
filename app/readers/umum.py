"""Fungsi bantu pembacaan Excel SITB."""
import calendar
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import lru_cache
from typing import Optional

from openpyxl import load_workbook

BULAN = {"januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
         "september": 9, "oktober": 10, "november": 11, "desember": 12}


class FormatTidakDikenali(Exception):
    """Pesan sengaja ditulis dalam Bahasa Indonesia agar bisa langsung ditampilkan ke pengguna."""


@dataclass
class Hasil:
    jenis: str
    sheet: str
    periode: Optional[tuple] = None          # (label, tanggal_awal, tanggal_akhir)
    baris: int = 0                           # baris data yang dibaca
    ditolak: int = 0
    fakta: Counter = field(default_factory=Counter)   # (tanggal, nama_faskes, indikator) -> nilai
    masalah: list = field(default_factory=list)       # (nomor_baris, pesan)
    baris_skrining: list = field(default_factory=list)  # khusus skrining: (tgl, unit, hash, terduga, konf)

    def tolak(self, no_baris, pesan):
        self.ditolak += 1
        if len(self.masalah) < 500:
            self.masalah.append((no_baris, pesan))


def buka(path):
    try:
        return load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        raise FormatTidakDikenali("File tidak bisa dibuka sebagai Excel (.xlsx). File mungkin rusak atau bukan file Excel.") from e


def teks(v) -> str:
    return " ".join(str(v).split()) if v is not None else ""


def g(r, j):
    return r[j] if j is not None and j < len(r) else None


@lru_cache(maxsize=8192)
def _parse(s):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def ke_tanggal(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str) and v.strip():
        return _parse(v.strip())
    return None


def angka(v) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", ".")) if v not in (None, "") else 0.0
    except ValueError:
        return 0.0


def baca_periode(head):
    for r in head:
        for v in r:
            if isinstance(v, str):
                m = re.search(r"([A-Za-z]+)\s*-\s*([A-Za-z]+)\s+(\d{4})", v)
                if m and m.group(1).lower() in BULAN and m.group(2).lower() in BULAN:
                    b1, b2, th = BULAN[m.group(1).lower()], BULAN[m.group(2).lower()], int(m.group(3))
                    return (f"{m.group(1).title()} - {m.group(2).title()} {th}", date(th, b1, 1),
                            date(th, b2, calendar.monthrange(th, b2)[1]))
    return None


def cari_kolom(head, label, tepat=True, dari_baris=0, sampai_baris=None):
    """Cari nomor kolom (mulai 0) berdasarkan judul kolom. Mengembalikan None bila tidak ada."""
    t = label.lower()
    for r in head[dari_baris:sampai_baris]:
        for j, v in enumerate(r):
            if isinstance(v, str):
                s = teks(v).lower()
                if (s == t) if tepat else s.startswith(t):
                    return j
    return None


def wajib(head, spek):
    """spek: nama -> (judul, tepat, dari_baris). Gagal dengan pesan jelas jika ada kolom hilang."""
    hasil, hilang = {}, []
    for nama, (label, tepat, dari) in spek.items():
        j = cari_kolom(head, label, tepat, dari)
        if j is None:
            hilang.append(label)
        hasil[nama] = j
    if hilang:
        raise FormatTidakDikenali("Kolom yang diperlukan tidak ditemukan: " + "; ".join(hilang) +
                                  ". Pastikan file diunduh langsung dari SITB tanpa mengubah judul kolom.")
    return hasil


def slug(s) -> str:
    return re.sub(r"[^a-z0-9]+", "_", teks(s).lower()).strip("_") or "kosong"


def head_lembar(ws, n=16):
    return list(ws.iter_rows(max_row=n, values_only=True))


def jumlah_baris_perkiraan(ws):
    try:
        return int(ws.max_row or 0)
    except Exception:
        return 0
