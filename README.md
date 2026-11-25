# TBC Monitoring Dashboard – Kabupaten Sragen (versi 5, rumus = slide Rakor)

Versi ini memperbaiki grafik dan rumus supaya **sama persis** dengan slide *Rakor Kapus 8 Okt 2026* dan *Data Zoom 7 Okt 2026*.
Sudah diuji dengan file SITB asli Januari–Oktober 2026: **18 grafik slide cocok 100% untuk 25 puskesmas** dan **34 uji otomatis lulus**.

Database bawaan (`data/tbc.db`) sudah berisi data Januari–Oktober 2026 (hanya angka agregat, tanpa nama/NIK),
jadi begitu website menyala, grafiknya langsung bisa dibandingkan dengan PPT.

---
## A. Menjalankan pertama kali di VS Code (Windows)

**Persiapan (sekali saja)**
1. Pasang **Python 3.12 atau 3.13** dari https://www.python.org/downloads/ → saat memasang **centang "Add python.exe to PATH"**.
2. Pasang **VS Code** dan ekstensi **Python** (Microsoft) dari menu Extensions (Ctrl+Shift+X).
3. Ekstrak zip ini ke folder BARU, misalnya `D:\tbc-sragen`. **Jangan** ditimpa ke folder versi lama
   (folder lama berisi kode berbeda dan file Excel pasien di `data\upload`).

**Membuka & menjalankan**
1. VS Code → **File → Open Folder…** → pilih folder `tbc-sragen` (folder yang berisi `app`, `frontend`, `requirements.txt`).
2. Menu **Terminal → New Terminal**, lalu ketik satu per satu (tekan Enter tiap baris):
   ```
   py -m venv .venv
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   .venv\Scripts\python.exe -m uvicorn app.main:app --reload
   ```
   (Jika `py` tidak dikenali, ganti dengan `python`. Langkah pip butuh internet, sekitar 2–5 menit, hanya pertama kali.)
3. Tunggu tulisan `Uvicorn running on http://127.0.0.1:8000`, lalu buka **http://127.0.0.1:8000** di browser.
4. Tekan **Ctrl+F5** sekali di browser (memastikan tidak ada tampilan lama yang tersimpan).
5. Untuk berhenti: klik terminal lalu tekan **Ctrl+C**.

**Berikutnya (hari-hari selanjutnya)** cukup buka folder di VS Code lalu tekan **F5** (konfigurasi "Jalankan Website TBC"),
atau **Terminal → Run Build Task (Ctrl+Shift+B)**, atau klik dua kali **JALANKAN.bat** tanpa VS Code.

**Jika muncul masalah**
| Pesan | Solusi |
|---|---|
| `py` / `python` is not recognized | Python belum terpasang / belum dicentang "Add to PATH". Pasang ulang Python. |
| `running scripts is disabled` saat activate | Tidak perlu activate. Pakai perintah persis seperti di atas (`.venv\Scripts\python.exe …`). |
| `[Errno 10048] address already in use` | Website sudah menyala di jendela lain. Tutup terminal/JALANKAN.bat lama, atau ganti `--port 8001`. |
| Tampilan masih seperti versi lama | Pastikan membuka folder BARU, lalu Ctrl+F5 di browser. |
| `ModuleNotFoundError` | Langkah `pip install -r requirements.txt` belum berhasil. Ulangi (perlu internet). |

---
## B. Halaman & grafik (mengikuti slide Rakor)
| Menu | Grafik slide | Sumber laporan |
|---|---|---|
| Skrining | Capaian Skrining TB (terbanyak dulu) | Laporan Skrining 1–3 |
| Terduga TBC | Capaian Terduga TB + Terduga (Bulanan) | TB.06 |
| Penemuan Kasus | Treatment Coverage + perkembangan kumulatif per puskesmas | TB.06 |
| TB Anak | Capaian Penemuan TB Anak | TB.06 |
| Enrolment | Penemuan kasus yang diobati (target 95%) | TB.06 |
| Status HIV / Status DM | Pasien TBC mengetahui status HIV / DM (target 100%) | TB.03SO |
| Sukses Rate | Capaian Sukses Rate (target 90%) | Data Zoom (lembar SUKSES RATE) atau TB.03SO kohort |
| Investigasi Kontak | Capaian IK (total, sudah, belum, %) | TB.16RK |
| TPT | Tabel Capaian TPT | TB.15 |

Setiap grafik punya tombol **⬇ PNG** (tabel data di bawah grafik ikut tersimpan), dan semua tabel bisa diunduh lewat **Rekap Excel**.

## B2. Baru di versi 5
- **Contact Us** (menu paling kanan): kartu Instansi, Unit Pengelola, Pengelola Dashboard, Email, Telepon/WhatsApp, Alamat,
  Website, Jam Layanan. Isi lewat tombol **Edit Informasi Kontak** (tersimpan di database, tabel `kontak`, dibuat otomatis).
  Email → tombol *Kirim Email*, nomor HP → tombol *Chat WhatsApp*, alamat → membuka Google Maps.
- **Menu atas satu baris yang bisa digeser**: pakai tombol panah ‹ ›, roda mouse saat kursor di atas menu, atau geser touchpad.
  Menu halaman yang sedang dibuka otomatis digeser supaya terlihat.

## C. Rumus (dicocokkan dengan pivot petugas, Data Zoom, dan slide)
| Indikator | Rumus |
|---|---|
| Skrining | 1 baris Laporan Skrining = 1 orang, per Unit Pelaksana (bagian 2 & 3 yang sama dengan bagian 1 dibuang) |
| Terduga TBC | TB.06, Status Diagnosis = "Sesuai standar" |
| Penemuan (TC) | TB.06, kolom "Terkonfirmasi TBC" terisi. % TC = penemuan ÷ target tahunan |
| Enrolment | Penemuan dengan Tindak Lanjut "Akan diobati" **dan Tanggal Mulai Pengobatan terisi**, atau "Melanjutkan pengobatan". % = enrolment ÷ penemuan *(versi lama selisih 5 dengan Zoom, sekarang sama)* |
| TB anak | Penemuan dengan umur ≤ 14 tahun |
| Jumlah pasien TB | TB.03SO, semua baris pasien per fasyankes |
| Tahu status HIV | TB.03SO, "Hasil Tes" (Kolaborasi TBC-HIV) **atau** "Status HIV" berisi ODHIV / Bukan ODHIV *(versi lama hanya kolom Status HIV, sehingga batang oranye jauh terlalu pendek)* |
| Tahu status DM | TB.03SO, kolom "DM" (Kegiatan TBC-DM) berisi Positif / Negatif |
| Investigasi kontak | TB.16RK, jumlah kasus indeks; Sudah IK = Status IK "Sudah IK" |
| Sukses rate | (Sembuh + Pengobatan Lengkap) ÷ pasien diobati; belum dievaluasi = diobati − semua hasil akhir |
| Target s.d. bulan | target tahunan ÷ 12 × bulan data. Terduga dibulatkan ke puluhan (seperti slide), penemuan & TB anak ke bilangan bulat |
| Target tahunan | Angka persis dari slide (mis. Kalijambe terduga 620,84; penemuan 114,97; TB anak 18,40) |

"Data sampai" = tanggal terakhir pada Laporan Skrining / TB.06 (tanggal di luar periode laporan diabaikan).

## D. Menambah data baru (mis. November)
Menu **Upload Data** → seret semua file SITB sekaligus → **Unggah dan Proses**.
Karena periodenya bertumpuk dengan data Oktober, sistem bertanya: pilih **Ganti Data Lama** (data lama tetap tersimpan di Riwayat).
File yang persis sama dengan yang sudah ada otomatis ditolak sebagai duplikat.
Untuk mulai dari database kosong: tutup website, hapus file `data\tbc.db`, lalu jalankan lagi.

## E. Uji otomatis
```
.venv\Scripts\python.exe tests\uji_file_asli.py "C:\folder\berisi\file-excel-SITB"
.venv\Scripts\python.exe tests\uji_crud_target.py
```

## F. Aturan keamanan data
- Database hanya menyimpan **angka agregat** (per tanggal, fasyankes, indikator). Nama, NIK, alamat, telepon **tidak disimpan**.
- File Excel asli **dihapus otomatis** setelah diolah (`SIMPAN_BERKAS_ASLI=false` di `.env`).
- Jangan bagikan folder `data\upload` dari versi lama: di sana masih ada file Excel berisi data pasien.
