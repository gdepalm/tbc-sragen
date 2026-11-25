import csv
from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from . import config
from .models import Basis, Pengaturan, Target
from .services.nama import key as kunci_faskes

_sqlite = config.DATABASE_URL.startswith("sqlite")
if _sqlite:   # pastikan folder database ada (mis. data/) supaya tidak error saat pertama kali dijalankan
    _p = config.DATABASE_URL.split("sqlite:///", 1)[-1]
    if _p and _p != ":memory:":
        Path(_p if Path(_p).is_absolute() else config.BASE / _p).parent.mkdir(parents=True, exist_ok=True)

_psycopg3 = config.DATABASE_URL.startswith("postgresql+psycopg://")

if _sqlite:
    engine = create_engine(
        config.DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False, "timeout": 60},
    )
elif _psycopg3:
    import psycopg

    _raw_url = config.DATABASE_URL.replace("postgresql+psycopg://", "postgresql://", 1)
    engine = create_engine(
        "postgresql+psycopg://",
        poolclass=NullPool,
        creator=lambda: psycopg.connect(_raw_url, prepare_threshold=None),
    )
else:
    engine = create_engine(
        config.DATABASE_URL,
        poolclass=NullPool,
    )

if _sqlite:
    @event.listens_for(engine, "connect")
    def _pragma(conn, _):
        c = conn.cursor(); c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA foreign_keys=ON"); c.close()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

PENGATURAN_AWAL = [
    ("target_enrolment_pct", 95, "Target enrolment (%). Sumber: slide Rakor (Target 95%)."),
    ("target_ik_pct", 90, "Target investigasi kontak (%). Sumber: dashboard lama."),
    ("target_tsr_pct", 90, "Target Sukses Rate (%). Sumber: slide Rakor (Target 90%)."),
    ("target_hiv_pct", 100, "Target pasien TBC mengetahui status HIV (%). Sumber: slide Rakor."),
    ("target_dm_pct", 100, "Target pasien TBC mengetahui status DM (%). Sumber: slide Rakor."),
    ("versi_target", 2, "Versi data target. 2 = angka target persis seperti slide Rakor (belum dibulatkan)."),
]
CSV_TARGET = Path(__file__).parent / "data" / "target_puskesmas_2026.csv"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _baca_csv():
    with open(CSV_TARGET, encoding="utf-8") as f:
        return [dict(key=kunci_faskes(r["puskesmas"]), nama="Puskesmas " + r["puskesmas"],
                     terduga_tahunan=float(r["target_terduga_tahunan"]), penemuan_tahunan=float(r["target_penemuan_tahunan"]),
                     tb_anak_tahunan=float(r["target_tb_anak_tahunan"])) for r in csv.DictReader(f)]


def init_db():
    Basis.metadata.create_all(engine)
    with SessionLocal() as db:
        versi_lama = db.get(Pengaturan, "versi_target")
        csv_rows = _baca_csv()
        if db.scalar(select(Target.key).limit(1)) is None:
            for r in csv_rows:
                db.add(Target(**r))
        elif versi_lama is None:
            # database dari versi sebelumnya: target masih dibulatkan (mis. 621). Ganti dengan angka persis slide
            # HANYA bila nilainya belum diubah pengguna (masih sama dengan pembulatan).
            for r in csv_rows:
                t = db.get(Target, r["key"])
                if t and all(round(getattr(t, k)) == round(r[k]) for k in ("terduga_tahunan", "penemuan_tahunan", "tb_anak_tahunan")):
                    t.terduga_tahunan, t.penemuan_tahunan, t.tb_anak_tahunan = r["terduga_tahunan"], r["penemuan_tahunan"], r["tb_anak_tahunan"]
        for k, v, ket in PENGATURAN_AWAL:
            if db.get(Pengaturan, k) is None:
                db.add(Pengaturan(kunci=k, nilai=v, keterangan=ket))
        db.commit()