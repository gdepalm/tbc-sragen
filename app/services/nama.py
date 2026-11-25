"""Menyeragamkan nama fasyankes antar file SITB."""
import re

ALIAS = {"karangmalangkabsragen": "karangmalang", "sambirejosragen": "sambirejo",
         "sembungmacani": "sambungmacani", "sembungmacanii": "sambungmacanii",
         "gemolongii": "gemolong"}


def key(nama) -> str:
    k = re.sub(r"[^a-z0-9]", "", str(nama).lower().replace("puskesmas", ""))
    return ALIAS.get(k, k)


def kelompok(nama) -> str:
    n = str(nama).strip().lower()
    if n.startswith("puskesmas"):
        return "puskesmas"
    if "lapas" in n:
        return "lapas"
    if n.startswith(("rs ", "rsu", "rsia")) or "rumah sakit" in n:
        return "rs"
    if "klinik" in n or "tpmd" in n or "dokter" in n:
        return "klinik"
    return "lainnya"
