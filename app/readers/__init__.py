from . import skrining, tb03so, tb06, tb15, tb16rk, zoom
from .deteksi import NAMA_JENIS, deteksi

PEMBACA = {"skrining": skrining.baca, "tb06": tb06.baca, "tb03so": tb03so.baca, "tb16rk": tb16rk.baca,
           "tb15": tb15.baca, "zoom": zoom.baca}
