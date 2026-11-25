"""Perhitungan rekap dari database. Hanya memakai batch AKTIF.

Rumus disamakan dengan slide Rakor Kapus 8 Okt 2026 dan Data Zoom 7 Okt 2026:
  Skrining            : 1 baris laporan skrining = 1 orang (per Unit Pelaksana)
  Terduga TBC         : TB.06, Status Diagnosis "Sesuai standar"
  Penemuan (TC)       : TB.06, Terkonfirmasi TBC terisi
  Enrolment           : penemuan yang sudah memulai pengobatan; % = enrolment / penemuan (target 95%)
  TB anak             : penemuan umur <= 14 th
  Status HIV / DM     : TB.03SO; % = pasien tahu status / jumlah pasien TB (target 100%)
  Investigasi kontak  : TB.16RK; % = "Sudah IK" / jumlah kasus indeks
  Sukses rate         : (sembuh + pengobatan lengkap) / pasien diobati pada kohort (target 90%)
  Target s.d. bulan   : target tahunan / 12 x bulan data. Terduga dibulatkan ke puluhan (seperti slide),
                        penemuan & TB anak dibulatkan ke bilangan bulat.
"""
import io
import math
from datetime import date, datetime

import pandas as pd
from sqlalchemy import func, select

from ..models import Batch, Fakta, Faskes, Pengaturan, Target

IND = ["skrining", "terduga", "penemuan", "enrolment", "tb_anak", "ik_indeks", "ik_sudah",
       "tb03so_kasus", "tb03so_hiv_tahu", "tb03so_dm_tahu"]


def _pct(a, b):
    if a is None or b is None or (isinstance(b, float) and math.isnan(b)) or not b:
        return None
    return round(100 * a / b, 1)


def _bulat(x, ke=1):
    """Pembulatan seperti Excel (0,5 ke atas). ke=10 -> puluhan."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return math.floor(x / ke + 0.5) * ke


def _filter(q, dari=None, sampai=None):
    q = q.join(Batch, Batch.id == Fakta.batch_id).where(Batch.aktif.is_(True))
    if dari:
        q = q.where(Fakta.tanggal >= dari)
    if sampai:
        q = q.where(Fakta.tanggal <= sampai)
    return q


# Hanya laporan yang bertanggal per kejadian (skrining & TB.06) yang menentukan "data sampai tanggal".
# Tanggal di luar periode laporan (salah ketik) diabaikan.
JENIS_BERTANGGAL = ("skrining", "tb06")


def _sel_tgl(fn):
    q = _filter(select(fn(Fakta.tanggal)).where(Fakta.jenis.in_(JENIS_BERTANGGAL)))
    return q.where((Batch.periode_akhir.is_(None)) | (Fakta.tanggal <= Batch.periode_akhir))


def tanggal_data_terakhir(db):
    return db.scalar(_sel_tgl(func.max))


def opsi_filter(db):
    awal = db.scalar(_sel_tgl(func.min))
    akhir = tanggal_data_terakhir(db)
    pusk = [dict(key=k, nama=n) for k, n in db.execute(select(Target.key, Target.nama).order_by(Target.nama))]
    return dict(tanggal_awal=awal, tanggal_akhir=akhir, puskesmas=pusk,
                tahun=sorted({d.year for d in (awal, akhir) if d}),
                jenis_laporan=[j for (j,) in db.execute(_filter(select(Fakta.jenis).distinct()))])


def bulan_target(db, sampai=None):
    akhir = tanggal_data_terakhir(db)
    if sampai and akhir:
        return min(sampai, akhir).month
    return (sampai or akhir or date.today()).month


def _tabel_target(db):
    return pd.DataFrame([(t.key, t.nama, t.terduga_tahunan, t.penemuan_tahunan, t.tb_anak_tahunan) for t in db.scalars(select(Target))],
                        columns=["key", "nama_target", "t_terduga", "t_penemuan", "t_tb_anak"])


def rekap(db, dari=None, sampai=None, kelompok="puskesmas", puskesmas=None):
    """Satu baris per fasyankes. Target & persentase target hanya untuk puskesmas yang punya target."""
    q = _filter(select(Fakta.faskes_key, Fakta.indikator, func.sum(Fakta.nilai)).where(Fakta.indikator.in_(IND)), dari, sampai)
    q = q.group_by(Fakta.faskes_key, Fakta.indikator)
    df = pd.DataFrame(db.execute(q).all(), columns=["key", "ind", "nilai"])
    if len(df):
        p = df.pivot_table(index="key", columns="ind", values="nilai", aggfunc="sum").reindex(columns=IND).fillna(0)
    else:
        p = pd.DataFrame(columns=IND)
    p.index.name = "key"
    p = p.reset_index()
    fk = pd.DataFrame(db.execute(select(Faskes.key, Faskes.nama, Faskes.kelompok)).all(), columns=["key", "nama", "kelompok"])
    tg = _tabel_target(db)
    d = p.merge(fk, on="key", how="left")
    # puskesmas yang punya target selalu tampil (meskipun angkanya 0)
    d = tg.merge(d, on="key", how="outer")
    for c in IND:
        d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0)
    d["nama"] = d["nama_target"].fillna(d["nama"]).fillna(d["key"])
    d["kelompok"] = d["kelompok"].fillna("puskesmas").where(d["nama_target"].isna(), "puskesmas")
    if kelompok != "semua":
        d = d[d["kelompok"] == kelompok]
    if puskesmas:
        d = d[d["key"].isin(puskesmas if isinstance(puskesmas, list) else [puskesmas])]
    bulan = bulan_target(db, sampai)
    d = d.copy()
    d["t_terduga_sd"] = [_bulat(v / 12 * bulan, 10) if pd.notna(v) else None for v in d["t_terduga"]]
    d["t_penemuan_sd"] = [_bulat(v / 12 * bulan) if pd.notna(v) else None for v in d["t_penemuan"]]
    d["t_tb_anak_sd"] = [_bulat(v / 12 * bulan) if pd.notna(v) else None for v in d["t_tb_anak"]]
    d["pct_terduga"] = [_pct(a, b) for a, b in zip(d["terduga"], d["t_terduga_sd"])]
    d["pct_terduga_th"] = [_pct(a, b) for a, b in zip(d["terduga"], d["t_terduga"])]
    d["pct_penemuan"] = [_pct(a, b) for a, b in zip(d["penemuan"], d["t_penemuan"])]          # treatment coverage (thd target tahunan)
    d["pct_penemuan_sd"] = [_pct(a, b) for a, b in zip(d["penemuan"], d["t_penemuan_sd"])]
    d["pct_tb_anak"] = [_pct(a, b) for a, b in zip(d["tb_anak"], d["t_tb_anak"])]
    d["pct_enrolment"] = [_pct(a, b) for a, b in zip(d["enrolment"], d["penemuan"])]
    d["pct_ik"] = [_pct(a, b) for a, b in zip(d["ik_sudah"], d["ik_indeks"])]
    d["ik_belum"] = (d["ik_indeks"] - d["ik_sudah"]).clip(lower=0)
    d["pct_hiv"] = [_pct(a, b) for a, b in zip(d["tb03so_hiv_tahu"], d["tb03so_kasus"])]
    d["pct_dm"] = [_pct(a, b) for a, b in zip(d["tb03so_dm_tahu"], d["tb03so_kasus"])]
    d = d.drop(columns=["nama_target"]).sort_values("nama").reset_index(drop=True)
    return d, bulan


def ringkasan(db, dari=None, sampai=None, kelompok="puskesmas", puskesmas=None):
    d, bulan = rekap(db, dari, sampai, kelompok, puskesmas)
    pg = {k: v for k, v in db.execute(select(Pengaturan.kunci, Pengaturan.nilai))}
    s = {c: float(d[c].sum()) for c in IND}
    jml = lambda c: float(pd.to_numeric(d[c], errors="coerce").sum()) if len(d) else 0.0
    tt, tp, ta = jml("t_terduga_sd"), jml("t_penemuan_sd"), jml("t_tb_anak_sd")
    tp_th, ta_th = jml("t_penemuan"), jml("t_tb_anak")
    return dict(bulan_target=bulan, jumlah_faskes=int(len(d)), total=s,
                target_sd_bulan=dict(terduga=tt, penemuan=tp, tb_anak=ta),
                target_tahunan=dict(terduga=jml("t_terduga"), penemuan=tp_th, tb_anak=ta_th),
                persen=dict(terduga=_pct(s["terduga"], tt), penemuan=_pct(s["penemuan"], tp_th), penemuan_sd=_pct(s["penemuan"], tp),
                            tb_anak=_pct(s["tb_anak"], ta_th), enrolment=_pct(s["enrolment"], s["penemuan"]),
                            ik=_pct(s["ik_sudah"], s["ik_indeks"]), hiv=_pct(s["tb03so_hiv_tahu"], s["tb03so_kasus"]),
                            dm=_pct(s["tb03so_dm_tahu"], s["tb03so_kasus"])),
                target_pct=dict(enrolment=pg.get("target_enrolment_pct"), ik=pg.get("target_ik_pct"),
                                tsr=pg.get("target_tsr_pct"), hiv=pg.get("target_hiv_pct", 100), dm=pg.get("target_dm_pct", 100)))


def tren(db, indikator, dari=None, sampai=None, puskesmas=None, per="bulan"):
    q = _filter(select(Fakta.tanggal, func.sum(Fakta.nilai)).where(Fakta.indikator == indikator), dari, sampai)
    q = q.where((Batch.periode_akhir.is_(None)) | (Fakta.tanggal <= Batch.periode_akhir))
    if puskesmas:
        q = q.where(Fakta.faskes_key.in_(puskesmas if isinstance(puskesmas, list) else [puskesmas]))
    df = pd.DataFrame(db.execute(q.group_by(Fakta.tanggal).order_by(Fakta.tanggal)).all(), columns=["tanggal", "nilai"])
    if df.empty:
        return []
    df["tanggal"] = pd.to_datetime(df["tanggal"])
    if per == "bulan":
        df = df.groupby(df["tanggal"].dt.to_period("M"))["nilai"].sum().reset_index()
        df["tanggal"] = df["tanggal"].astype(str)
    else:
        df["tanggal"] = df["tanggal"].dt.strftime("%Y-%m-%d")
    return df.to_dict("records")


def tren_puskesmas(db, indikator, dari=None, sampai=None, puskesmas=None, kumulatif=True):
    """Nilai per puskesmas per bulan (kumulatif), untuk grafik perkembangan per puskesmas (slide 20-23)."""
    q = _filter(select(Fakta.faskes_key, Fakta.tanggal, Fakta.nilai).where(Fakta.indikator == indikator), dari, sampai)
    q = q.where((Batch.periode_akhir.is_(None)) | (Fakta.tanggal <= Batch.periode_akhir))
    df = pd.DataFrame(db.execute(q).all(), columns=["key", "tanggal", "nilai"])
    tg = _tabel_target(db)
    if puskesmas:
        tg = tg[tg["key"].isin(puskesmas if isinstance(puskesmas, list) else [puskesmas])]
    if df.empty or tg.empty:
        return dict(bulan=[], data=[])
    df["bulan"] = pd.to_datetime(df["tanggal"]).dt.to_period("M").astype(str)
    bulan = sorted(df["bulan"].unique())
    pv = df[df["key"].isin(tg["key"])].pivot_table(index="key", columns="bulan", values="nilai", aggfunc="sum").reindex(columns=bulan).fillna(0)
    if kumulatif:
        pv = pv.cumsum(axis=1)
    kol_target = {"penemuan": "t_penemuan", "terduga": "t_terduga", "tb_anak": "t_tb_anak"}.get(indikator)
    data = []
    for _, t in tg.iterrows():
        nilai = [float(pv.loc[t["key"], b]) if t["key"] in pv.index else 0.0 for b in bulan]
        data.append(dict(key=t["key"], nama=t["nama_target"], nilai=nilai,
                         target=_bulat(t[kol_target]) if kol_target else None))
    return dict(bulan=bulan, data=data)


# ---------------- Sukses rate (TSR) ----------------
HASIL_SUKSES = ("sembuh", "pengobatan_lengkap")
HASIL_SEMUA = {"sembuh": "sembuh", "pengobatan_lengkap": "lengkap", "gagal": "gagal", "meninggal": "meninggal",
               "putus_berobat_lost_to_follow_up": "ltfu", "tidak_dievaluasi_pindah": "tidak_evaluasi"}


def sukses_rate(db, puskesmas=None):
    """Sumber utama: lembar 'SUKSES RATE' di Data Zoom terbaru (seperti slide Rakor).
    Bila tidak ada, dihitung dari TB.03SO kohort tahun sebelumnya (atau tahun terlama yang tersedia)."""
    tg = _tabel_target(db)
    if puskesmas:
        tg = tg[tg["key"].isin(puskesmas if isinstance(puskesmas, list) else [puskesmas])]
    pg = {k: v for k, v in db.execute(select(Pengaturan.kunci, Pengaturan.nilai))}
    target = pg.get("target_tsr_pct", 90)
    tz = db.scalar(_filter(select(func.max(Fakta.tanggal)).where(Fakta.indikator == "zoom_tsr_total")))
    baris, sumber = [], ""
    if tz:
        q = _filter(select(Fakta.faskes_key, Fakta.indikator, func.sum(Fakta.nilai))
                    .where(Fakta.indikator.like("zoom_tsr_%"), Fakta.tanggal == tz)).group_by(Fakta.faskes_key, Fakta.indikator)
        z = {}
        for k, ind, v in db.execute(q):
            z.setdefault(k, {})[ind.replace("zoom_tsr_", "")] = v
        sumber = f"Data Zoom (lembar Sukses Rate, tarikan {tz:%d/%m/%Y}) - kohort pasien diobati tahun sebelumnya"
        for _, t in tg.iterrows():
            x = z.get(t["key"], {})
            total = x.get("total", 0) or 0
            sukses = (x.get("sembuh", 0) or 0) + (x.get("lengkap", 0) or 0)
            dinilai = sum((x.get(k, 0) or 0) for k in ("gagal", "meninggal", "lengkap", "ltfu", "sembuh", "tidak_evaluasi"))
            baris.append(dict(key=t["key"], nama=t["nama_target"], diobati=total, sukses=sukses, belum_evaluasi=max(total - dinilai, 0),
                              **{k: x.get(k, 0) or 0 for k in ("sembuh", "lengkap", "gagal", "meninggal", "ltfu", "tidak_evaluasi")},
                              pct=_pct(sukses, total)))
    else:
        q = _filter(select(Fakta.faskes_key, Fakta.tanggal, Fakta.indikator, Fakta.nilai)
                    .where((Fakta.indikator == "tb03so_kasus") | Fakta.indikator.like("tb03so_hasil_%")))
        df = pd.DataFrame(db.execute(q).all(), columns=["key", "tanggal", "ind", "nilai"])
        if not df.empty:
            df["tahun"] = pd.to_datetime(df["tanggal"]).dt.year
            akhir = tanggal_data_terakhir(db)
            th = sorted(df["tahun"].unique())
            kohort = max([y for y in th if akhir and y < akhir.year] or [min(th)])
            df = df[df["tahun"] == kohort]
            pv = df.pivot_table(index="key", columns="ind", values="nilai", aggfunc="sum").fillna(0)
            sumber = f"TB.03SO - kohort pasien mulai diobati tahun {kohort}"
            for _, t in tg.iterrows():
                r = pv.loc[t["key"]] if t["key"] in pv.index else pd.Series(dtype=float)
                g = lambda s: float(r.get("tb03so_hasil_" + s, 0))
                total = float(r.get("tb03so_kasus", 0))
                x = {v: g(k) for k, v in HASIL_SEMUA.items()}
                sukses = x["sembuh"] + x["lengkap"]
                baris.append(dict(key=t["key"], nama=t["nama_target"], diobati=total, sukses=sukses,
                                  belum_evaluasi=max(total - sum(x.values()), 0), **x, pct=_pct(sukses, total)))
    tot = {k: sum(b[k] for b in baris) for k in ("diobati", "sukses", "belum_evaluasi")} if baris else {}
    if tot:
        tot["pct"] = _pct(tot["sukses"], tot["diobati"])
    return dict(sumber=sumber, target=target, data=baris, total=tot)


# ---------------- TPT (TB.15) ----------------
KAT_TPT = [("anak_lt5", "Kontak Serumah (anak usia < 5 tahun)"), ("anak_5_14", "Kontak Serumah (anak usia 5-14 tahun)"),
           ("dewasa_ge15", "Kontak Serumah Remaja dan Dewasa (usia > 15 tahun)"), ("risiko_lain", "Kelompok Risiko Lainnya (Semua umur)")]


def tpt(db, puskesmas=None):
    """Capaian TPT dari TB.15 aktif terbaru (angka kumulatif periode laporan; filter tanggal tidak berlaku)."""
    tz = db.scalar(_filter(select(func.max(Fakta.tanggal)).where(Fakta.jenis == "tb15")))
    if not tz:
        return dict(tanggal=None, kolom=[k for k, _ in KAT_TPT], label=[l for _, l in KAT_TPT], data=[])
    b = db.scalar(select(Batch).join(Fakta, Fakta.batch_id == Batch.id).where(Batch.aktif.is_(True), Fakta.jenis == "tb15",
                                                                          Fakta.tanggal == tz).limit(1))
    q = _filter(select(Fakta.faskes_key, Fakta.indikator, func.sum(Fakta.nilai))
                .where(Fakta.jenis == "tb15", Fakta.tanggal == tz, Fakta.indikator.in_([f"tpt_{k}" for k, _ in KAT_TPT])))
    pv = {}
    for k, ind, v in db.execute(q.group_by(Fakta.faskes_key, Fakta.indikator)):
        pv.setdefault(k, {})[ind[4:]] = v
    tg = _tabel_target(db)
    if puskesmas:
        tg = tg[tg["key"].isin(puskesmas if isinstance(puskesmas, list) else [puskesmas])]
    data = [dict(key=t["key"], nama=t["nama_target"], **{k: pv.get(t["key"], {}).get(k, 0) for k, _ in KAT_TPT}) for _, t in tg.iterrows()]
    return dict(tanggal=tz, periode=b.periode_label if b else None, kolom=[k for k, _ in KAT_TPT], label=[l for _, l in KAT_TPT], data=data)


# ---------------- verifikasi terhadap Data Zoom ----------------
PASANGAN_ZOOM = {"skrining": "zoom_skrining", "terduga": "zoom_terduga", "penemuan": "zoom_penemuan",
                 "enrolment": "zoom_enrolment", "tb_anak": "zoom_tb_anak", "tb03so_kasus": "zoom_diobati",
                 "tb03so_hiv_tahu": "zoom_status_hiv", "tb03so_dm_tahu": "zoom_status_dm"}


def bandingkan_zoom(db):
    """Membandingkan hasil hitung sistem dengan angka Data Zoom pada tanggal tarikan yang sama."""
    tz = db.scalar(_filter(select(func.max(Fakta.tanggal)).where(Fakta.jenis == "zoom")))
    if not tz:
        return dict(tanggal=None, baris=[], pesan="Belum ada Data Zoom yang diunggah.")
    q = _filter(select(Fakta.faskes_key, Fakta.indikator, func.sum(Fakta.nilai))
                .where(Fakta.indikator.in_(list(PASANGAN_ZOOM.values())), Fakta.tanggal == tz)).group_by(Fakta.faskes_key, Fakta.indikator)
    z = pd.DataFrame(db.execute(q).all(), columns=["key", "ind", "zoom"]).pivot_table(index="key", columns="ind", values="zoom", aggfunc="sum")
    d, _ = rekap(db, None, tz)
    d = d.set_index("key")
    baris = []
    for key, r in z.iterrows():
        for sis, zm in PASANGAN_ZOOM.items():
            if zm not in z.columns:
                continue
            a, b = float(d[sis].get(key, 0) if key in d.index else 0), float(r.get(zm, 0) or 0)
            if a != b:
                baris.append(dict(puskesmas=d["nama"].get(key, key), indikator=sis, sistem=a, zoom=b, selisih=a - b))
    tot = {sis: dict(sistem=float(d.loc[d.index.isin(z.index), sis].sum()), zoom=float(z[zm].sum()))
           for sis, zm in PASANGAN_ZOOM.items() if zm in z.columns}
    return dict(tanggal=tz, total=tot, baris=baris)


def ke_excel(db, dari, sampai, kelompok="puskesmas", puskesmas=None) -> bytes:
    d, bulan = rekap(db, dari, sampai, kelompok, puskesmas)
    kol = {"nama": "Fasyankes", "skrining": "Skrining", "terduga": "Terduga TBC", "t_terduga": "Target Terduga Tahunan",
           "t_terduga_sd": f"Target Terduga s.d. Bulan ke-{bulan}", "pct_terduga": "% Terduga (thd target s.d. bulan)",
           "penemuan": "Penemuan Kasus", "t_penemuan": "Target Penemuan Tahunan", "pct_penemuan": "% Treatment Coverage",
           "enrolment": "Enrolment", "pct_enrolment": "% Enrolment (dari penemuan)",
           "tb_anak": "TB Anak (<=14 th)", "t_tb_anak": "Target TB Anak Tahunan", "pct_tb_anak": "% TB Anak",
           "tb03so_kasus": "Jumlah Pasien TB (TB.03SO)", "tb03so_hiv_tahu": "Tahu Status HIV", "pct_hiv": "% Status HIV",
           "tb03so_dm_tahu": "Tahu Status DM", "pct_dm": "% Status DM",
           "ik_indeks": "Total Kasus (IK)", "ik_sudah": "Sudah IK", "ik_belum": "Belum IK", "pct_ik": "% IK"}
    out = d[list(kol)].rename(columns=kol)
    for c in ("Target Terduga Tahunan", "Target Penemuan Tahunan", "Target TB Anak Tahunan"):
        out[c] = out[c].round(0)
    ket = pd.DataFrame({"Keterangan": ["Rekap Program TBC Kabupaten Sragen", f"Periode data: {dari or 'awal'} s.d. {sampai or 'terakhir'}",
                                       f"Dibuat: {datetime.now():%d/%m/%Y %H:%M}",
                                       f"Target s.d. bulan = target tahunan / 12 x {bulan} (terduga dibulatkan ke puluhan, seperti slide Rakor)",
                                       "Sumber: file SITB yang diunggah. Tidak berisi identitas pasien."]})
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        out.to_excel(w, sheet_name="Rekap", index=False)
        ket.to_excel(w, sheet_name="Keterangan", index=False)
        for ws in w.book.worksheets:
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = min(40, max(12, max(len(str(c.value or "")) for c in col) + 2))
    return buf.getvalue()
