"""Struktur database. TIDAK ada tabel yang menyimpan nama, NIK, alamat, atau telepon pasien."""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Basis(DeclarativeBase):
    pass


class Batch(Basis):
    """Satu kali pengolahan = satu jenis laporan (laporan skrining 1-3 digabung jadi satu batch)."""
    __tablename__ = "batch"
    id: Mapped[int] = mapped_column(primary_key=True)
    jenis: Mapped[str] = mapped_column(String(20))
    periode_label: Mapped[Optional[str]] = mapped_column(String(80))
    periode_awal: Mapped[Optional[date]] = mapped_column(Date)
    periode_akhir: Mapped[Optional[date]] = mapped_column(Date)
    # menunggu | menunggu_konfirmasi | diproses | selesai | gagal | dibatalkan
    status: Mapped[str] = mapped_column(String(25), default="menunggu")
    aktif: Mapped[bool] = mapped_column(Boolean, default=False)  # hanya batch aktif dipakai dashboard
    mode: Mapped[str] = mapped_column(String(10), default="tambah")  # tambah | ganti
    progres: Mapped[int] = mapped_column(Integer, default=0)
    pesan: Mapped[Optional[str]] = mapped_column(Text)
    baris_dibaca: Mapped[int] = mapped_column(Integer, default=0)
    baris_berhasil: Mapped[int] = mapped_column(Integer, default=0)
    baris_ditolak: Mapped[int] = mapped_column(Integer, default=0)
    baris_ganda: Mapped[int] = mapped_column(Integer, default=0)  # dibuang karena sama dengan file lain
    dibuat: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    selesai_pada: Mapped[Optional[datetime]] = mapped_column(DateTime)
    diganti_oleh: Mapped[Optional[int]] = mapped_column(Integer)
    berkas: Mapped[list["Berkas"]] = relationship(back_populates="batch")


class Berkas(Basis):
    __tablename__ = "berkas"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("batch.id"))
    nama_asli: Mapped[str] = mapped_column(String(300))
    ukuran: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    jenis: Mapped[Optional[str]] = mapped_column(String(20))
    sheet: Mapped[Optional[str]] = mapped_column(String(100))
    baris: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(25), default="diterima")
    pesan: Mapped[Optional[str]] = mapped_column(Text)
    path: Mapped[Optional[str]] = mapped_column(String(500))
    dibuat: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    batch: Mapped[Optional[Batch]] = relationship(back_populates="berkas")


class Fakta(Basis):
    """Angka agregat: jumlah per (tanggal, fasyankes, indikator). Tanpa identitas pasien."""
    __tablename__ = "fakta"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batch.id"), index=True)
    jenis: Mapped[str] = mapped_column(String(20))
    tanggal: Mapped[date] = mapped_column(Date, index=True)
    faskes_key: Mapped[str] = mapped_column(String(120), index=True)
    indikator: Mapped[str] = mapped_column(String(60), index=True)
    nilai: Mapped[float] = mapped_column(Float)


Index("ix_fakta_cari", Fakta.indikator, Fakta.tanggal, Fakta.faskes_key)


class Faskes(Basis):
    __tablename__ = "faskes"
    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    nama: Mapped[str] = mapped_column(String(200))
    kelompok: Mapped[str] = mapped_column(String(20))  # puskesmas | klinik | rs | lapas | lainnya


class Target(Basis):
    __tablename__ = "target_puskesmas"
    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    nama: Mapped[str] = mapped_column(String(200))
    terduga_tahunan: Mapped[float] = mapped_column(Float)
    penemuan_tahunan: Mapped[float] = mapped_column(Float)
    tb_anak_tahunan: Mapped[float] = mapped_column(Float)


class Pengaturan(Basis):
    __tablename__ = "pengaturan"
    kunci: Mapped[str] = mapped_column(String(60), primary_key=True)
    nilai: Mapped[float] = mapped_column(Float)
    keterangan: Mapped[Optional[str]] = mapped_column(String(300))


class Masalah(Basis):
    """Catatan validasi. Hanya nomor baris + alasan, TIDAK menyimpan isi baris."""
    __tablename__ = "masalah_validasi"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batch.id"), index=True)
    berkas: Mapped[Optional[str]] = mapped_column(String(300))
    baris: Mapped[Optional[int]] = mapped_column(Integer)
    pesan: Mapped[str] = mapped_column(String(300))


class RekapHistoris(Basis):
    """Riwayat dari database lama (tbc.db) / slide Rakor."""
    __tablename__ = "rekap_historis"
    id: Mapped[int] = mapped_column(primary_key=True)
    tanggal: Mapped[date] = mapped_column(Date, index=True)
    key: Mapped[str] = mapped_column(String(120), index=True)
    puskesmas: Mapped[str] = mapped_column(String(200))
    skrining: Mapped[Optional[float]] = mapped_column(Float)
    terduga: Mapped[Optional[float]] = mapped_column(Float)
    penemuan: Mapped[Optional[float]] = mapped_column(Float)
    enrolment: Mapped[Optional[float]] = mapped_column(Float)
    tb_anak: Mapped[Optional[float]] = mapped_column(Float)
    ik_total: Mapped[Optional[float]] = mapped_column(Float)
    ik_sudah: Mapped[Optional[float]] = mapped_column(Float)
    sumber: Mapped[str] = mapped_column(String(20), default="slide")


class Kontak(Basis):
    """Isi halaman Contact Us (bisa diubah lewat website). Bukan data pasien."""
    __tablename__ = "kontak"
    kunci: Mapped[str] = mapped_column(String(40), primary_key=True)
    nilai: Mapped[Optional[str]] = mapped_column(Text)
