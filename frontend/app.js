"use strict";
/* TBC Monitoring Dashboard Kabupaten Sragen – seluruh tampilan Bahasa Indonesia */
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = n => n == null ? "–" : Number(n).toLocaleString("id-ID", { maximumFractionDigits: 1 });
const pct = n => n == null ? "–" : fmt(n) + "%";
const BLN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
const blnPendek = k => { const [y, m] = k.split("-"); return m ? BLN[+m - 1].slice(0, 3) + " " + y : k; };
const tglId = iso => iso ? new Date(iso + "T00:00:00").toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" }) : "–";
const NAMA_IND = { skrining: "Skrining", terduga: "Terduga TBC", penemuan: "Penemuan Kasus", enrolment: "Enrolment", tb_anak: "TB Anak (≤14 th)", tb03so_kasus: "Pasien TB Diobati (TB.03SO)", tb03so_hiv_tahu: "Tahu Status HIV", tb03so_dm_tahu: "Tahu Status DM", ik_indeks: "Kasus Indeks IK", ik_sudah: "Sudah Investigasi Kontak" };
const WARNA = { navy: "#0b2a4a", teal: "#0f9d94", teal2: "#14b8a6", biru: "#7dd3fc", abu: "#94a3b8", merah: "#d64545" };

const S = { f: { tahun: "", bulan: "", dari: "", sampai: "", kelompok: "puskesmas", puskesmas: [] }, opsi: null, charts: {}, timer: null };

const MENU = [
  ["dashboard", "▦", "Dashboard Utama", pgDashboard, true],
  ["upload", "⬆", "Upload Data", pgUpload, false],
  ["skrining", "◎", "Data Skrining", () => pgIndikator(CFG.skrining), true],
  ["terduga", "?", "Data Terduga TBC", () => pgIndikator(CFG.terduga), true],
  ["penemuan", "✚", "Penemuan Kasus", () => pgIndikator(CFG.penemuan), true],
  ["tb_anak", "☺", "TB Anak", () => pgIndikator(CFG.tb_anak), true],
  ["enrolment", "℞", "Enrolment", () => pgIndikator(CFG.enrolment), true],
  ["hiv", "⚕", "Status HIV Pasien TBC", () => pgIndikator(CFG.hiv), true],
  ["dm", "◍", "Status DM Pasien TBC", () => pgIndikator(CFG.dm), true],
  ["tsr", "✓", "Sukses Rate", pgTsr, true],
  ["ik", "☍", "Investigasi Kontak", () => pgIndikator(CFG.ik), true],
  ["tpt", "⛨", "Capaian TPT", pgTpt, true],
  ["tren", "↗", "Tren dan Analisis", pgTren, true],
  ["database", "▤", "Database", pgDatabase, true],
  ["target", "✎", "Data Target Puskesmas", pgTarget, false],
  ["riwayat", "⟲", "Riwayat Upload", pgRiwayat, false],
  ["kontak", "✆", "Contact Us", pgKontak, false],
];

/* ---------- utilitas ---------- */
function toast(pesan, err) {
  const t = document.createElement("div"); t.className = "toast" + (err ? " err" : ""); t.textContent = pesan;
  $("#toast").appendChild(t); setTimeout(() => t.remove(), err ? 7000 : 4000);
}
async function api(path, params, opt) {
  const u = new URL(path, location.origin);
  Object.entries(params || {}).forEach(([k, v]) => { if (v !== "" && v != null && !(Array.isArray(v) && !v.length)) u.searchParams.set(k, Array.isArray(v) ? v.join(",") : v); });
  const r = await fetch(u, opt);
  if (!r.ok) { let m = "Terjadi kesalahan pada server."; try { const d = (await r.json()).detail; m = Array.isArray(d) ? d.map(x => String(x.msg || "").replace(/^Value error, /, "")).join("; ") || m : d || m; } catch (e) { } throw new Error(m); }
  return r.json();
}
function qs() { const f = S.f; return { dari: f.dari, sampai: f.sampai, kelompok: f.kelompok, puskesmas: f.puskesmas }; }
function buatGrafik(id, cfg) {
  if (S.charts[id]) S.charts[id].destroy();
  const el = document.getElementById(id); if (!el) return;
  cfg.options = Object.assign({ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: (cfg.data.datasets.length > 1) } } }, cfg.options || {});
  S.charts[id] = new Chart(el, cfg);
}
const kartuGrafik = (id, judul, sub, tinggi) => `<div class="kartu"><div class="kartu-kepala"><div><h3>${judul}</h3><div class="sub">${sub || ""}</div></div><button class="btn ghost kecil" data-png="${id}" data-nama="${esc(judul)}">⬇ PNG</button></div><div class="chart-box ${tinggi ? "tinggi" : ""}"><canvas id="${id}"></canvas></div></div>`;
document.addEventListener("click", e => {
  const b = e.target.closest("[data-png]"); if (!b) return;
  const c = S.charts[b.dataset.png]; if (!c) return;
  const k = document.createElement("canvas"); k.width = c.canvas.width; k.height = c.canvas.height;
  const x = k.getContext("2d"); x.fillStyle = "#fff"; x.fillRect(0, 0, k.width, k.height); x.drawImage(c.canvas, 0, 0);
  const a = document.createElement("a"); a.href = k.toDataURL("image/png"); a.download = b.dataset.nama.replace(/[^\w]+/g, "_") + ".png"; a.click();
});
const kosong = (judul, teks) => `<div class="kartu kosong"><div class="ikon">📂</div><h2>${judul}</h2><p>${teks}</p><a class="btn teal" href="#upload">Buka Upload Data</a></div>`;
const loading = () => { $("#isi").innerHTML = '<div class="spin" role="status" aria-label="Memuat"></div>'; };

/* ---------- filter ---------- */
function atur_periode() {
  const f = S.f; if (!f.tahun) return;
  const y = +f.tahun, m = f.bulan ? +f.bulan : 0;
  f.dari = m ? `${y}-${String(m).padStart(2, "0")}-01` : `${y}-01-01`;
  const akhir = m ? new Date(y, m, 0).getDate() : 31; f.sampai = m ? `${y}-${String(m).padStart(2, "0")}-${akhir}` : `${y}-12-31`;
}
function renderFilter() {
  const o = S.opsi, f = S.f, el = $("#filter");
  const th = o.tahun.map(y => `<option ${f.tahun == y ? "selected" : ""}>${y}</option>`).join("");
  const bl = BLN.map((b, i) => `<option value="${i + 1}" ${f.bulan == i + 1 ? "selected" : ""}>${b}</option>`).join("");
  const pk = o.puskesmas.map(p => `<option value="${p.key}" ${f.puskesmas.includes(p.key) ? "selected" : ""}>${esc(p.nama)}</option>`).join("");
  el.innerHTML = `
   <label>Tahun<select id="f-tahun"><option value="">Semua</option>${th}</select></label>
   <label>Bulan<select id="f-bulan"><option value="">Semua</option>${bl}</select></label>
   <label>Dari tanggal<input type="date" id="f-dari" value="${f.dari}"></label>
   <label>Sampai tanggal<input type="date" id="f-sampai" value="${f.sampai}"></label>
   <label>Fasyankes<select id="f-kel"><option value="puskesmas" ${f.kelompok == "puskesmas" ? "selected" : ""}>25 Puskesmas</option><option value="semua" ${f.kelompok == "semua" ? "selected" : ""}>Semua fasyankes</option></select></label>
   <label>Puskesmas (boleh pilih beberapa)<select id="f-pusk" multiple>${pk}</select></label>
   <button class="btn ghost" id="f-reset">Reset Filter</button>
   <button class="btn teal" id="f-unduh">⬇ Rekap Excel</button>`;
  const baru = () => { S.f.puskesmas = [...$("#f-pusk").selectedOptions].map(x => x.value); halaman(); };
  $("#f-tahun").onchange = e => { f.tahun = e.target.value; if (!f.tahun) { f.bulan = ""; f.dari = f.sampai = ""; } atur_periode(); renderFilter(); baru(); };
  $("#f-bulan").onchange = e => { f.bulan = e.target.value; if (!f.tahun && f.bulan) { f.tahun = o.tahun[o.tahun.length - 1]; } atur_periode(); renderFilter(); baru(); };
  $("#f-dari").onchange = e => { f.dari = e.target.value; f.tahun = f.bulan = ""; baru(); };
  $("#f-sampai").onchange = e => { f.sampai = e.target.value; f.tahun = f.bulan = ""; baru(); };
  $("#f-kel").onchange = e => { f.kelompok = e.target.value; if (f.kelompok == "semua") f.puskesmas = []; baru(); };
  $("#f-pusk").onchange = baru;
  $("#f-reset").onclick = () => { Object.assign(S.f, { tahun: "", bulan: "", dari: "", sampai: "", kelompok: "puskesmas", puskesmas: [] }); renderFilter(); halaman(); };
  $("#f-unduh").onclick = () => { const u = new URL("/api/unduh/rekap.xlsx", location.origin); Object.entries(qs()).forEach(([k, v]) => { if (v && !(Array.isArray(v) && !v.length)) u.searchParams.set(k, Array.isArray(v) ? v.join(",") : v); }); location.href = u; };
}

/* ---------- komponen ---------- */
function statusWarna(p, target) { if (p == null) return ""; return p >= target ? "ok" : p >= target * .8 ? "warn" : "bad"; }
function kartuStat(judul, nilai, sub, p, target, ketTarget) {
  const w = statusWarna(p, target || 100);
  return `<div class="kartu stat"><div class="t">${judul}</div><div class="n">${typeof nilai == "string" ? nilai : fmt(nilai)}</div>
  ${p != null ? `<div class="p ${w}">${pct(p)} <span class="muted">${ketTarget || ("dari " + (target ? "target " + target + "%" : "target s.d. bulan ini"))}</span></div><div class="bar"><div style="width:${Math.min(p, 100)}%"></div></div>` : ""}
  <div class="muted" style="font-size:12.5px;margin-top:6px;position:relative;z-index:1">${sub || ""}</div></div>`;
}
function tabel(rows, cols, foot) {
  return `<div class="tabel-wrap"><table><thead><tr>${cols.map((c, i) => `<th class="${i ? "" : "kiri"}">${c.l}</th>`).join("")}</tr></thead><tbody>${rows.map(r => `<tr>${cols.map((c, i) => `<td class="${i ? "" : "kiri"}">${c.p ? pct(r[c.k]) : (i ? fmt(r[c.k]) : esc(r[c.k]))}</td>`).join("")}</tr>`).join("")}</tbody>
  ${foot ? `<tfoot><tr>${cols.map((c, i) => `<td class="${i ? "" : "kiri"}">${foot[c.k] === undefined ? "" : (c.p ? pct(foot[c.k]) : (i ? fmt(foot[c.k]) : foot[c.k]))}</td>`).join("")}</tr></tfoot>` : ""}</table></div>`;
}
const jumlah = (rows, k) => rows.reduce((a, r) => a + (+r[k] || 0), 0);
const trenData = (ind) => api("/api/tren", { indikator: ind, dari: S.f.dari, sampai: S.f.sampai, puskesmas: S.f.puskesmas, per: "bulan" });
const tidakAdaData = r => !r || !Object.values(r.total).some(v => v > 0);

/* ---------- Dashboard Utama (gaya landing page: hero + bagian bergulir) ---------- */
function aktifkanReveal() {
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add("tampil"); io.unobserve(e.target); } }), { threshold: .1 });
  document.querySelectorAll(".rv").forEach(x => io.observe(x));
}
function seksi(n, kelas, balik, judul, angka, sub, p, target, tautan, cid) {
  return `<div class="seksi ${kelas} ${balik ? "balik" : ""} rv"><div class="seksi-teks"><span class="label">${n} · ${judul}</span><h2>${judul}</h2><div class="angka">${fmt(angka)}</div><p>${sub}</p>
   ${p != null ? `<div class="bar"><div style="width:${Math.min(p, 100)}%"></div></div><div class="kecil-p">${pct(p)} ${target ? "dari target " + target + "%" : "dari target s.d. bulan ini"}</div>` : ""}
   <a class="btn" href="#${tautan}">Lihat detail →</a></div><div class="seksi-grafik"><div class="chart-box"><canvas id="${cid}"></canvas></div></div></div>`;
}
const LANGKAH = `<div class="blok rv"><h2>Tiga langkah <em>sederhana</em></h2><p class="lead">Tidak perlu lagi membuka banyak file Excel, membuat Pivot Table, atau menghitung manual.</p>
  <div class="langkah"><div class="kartu"><span class="no">1</span><h3>Unggah file Excel</h3><p>Seret semua laporan SITB sekaligus. Jenis laporan dikenali otomatis.</p></div>
  <div class="kartu"><span class="no">2</span><h3>Diolah otomatis</h3><p>Data diperiksa, digabung tanpa ganda, lalu indikator dihitung.</p></div>
  <div class="kartu"><span class="no">3</span><h3>Lihat dan unduh</h3><p>Grafik, tabel capaian, dan rekap Excel siap dipakai untuk laporan.</p></div></div></div>`;
async function pgDashboard() {
  const [rg, rk, sk, td, pn, en] = await Promise.all([api("/api/ringkasan", qs()), api("/api/rekap", qs()), trenData("skrining"), trenData("terduga"), trenData("penemuan"), trenData("enrolment")]);
  const ada = !tidakAdaData(rg), t = rg.total, p = rg.persen, tp = rg.target_pct;
  const hero = `<section class="hero rv"><div><span class="etiket">Program TBC · Kabupaten Sragen</span>
    <h2>Pantau program <em>TBC</em> Kabupaten Sragen dalam satu layar</h2>
    <p>Unggah laporan Excel dari SITB. Sistem membaca, memeriksa, menghitung, dan menyajikannya sebagai angka, grafik, dan laporan.</p>
    <div class="tools"><a class="btn putih" href="#upload">⬆ Unggah Data</a>${ada ? '<a class="btn garis" href="#sec-capaian">Lihat Capaian ↓</a>' : ""}</div></div>
    ${ada ? `<div class="kaca"><div class="baris"><span>Total skrining</span><b>${fmt(t.skrining)}</b></div><div class="baris"><span>Terduga TBC</span><b>${fmt(t.terduga)}</b></div><div class="baris"><span>Penemuan kasus</span><b>${fmt(t.penemuan)}</b></div><small>Data sampai ${tglId(S.opsi.tanggal_akhir)}</small></div>`
      : `<div class="status-kosong"><b>Belum ada data.</b><br>Mulai dengan mengunggah file Excel SITB pertama Anda.</div>`}<span class="orb"></span></section>`;
  if (!ada) { $("#isi").innerHTML = hero + LANGKAH; $("#filter").hidden = true; return; }
  $("#isi").innerHTML = hero + `
  <div class="blok rv" id="sec-capaian"><h2>Ringkasan <em>capaian</em></h2><p class="lead">Persentase dihitung terhadap target tahunan ÷ 12 × ${rg.bulan_target} (sampai bulan ke-${rg.bulan_target}). Data terbaru sampai ${tglId(S.opsi.tanggal_akhir)}, jadi bulan terakhir pada grafik belum penuh.</p>
   <div class="grid kartu-grid geser-hp">
    ${kartuStat("Total Skrining", t.skrining, "orang diskrining")}
    ${kartuStat("Terduga TBC", t.terduga, "sesuai standar", p.terduga)}
    ${kartuStat("Penemuan Kasus", t.penemuan, "terkonfirmasi (treatment coverage)", p.penemuan, null, "dari target tahunan")}
    ${kartuStat("Enrolment", t.enrolment, "dari penemuan kasus", p.enrolment, tp.enrolment)}
    ${kartuStat("TB Anak (≤14 th)", t.tb_anak, "kasus anak ditemukan", p.tb_anak, null, "dari target tahunan")}
    ${kartuStat("Tahu Status HIV", t.tb03so_hiv_tahu, `dari ${fmt(t.tb03so_kasus)} pasien TB`, p.hiv, tp.hiv)}
    ${kartuStat("Tahu Status DM", t.tb03so_dm_tahu, `dari ${fmt(t.tb03so_kasus)} pasien TB`, p.dm, tp.dm)}
    ${kartuStat("Investigasi Kontak", t.ik_sudah, `dari ${fmt(t.ik_indeks)} kasus indeks`, p.ik, tp.ik)}
   </div></div>
  ${LANGKAH}
  ${seksi("01", "s1", false, "Skrining", t.skrining, "Jumlah orang yang diskrining TBC. Grafik menunjukkan perkembangan tiap bulan.", null, null, "skrining", "d-skr")}
  ${seksi("02", "s2", true, "Terduga TBC", t.terduga, "Terduga dengan status diagnosis sesuai standar.", p.terduga, null, "terduga", "d-td")}
  ${seksi("03", "s3", false, "Penemuan Kasus", t.penemuan, "Kasus terkonfirmasi TBC yang ditemukan, termasuk " + fmt(t.tb_anak) + " kasus anak. Persentase = treatment coverage terhadap target tahunan.", p.penemuan, null, "penemuan", "d-pn").replace("dari target s.d. bulan ini", "dari target tahunan")}
  ${seksi("04", "s4", true, "Enrolment", t.enrolment, "Pasien yang akan atau sedang melanjutkan pengobatan, dibanding seluruh kasus yang ditemukan.", p.enrolment, tp.enrolment, "enrolment", "d-en")}
  ${seksi("05", "s5", false, "Investigasi Kontak", t.ik_sudah, `Kasus indeks yang sudah diinvestigasi kontaknya, dari ${fmt(t.ik_indeks)} kasus indeks.`, p.ik, tp.ik, "ik", "d-ik")}
  <div class="blok rv"><h2>Capaian per <em>puskesmas</em></h2><p class="lead">Realisasi dibanding target sampai bulan ini, sesuai filter yang dipilih.</p>
   <div class="grid dua">${kartuGrafik("c-pn", "Penemuan Kasus per Puskesmas", "Realisasi dibanding target", true)}${kartuGrafik("c-td", "Terduga TBC per Puskesmas", "Realisasi dibanding target", true)}</div>
   <div class="kartu" style="margin-top:16px"><h3>Tabel Capaian</h3><div class="sub">Sesuai filter yang dipilih</div>${tabelCapaian(rk.data)}</div></div>
  <div class="footer-lp rv">Data kesehatan bersifat rahasia. Hanya angka agregat yang ditampilkan; nama, NIK, alamat, dan nomor telepon pasien tidak disimpan.</div>`;
  $(".hero").after($("#filter")); $("#filter").hidden = false;
  const bar = (id, data, warna) => buatGrafik(id, { type: "bar", data: { labels: data.map(x => blnPendek(x.tanggal)), datasets: [{ label: id, data: data.map(x => x.nilai), backgroundColor: warna, borderRadius: 8 }] }, options: { plugins: { legend: { display: false } } } });
  buatGrafik("d-skr", { type: "line", data: { labels: sk.map(x => blnPendek(x.tanggal)), datasets: [{ label: "Skrining", data: sk.map(x => x.nilai), borderColor: WARNA.teal, backgroundColor: "rgba(20,184,166,.15)", fill: true, tension: .35 }] }, options: { plugins: { legend: { display: false } } } });
  bar("d-td", td, WARNA.biru); bar("d-pn", pn, WARNA.teal); bar("d-en", en, WARNA.navy);
  buatGrafik("d-ik", { type: "doughnut", data: { labels: ["Sudah IK", "Belum IK"], datasets: [{ data: [t.ik_sudah, Math.max(t.ik_indeks - t.ik_sudah, 0)], backgroundColor: [WARNA.teal, WARNA.merah] }] }, options: { plugins: { legend: { display: true, position: "bottom" } } } });
  grafikPuskesmas("c-pn", rk.data, "penemuan", "t_penemuan_sd"); grafikPuskesmas("c-td", rk.data, "terduga", "t_terduga_sd");
}
function grafikPuskesmas(id, data, k, kt) {
  const d = [...data].sort((a, b) => b[k] - a[k]);
  const ds = [{ label: "Realisasi", data: d.map(x => x[k]), backgroundColor: WARNA.teal }];
  if (kt && d.some(x => x[kt] != null)) ds.push({ label: "Target s.d. bulan ini", data: d.map(x => x[kt]), backgroundColor: WARNA.abu });
  buatGrafik(id, { type: "bar", data: { labels: d.map(x => x.nama.replace("Puskesmas ", "")), datasets: ds }, options: { indexAxis: "y" } });
}
function tabelCapaian(d) {
  const cols = [{ k: "nama", l: "Fasyankes" }, { k: "skrining", l: "Skrining" }, { k: "terduga", l: "Terduga" }, { k: "pct_terduga", l: "% Terduga (s.d. bln)", p: 1, dari: ["terduga", "t_terduga_sd"] },
    { k: "penemuan", l: "Penemuan" }, { k: "pct_penemuan", l: "% TC (thd target th)", p: 1, dari: ["penemuan", "t_penemuan"] }, { k: "enrolment", l: "Enrolment" }, { k: "pct_enrolment", l: "% Enrolment", p: 1, dari: ["enrolment", "penemuan"] },
    { k: "tb_anak", l: "TB Anak" }, { k: "tb03so_kasus", l: "Pasien TB" }, { k: "pct_hiv", l: "% Tahu HIV", p: 1, dari: ["tb03so_hiv_tahu", "tb03so_kasus"] }, { k: "pct_dm", l: "% Tahu DM", p: 1, dari: ["tb03so_dm_tahu", "tb03so_kasus"] },
    { k: "ik_indeks", l: "Kasus Indeks" }, { k: "ik_sudah", l: "Sudah IK" }, { k: "pct_ik", l: "% IK", p: 1, dari: ["ik_sudah", "ik_indeks"] }];
  return tabel(PPT.urut(d), cols, totalBaris(d, cols));
}
/* baris TOTAL: angka dijumlahkan, persentase dihitung ulang dari jumlahnya (bukan rata-rata persen) */
function totalBaris(d, cols) {
  const f = { nama: "TOTAL" };
  cols.forEach((c, i) => { if (!i) return; if (c.dari) { const a = jumlah(d, c.dari[0]), b = jumlah(d, c.dari[1]); f[c.k] = b ? 100 * a / b : null; } else if (c.jml) f[c.k] = Math.round(jumlah(d, c.jml)); else f[c.k] = jumlah(d, c.k); });
  return f;
}

/* ---------- halaman per indikator ---------- */
/* Rumus mengikuti slide Rakor Kapus & Data Zoom (lihat app/services/rekap.py). */
const CFG = {
  skrining: { judul: "Data Skrining", ind: "skrining", label: "Skrining", ppt: "skrining",
    ket: "Jumlah orang diskrining (satu baris Laporan Skrining = satu orang, dihitung per Unit Pelaksana). Sumber: Laporan Skrining SITB.",
    stat: (t) => [kartuStat("Total Skrining", t.skrining, "orang diskrining sesuai filter")],
    kolom: [{ k: "skrining", l: "Skrining" }] },
  terduga: { judul: "Data Terduga TBC", ind: "terduga", label: "Terduga TBC", ppt: "terduga",
    ket: "Terduga TBC = Status Diagnosis \"Sesuai standar\" (TB.06). Target s.d. bulan = target tahunan ÷ 12 × bulan data, dibulatkan ke puluhan seperti slide.",
    stat: (t, r) => [kartuStat("Terduga TBC", t.terduga, "sesuai standar"),
      kartuStat("Target Tahunan", Math.round(r.target_tahunan.terduga), "target 1 tahun"),
      kartuStat(`Target s.d. ${BLN[r.bulan_target - 1]}`, r.target_sd_bulan.terduga, `target ÷ 12 × ${r.bulan_target}`),
      kartuStat("Capaian", pct(r.persen.terduga), "terhadap target s.d. bulan ini", r.persen.terduga, null, "dari target s.d. bulan ini")],
    kolom: [{ k: "t_terduga", l: "Target Tahunan", bulat: 1 }, { k: "t_terduga_sd", l: "Target s.d. Bulan Ini" }, { k: "terduga", l: "Terduga" },
      { k: "pct_terduga", l: "Capaian s.d. Bulan (%)", p: 1, dari: ["terduga", "t_terduga_sd"] }, { k: "pct_terduga_th", l: "Capaian thd Target Tahunan (%)", p: 1, dari: ["terduga", "t_terduga"] }] },
  penemuan: { judul: "Penemuan Kasus", ind: "penemuan", label: "Penemuan Kasus", ppt: "penemuan", perkembangan: true,
    ket: "Penemuan kasus = kolom \"Terkonfirmasi TBC\" terisi (TB.06). Treatment coverage (TC) = penemuan ÷ target tahunan.",
    stat: (t, r) => [kartuStat("Penemuan Kasus", t.penemuan, "terkonfirmasi TBC"),
      kartuStat("Target Tahunan", Math.round(r.target_tahunan.penemuan), "target 1 tahun"),
      kartuStat("Treatment Coverage", pct(r.persen.penemuan), "penemuan ÷ target tahunan", r.persen.penemuan, null, "dari target tahunan"),
      kartuStat(`Capaian s.d. ${BLN[r.bulan_target - 1]}`, pct(r.persen.penemuan_sd), `target s.d. bulan: ${fmt(r.target_sd_bulan.penemuan)}`, r.persen.penemuan_sd, null, "dari target s.d. bulan ini")],
    kolom: [{ k: "t_penemuan", l: "Target Tahunan", bulat: 1 }, { k: "penemuan", l: "Penemuan" }, { k: "pct_penemuan", l: "Treatment Coverage (%)", p: 1, dari: ["penemuan", "t_penemuan"] },
      { k: "t_penemuan_sd", l: "Target s.d. Bulan Ini" }, { k: "pct_penemuan_sd", l: "Capaian s.d. Bulan (%)", p: 1, dari: ["penemuan", "t_penemuan_sd"] }] },
  tb_anak: { judul: "Penemuan TB Anak", ind: "tb_anak", label: "TB Anak", ppt: "tb_anak",
    ket: "TB anak = penemuan kasus dengan umur ≤ 14 tahun (TB.06). Target = target tahunan TB anak.",
    stat: (t, r) => [kartuStat("TB Anak (≤14 th)", t.tb_anak, "kasus anak ditemukan"),
      kartuStat("Target Tahunan", Math.round(r.target_tahunan.tb_anak), "target 1 tahun"),
      kartuStat("Capaian", pct(r.persen.tb_anak), "TB anak ÷ target tahunan", r.persen.tb_anak, null, "dari target tahunan")],
    kolom: [{ k: "t_tb_anak", l: "Target (Th)", bulat: 1 }, { k: "tb_anak", l: "Penemuan TB Anak" }, { k: "pct_tb_anak", l: "Capaian (%)", p: 1, dari: ["tb_anak", "t_tb_anak"] }] },
  enrolment: { judul: "Enrolment", ind: "enrolment", label: "Enrolment", ppt: "enrolment", target: "enrolment",
    ket: "Enrolment = penemuan kasus yang sudah memulai pengobatan (Tindak Lanjut \"Akan diobati\" dengan Tanggal Mulai Pengobatan terisi, atau \"Melanjutkan pengobatan\"). Persentase = enrolment ÷ penemuan kasus.",
    stat: (t, r) => [kartuStat("Enrolment", t.enrolment, "kasus sudah diobati"), kartuStat("Penemuan Kasus", t.penemuan, "terkonfirmasi TBC"),
      kartuStat("Capaian", pct(r.persen.enrolment), "enrolment ÷ penemuan", r.persen.enrolment, r.target_pct.enrolment)],
    kolom: [{ k: "penemuan", l: "Penemuan" }, { k: "enrolment", l: "Enrolment" }, { k: "pct_enrolment", l: "Capaian (%)", p: 1, dari: ["enrolment", "penemuan"] }] },
  hiv: { judul: "Pasien TBC Mengetahui Status HIV", ind: "tb03so_hiv_tahu", label: "Tahu Status HIV", ppt: "hiv", target: "hiv",
    ket: "Sumber TB.03SO. Jumlah pasien TB = semua pasien di register. Tahu status HIV = hasil tes HIV (Kolaborasi TBC-HIV) atau Status HIV berisi ODHIV / Bukan ODHIV.",
    stat: (t, r) => [kartuStat("Jumlah Pasien TB", t.tb03so_kasus, "pasien di TB.03SO"), kartuStat("Tahu Status HIV", t.tb03so_hiv_tahu, "ODHIV / Bukan ODHIV"),
      kartuStat("Belum Tahu Status", Math.max(t.tb03so_kasus - t.tb03so_hiv_tahu, 0), "perlu ditindaklanjuti"),
      kartuStat("Capaian", pct(r.persen.hiv), "tahu status ÷ jumlah pasien", r.persen.hiv, r.target_pct.hiv)],
    kolom: [{ k: "tb03so_kasus", l: "Jumlah Pasien TB" }, { k: "tb03so_hiv_tahu", l: "Tahu Status HIV" }, { k: "pct_hiv", l: "Capaian (%)", p: 1, dari: ["tb03so_hiv_tahu", "tb03so_kasus"] }] },
  dm: { judul: "Pasien TBC Mengetahui Status DM", ind: "tb03so_dm_tahu", label: "Tahu Status DM", ppt: "dm", target: "dm",
    ket: "Sumber TB.03SO. Tahu status DM = kolom DM (Kegiatan TBC-DM) berisi Positif atau Negatif.",
    stat: (t, r) => [kartuStat("Jumlah Pasien TB", t.tb03so_kasus, "pasien di TB.03SO"), kartuStat("Tahu Status DM", t.tb03so_dm_tahu, "Positif / Negatif"),
      kartuStat("Belum Tahu Status", Math.max(t.tb03so_kasus - t.tb03so_dm_tahu, 0), "perlu ditindaklanjuti"),
      kartuStat("Capaian", pct(r.persen.dm), "tahu status ÷ jumlah pasien", r.persen.dm, r.target_pct.dm)],
    kolom: [{ k: "tb03so_kasus", l: "Jumlah Pasien TB" }, { k: "tb03so_dm_tahu", l: "Tahu Status DM" }, { k: "pct_dm", l: "Capaian (%)", p: 1, dari: ["tb03so_dm_tahu", "tb03so_kasus"] }] },
  ik: { judul: "Investigasi Kontak", ind: "ik_sudah", label: "Sudah IK", ppt: "ik", donut: true, target: "ik",
    ket: "Sumber TB.16RK. Total kasus = jumlah kasus indeks; Sudah IK = Status IK \"Sudah IK\". Persentase = sudah IK ÷ total kasus.",
    stat: (t, r) => [kartuStat("Total Kasus Indeks", t.ik_indeks, "TB.16RK"), kartuStat("Sudah IK", t.ik_sudah, "sudah investigasi kontak"),
      kartuStat("Belum IK", Math.max(t.ik_indeks - t.ik_sudah, 0), "perlu ditindaklanjuti"),
      kartuStat("Capaian", pct(r.persen.ik), "sudah IK ÷ total kasus", r.persen.ik, r.target_pct.ik)],
    kolom: [{ k: "ik_indeks", l: "Total Kasus" }, { k: "ik_sudah", l: "Sudah IK" }, { k: "ik_belum", l: "Belum IK" }, { k: "pct_ik", l: "Persentase (%)", p: 1, dari: ["ik_sudah", "ik_indeks"] }] },
};
async function pgIndikator(c) {
  const [rg, rk, tr] = await Promise.all([api("/api/ringkasan", qs()), api("/api/rekap", qs()), trenData(c.ind)]);
  if (tidakAdaData(rg)) return $("#isi").innerHTML = kosong("Belum ada data untuk ditampilkan", "Unggah file Excel dari SITB atau ubah filter Anda.");
  const d = rk.data;
  d.forEach(r => c.kolom.forEach(x => { if (x.bulat) r[x.k + "_b"] = r[x.k] == null ? null : Math.round(r[x.k]); }));
  const cols = [{ k: "nama", l: "Fasyankes" }, ...c.kolom.map(x => x.bulat ? Object.assign({}, x, { k: x.k + "_b", jml: x.k }) : x)];
  const tgl = S.f.sampai && S.opsi.tanggal_akhir && S.f.sampai > S.opsi.tanggal_akhir ? S.opsi.tanggal_akhir : (S.f.sampai || S.opsi.tanggal_akhir);
  const sumberKosong = c.ppt == "hiv" || c.ppt == "dm" ? !rg.total.tb03so_kasus : c.ppt == "ik" ? !rg.total.ik_indeks : false;
  $("#isi").innerHTML = `
  <div class="grid kartu-grid">${c.stat(rg.total, rg).join("")}</div>
  <div class="catatan">${c.ket}</div>
  ${sumberKosong ? `<div class="catatan">Belum ada data ${c.ppt == "ik" ? "TB.16RK" : "TB.03SO"} yang aktif. Unggah laporan tersebut di menu Upload Data.</div>` : ""}
  <div class="grid dua" style="margin-top:12px">
    ${kartuGrafik("g-bln", "Perkembangan per Bulan", c.label)}
    ${c.donut ? kartuGrafik("g-donut", "Sudah dan Belum Investigasi Kontak", "") : ""}
  </div>
  <div class="grid" id="ppt-wadah" style="margin-top:16px"></div>
  ${c.perkembangan ? '<div class="grid" id="ppt-kembang" style="margin-top:16px"></div>' : ""}
  <div class="kartu" style="margin-top:16px"><h3>Tabel ${c.judul}</h3><div class="sub">Urutan puskesmas sama dengan slide Rakor. Baris TOTAL: persentase dihitung dari jumlah.</div>${tabel(PPT.urut(d), cols, totalBaris(d, cols))}</div>`;
  buatGrafik("g-bln", { type: "bar", data: { labels: tr.map(x => blnPendek(x.tanggal)), datasets: [{ label: c.label, data: tr.map(x => x.nilai), backgroundColor: WARNA.teal, borderRadius: 4 }] }, options: { plugins: { legend: { display: false } } } });
  if (c.donut) buatGrafik("g-donut", { type: "doughnut", data: { labels: ["Sudah IK", "Belum IK"], datasets: [{ data: [rg.total.ik_sudah, Math.max(rg.total.ik_indeks - rg.total.ik_sudah, 0)], backgroundColor: [WARNA.teal, WARNA.merah] }] }, options: { plugins: { legend: { display: true, position: "bottom" } } } });
  PPT.gambar($("#ppt-wadah"), c.ppt, d, { tgl, bulan: BLN[rg.bulan_target - 1], nBulan: rg.bulan_target, target: c.target ? rg.target_pct[c.target] : null });
  if (c.perkembangan) {
    const tp = await api("/api/tren-puskesmas", { indikator: "penemuan", dari: S.f.dari, sampai: S.f.sampai, puskesmas: S.f.puskesmas });
    if (tp.bulan.length && $("#ppt-kembang")) PPT.perkembangan($("#ppt-kembang"), tp, tgl);
  }
}

/* ---------- Sukses Rate (TSR) ---------- */
async function pgTsr() {
  const r = await api("/api/sukses-rate", { puskesmas: S.f.puskesmas });
  if (!r.data.length || !r.total.diobati) return $("#isi").innerHTML = kosong("Belum ada data sukses rate", "Unggah Data Zoom (lembar SUKSES RATE) atau TB.03SO kohort tahun sebelumnya.");
  const t = r.total, cols = [{ k: "nama", l: "Fasyankes" }, { k: "diobati", l: "Pasien Diobati" }, { k: "sembuh", l: "Sembuh" }, { k: "lengkap", l: "Pengobatan Lengkap" },
    { k: "gagal", l: "Gagal" }, { k: "meninggal", l: "Meninggal" }, { k: "ltfu", l: "Putus Berobat" }, { k: "tidak_evaluasi", l: "Tidak Dievaluasi/Pindah" },
    { k: "belum_evaluasi", l: "Belum Dievaluasi" }, { k: "pct", l: "Sukses Rate (%)", p: 1, dari: ["sukses", "diobati"] }];
  $("#isi").innerHTML = `<div class="grid kartu-grid">
     ${kartuStat("Pasien Diobati (kohort)", t.diobati, "pasien dievaluasi")}
     ${kartuStat("Sembuh + Lengkap", t.sukses, "pengobatan berhasil")}
     ${kartuStat("Belum Dievaluasi", t.belum_evaluasi, "mohon dicek")}
     ${kartuStat("Sukses Rate", pct(t.pct), "(sembuh + lengkap) ÷ diobati", t.pct, r.target)}</div>
   <div class="catatan">Sumber: ${esc(r.sumber)}. Sukses rate = (sembuh + pengobatan lengkap) ÷ pasien diobati. Target ${fmt(r.target)}%. Filter tanggal tidak berlaku untuk halaman ini (kohort tetap).</div>
   <div class="grid" id="ppt-wadah" style="margin-top:12px"></div>
   <div class="kartu" style="margin-top:16px"><h3>Tabel Sukses Rate</h3>${tabel(PPT.urut(r.data), cols, totalBaris(r.data, cols))}</div>`;
  PPT.gambar($("#ppt-wadah"), "tsr", r.data, { target: r.target, periode: r.sumber.split(" - ")[0] });
}

/* ---------- Capaian TPT (TB.15) ---------- */
async function pgTpt() {
  const r = await api("/api/tpt", { puskesmas: S.f.puskesmas });
  if (!r.data.length || !r.tanggal) return $("#isi").innerHTML = kosong("Belum ada data TPT", "Unggah laporan TB.15 (Pengobatan Pencegahan TBC) dari SITB.");
  const d = PPT.urut(r.data), tot = {}; r.kolom.forEach(k => tot[k] = jumlah(d, k));
  const sel = v => `<td class="${v ? "" : "nol"}">${fmt(v)}</td>`;
  $("#isi").innerHTML = `<div class="grid kartu-grid">${r.kolom.map((k, i) => kartuStat(r.label[i], tot[k], "orang menerima TPT")).join("")}</div>
   <div class="catatan">Sumber TB.15 periode ${esc(r.periode || "–")} (angka kumulatif periode laporan, filter tanggal tidak berlaku). Sel merah = 0 (belum ada capaian), seperti di slide.</div>
   <div class="kartu ppt" style="margin-top:12px"><div class="kartu-kepala"><div class="ppt-judul"><div class="l1">CAPAIAN TPT</div><div class="l3">(${esc(r.periode || "")})</div></div></div>
   <div class="tabel-wrap tabel-ppt"><table><thead><tr><th class="kiri" rowspan="2">Nama Fasyankes</th><th colspan="${r.kolom.length}">Jumlah Kontak Serumah/Kelompok Risiko Lainnya yang Mendapat TPT</th></tr>
   <tr>${["Kontak Serumah (anak usia < 5 th)", "Kontak Serumah (anak usia 5-14 th)", "Kontak Serumah Remaja & Dewasa (> 15 th)", "Kelompok Risiko Lainnya (semua umur)"].map(l => `<th style="white-space:normal;min-width:120px">${esc(l)}</th>`).join("")}</tr></thead>
   <tbody>${d.map(x => `<tr><td class="kiri">${esc(x.nama)}</td>${r.kolom.map(k => sel(x[k])).join("")}</tr>`).join("")}</tbody>
   <tfoot><tr><td class="kiri">TOTAL</td>${r.kolom.map(k => `<td>${fmt(tot[k])}</td>`).join("")}</tr></tfoot></table></div></div>
   <div class="grid" style="margin-top:16px">${kartuGrafik("g-tpt", "TPT per Puskesmas", "Jumlah penerima TPT per kategori", true)}</div>`;
  const warna = ["#4472C4", "#ED7D31", "#A5A5A5", "#FFC000"];
  buatGrafik("g-tpt", { type: "bar", data: { labels: d.map(x => PPT.label(x.nama)), datasets: r.kolom.map((k, i) => ({ label: r.label[i], data: d.map(x => x[k]), backgroundColor: warna[i] })) },
    options: { scales: { x: { stacked: true, ticks: { autoSkip: false, maxRotation: 45, minRotation: 45 } }, y: { stacked: true, beginAtZero: true } }, plugins: { legend: { display: true, position: "top" } } } });
}

/* ---------- Tren dan Analisis ---------- */
async function pgTren() {
  const pilih = S.trenPilih || ["skrining", "terduga", "penemuan"], per = S.trenPer || "bulan", kum = !!S.trenKum;
  $("#isi").innerHTML = `<div class="kartu"><h3>Pilih indikator</h3><div class="cek">${Object.entries(NAMA_IND).map(([k, v]) => `<label><input type="checkbox" value="${k}" ${pilih.includes(k) ? "checked" : ""}> ${v}</label>`).join("")}</div>
   <div class="tools"><label>Satuan waktu <select id="t-per"><option value="bulan" ${per == "bulan" ? "selected" : ""}>Per bulan</option><option value="hari" ${per == "hari" ? "selected" : ""}>Per hari</option></select></label>
   <label class="cek"><input type="checkbox" id="t-kum" ${kum ? "checked" : ""}> Tampilkan kumulatif</label><button class="btn teal" id="t-go">Tampilkan</button></div></div><div id="t-hasil"></div>`;
  $("#t-go").onclick = () => { S.trenPilih = [...document.querySelectorAll(".cek input[value]:checked")].map(x => x.value); S.trenPer = $("#t-per").value; S.trenKum = $("#t-kum").checked; pgTren(); };
  if (!pilih.length) return $("#t-hasil").innerHTML = '<div class="catatan">Pilih minimal satu indikator.</div>';
  const data = await Promise.all(pilih.map(k => api("/api/tren", { indikator: k, dari: S.f.dari, sampai: S.f.sampai, puskesmas: S.f.puskesmas, per })));
  if (data.every(d => !d.length)) return $("#t-hasil").innerHTML = kosong("Belum ada data", "Unggah data atau ubah filter.");
  $("#t-hasil").innerHTML = `<div class="grid dua" style="margin-top:16px">${pilih.map(k => kartuGrafik("tr-" + k, NAMA_IND[k], (per == "bulan" ? "Per bulan" : "Per hari") + (kum ? ", kumulatif" : ""))).join("")}</div>
   ${per == "bulan" ? `<div class="kartu" style="margin-top:16px"><h3>Perubahan dari Bulan ke Bulan</h3><div class="sub">Persentase dibanding bulan sebelumnya. Bulan terakhir bisa belum penuh karena data baru sampai tanggal tertentu.</div>${tabelPerubahan(pilih, data)}</div>` : ""}`;
  pilih.forEach((k, i) => { let v = data[i].map(x => x.nilai); if (kum) { let a = 0; v = v.map(x => a += x); }
    buatGrafik("tr-" + k, { type: "line", data: { labels: data[i].map(x => per == "bulan" ? blnPendek(x.tanggal) : x.tanggal), datasets: [{ label: NAMA_IND[k], data: v, borderColor: i % 2 ? WARNA.navy : WARNA.teal, backgroundColor: "rgba(20,184,166,.12)", fill: true, tension: .25, pointRadius: per == "hari" ? 0 : 3 }] } }); });
}
function tabelPerubahan(pilih, data) {
  const bl = [...new Set(data.flatMap(d => d.map(x => x.tanggal)))].sort(), peta = data.map(d => Object.fromEntries(d.map(x => [x.tanggal, x.nilai])));
  return `<div class="tabel-wrap"><table><thead><tr><th class="kiri">Bulan</th>${pilih.map(k => `<th>${NAMA_IND[k]}</th><th>Δ%</th>`).join("")}</tr></thead><tbody>${bl.map((b, j) => `<tr><td class="kiri">${blnPendek(b)}</td>${pilih.map((k, i) => { const v = peta[i][b] || 0, p = j ? (peta[i][bl[j - 1]] || 0) : 0; const d = j && p ? (100 * (v - p) / p) : null; return `<td>${fmt(v)}</td><td class="${d == null ? "" : d >= 0 ? "ok" : "bad"}">${d == null ? "–" : (d > 0 ? "+" : "") + fmt(d) + "%"}</td>`; }).join("")}</tr>`).join("")}</tbody></table></div>`;
}

/* ---------- Database ---------- */
async function pgDatabase() {
  const [db, rk] = await Promise.all([api("/api/database/ringkasan"), api("/api/rekap", { kelompok: "semua" })]);
  $("#isi").innerHTML = `<div class="grid kartu-grid">
   ${[["Batch pengolahan", db.batch], ["Batch aktif", db.batch_aktif], ["Baris angka agregat", db.fakta], ["Fasyankes tercatat", db.faskes], ["Riwayat dashboard lama", db.riwayat_lama]].map(([a, b]) => `<div class="kartu stat"><div class="t">${a}</div><div class="n">${fmt(b)}</div></div>`).join("")}</div>
   <div class="catatan">Database hanya menyimpan angka agregat. Nama, NIK, alamat, dan nomor telepon pasien tidak disimpan. Filter di atas tidak berlaku di halaman ini (selalu menampilkan semua fasyankes dan semua periode).</div>
   <div class="kartu"><h3>Data aktif per jenis laporan</h3>${tabel(db.per_jenis, [{ k: "nama", l: "Jenis laporan" }, { k: "batch_aktif", l: "Batch aktif" }, { k: "baris_agregat", l: "Baris agregat" }], null)}</div>
   <div class="kartu" style="margin-top:16px"><h3>Hasil pengolahan seluruh fasyankes</h3><div class="sub">Target hanya tersedia untuk 25 puskesmas.</div>${tabelCapaian(rk.data)}</div>`;
}

/* ---------- Data Target Puskesmas (CRUD) ---------- */
const IKON_EDIT = '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>';
const IKON_HAPUS = '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>';
const jsonOpt = (metode, data) => ({ method: metode, headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
let dataTarget = [], versiTarget = 0;

async function pgTarget() {
  const T = S.tgt = Object.assign({ q: "" }, S.tgt || {});
  $("#isi").innerHTML = `<div class="kartu">
   <div class="crud-kepala"><div><h3>Data Target Puskesmas</h3><div class="sub">Target tahunan tiap puskesmas. Dipakai dashboard untuk menghitung persentase capaian.</div></div>
    <div class="crud-alat"><input type="search" id="tg-cari" placeholder="Cari puskesmas…" aria-label="Cari puskesmas" value="${esc(T.q)}"><button class="btn tambah" id="tg-tambah" type="button">+ Tambah Data</button></div></div>
   <div id="tg-tabel"></div></div>`;
  let t; $("#tg-cari").oninput = e => { clearTimeout(t); t = setTimeout(() => { T.q = e.target.value.trim(); muatTarget(); }, 300); };
  $("#tg-tambah").onclick = () => formTarget(null);
  await muatTarget();
}
async function muatTarget() {
  const box = $("#tg-tabel"); if (!box) return;
  const v = ++versiTarget, q = (S.tgt || {}).q || "";
  const d = await api("/api/target", { q });
  if (v != versiTarget || !$("#tg-tabel")) return;   // hasil usang (pengguna sudah mengetik lagi / pindah halaman)
  dataTarget = d;
  box.innerHTML = d.length ? `<div class="tabel-wrap"><table><thead><tr><th class="kiri">No</th><th class="kiri">Puskesmas</th><th>Target Terduga / tahun</th><th>Target Penemuan / tahun</th><th>Target TB Anak / tahun</th><th class="aksi">Aksi</th></tr></thead><tbody>
    ${d.map((r, i) => `<tr><td class="kiri">${i + 1}</td><td class="kiri">${esc(r.nama)}</td><td>${fmt(r.terduga_tahunan)}</td><td>${fmt(r.penemuan_tahunan)}</td><td>${fmt(r.tb_anak_tahunan)}</td>
     <td class="aksi"><button class="ikon-btn" type="button" data-edit="${esc(r.key)}" title="Edit" aria-label="Edit ${esc(r.nama)}">${IKON_EDIT}</button><button class="ikon-btn hapus" type="button" data-hapus="${esc(r.key)}" title="Hapus" aria-label="Hapus ${esc(r.nama)}">${IKON_HAPUS}</button></td></tr>`).join("")}
    </tbody></table></div><div class="hal"><span class="muted">${fmt(d.length)} puskesmas${q ? ` ditemukan untuk “${esc(q)}”` : ""}</span></div>`
    : `<div class="kosong"><div class="ikon">🔍</div><p>${q ? `Tidak ada puskesmas yang cocok dengan “${esc(q)}”.` : "Belum ada data target. Klik “+ Tambah Data” untuk menambahkan."}</p></div>`;
  box.querySelectorAll("[data-edit]").forEach(b => b.onclick = () => formTarget(dataTarget.find(x => x.key == b.dataset.edit)));
  box.querySelectorAll("[data-hapus]").forEach(b => b.onclick = () => konfirmasiHapusTarget(dataTarget.find(x => x.key == b.dataset.hapus)));
}
function formTarget(r) {
  const edit = !!r, inti = edit ? r.nama.replace(/^Puskesmas\s+/i, "") : "";
  const angka = (id, label, nilai) => `<label for="${id}">${label} <span class="wajib">*</span><input type="number" id="${id}" min="0" step="1" inputmode="numeric" required value="${edit ? nilai : ""}" placeholder="Contoh: 100"><span class="pesan-salah" id="${id}-e" role="alert"></span></label>`;
  $("#modal-isi").innerHTML = `<h3 style="margin:0 0 4px;color:var(--navy)">${edit ? "Edit Data Target" : "Tambah Data Target"}</h3>
   <p class="muted" style="margin:0 0 14px;font-size:13.5px">Kolom bertanda <span class="wajib">*</span> wajib diisi.</p>
   <form class="form-crud" id="form-target" novalidate>
    <label for="ft-nama">Nama Puskesmas <span class="wajib">*</span><small>${edit ? "Nama tampilan saja; kunci pencocokan dengan laporan SITB tidak berubah." : "Tulis tanpa kata “Puskesmas”, contoh: Kalijambe."}</small><input type="text" id="ft-nama" maxlength="100" required autocomplete="off" value="${esc(inti)}" placeholder="Nama puskesmas"><span class="pesan-salah" id="ft-nama-e" role="alert"></span></label>
    ${angka("ft-td", "Target Terduga TBC per Tahun", edit ? r.terduga_tahunan : "")}
    ${angka("ft-pn", "Target Penemuan Kasus per Tahun", edit ? r.penemuan_tahunan : "")}
    ${angka("ft-ta", "Target TB Anak per Tahun", edit ? r.tb_anak_tahunan : "")}
    <div class="form-aksi"><button type="button" class="btn ghost" id="ft-batal">Batal</button><button type="submit" class="btn teal" id="ft-simpan">${edit ? "Simpan Perubahan" : "Simpan Data"}</button></div>
   </form>`;
  $("#modal").hidden = false; $("#ft-nama").focus();
  $("#ft-batal").onclick = () => $("#modal").hidden = true;
  const tandai = (id, pesan) => { $("#" + id).classList.toggle("salah", !!pesan); $("#" + id + "-e").textContent = pesan || ""; return !pesan; };
  const periksa = () => {
    let ok = true;
    ok = tandai("ft-nama", $("#ft-nama").value.trim().replace(/^puskesmas\s+/i, "") ? "" : "Nama puskesmas wajib diisi.") && ok;
    [["ft-td", "Target terduga"], ["ft-pn", "Target penemuan"], ["ft-ta", "Target TB anak"]].forEach(([id, l]) => {
      const v = $("#" + id).value.trim();
      ok = tandai(id, v === "" ? `${l} wajib diisi.` : (isNaN(+v) || +v < 0) ? `${l} harus berupa angka 0 atau lebih.` : "") && ok;
    });
    return ok;
  };
  ["ft-nama", "ft-td", "ft-pn", "ft-ta"].forEach(id => $("#" + id).addEventListener("input", () => $("#" + id).classList.remove("salah")));
  $("#form-target").onsubmit = async e => {
    e.preventDefault(); if (!periksa()) { toast("Periksa kembali isian yang ditandai merah.", true); return; }
    const data = { nama: $("#ft-nama").value.trim(), terduga_tahunan: +$("#ft-td").value, penemuan_tahunan: +$("#ft-pn").value, tb_anak_tahunan: +$("#ft-ta").value };
    const tombol = $("#ft-simpan"); tombol.disabled = true; tombol.textContent = "Menyimpan…";
    try {
      const hasil = await api(edit ? "/api/target/" + encodeURIComponent(r.key) : "/api/target", null, jsonOpt(edit ? "PUT" : "POST", data));
      $("#modal").hidden = true; toast(`Data ${hasil.nama} berhasil ${edit ? "diperbarui" : "ditambahkan"}.`);
      await segarTarget();
    } catch (err) { toast(err.message, true); tombol.disabled = false; tombol.textContent = edit ? "Simpan Perubahan" : "Simpan Data"; }
  };
}
function konfirmasiHapusTarget(r) {
  if (!r) return;
  $("#modal-isi").innerHTML = `<div class="konfirmasi-hapus"><div class="ikon">🗑️</div><h3 style="margin:0;text-align:center;color:var(--navy)">Hapus data target?</h3>
   <p style="text-align:center">Anda akan menghapus target <b>${esc(r.nama)}</b>. Puskesmas ini tidak akan muncul lagi pada filter dan perhitungan target di dashboard. Tindakan ini tidak dapat dibatalkan.</p>
   <div class="form-aksi" style="justify-content:center"><button type="button" class="btn ghost" id="hp-batal">Batal</button><button type="button" class="btn merah" id="hp-ya">Ya, Hapus</button></div></div>`;
  $("#modal").hidden = false; $("#hp-batal").focus();
  $("#hp-batal").onclick = () => $("#modal").hidden = true;
  $("#hp-ya").onclick = async () => {
    const t = $("#hp-ya"); t.disabled = true; t.textContent = "Menghapus…";
    try { const h = await api("/api/target/" + encodeURIComponent(r.key), null, { method: "DELETE" }); $("#modal").hidden = true; toast(`Data ${h.nama} berhasil dihapus.`); await segarTarget(); }
    catch (err) { toast(err.message, true); t.disabled = false; t.textContent = "Ya, Hapus"; }
  };
}
/* setelah tambah/ubah/hapus: tabel, filter puskesmas, dan dashboard ikut diperbarui */
async function segarTarget() {
  await muatOpsi();
  S.f.puskesmas = S.f.puskesmas.filter(k => S.opsi.puskesmas.some(p => p.key == k));
  $("#filter").innerHTML = "";   // dirender ulang dengan daftar puskesmas terbaru saat membuka halaman berfilter
  await muatTarget();
}

/* ---------- Riwayat Upload ---------- */
const NAMA_STATUS = { selesai: "Selesai", gagal: "Gagal", diproses: "Diproses", menunggu: "Menunggu", menunggu_konfirmasi: "Menunggu konfirmasi", dibatalkan: "Dibatalkan" };
async function pgRiwayat() {
  const R = S.riw = Object.assign({ q: "", jenis: "", status: "", hal: 1 }, S.riw || {}), per = 10;
  const r = await api("/api/batch", { q: R.q, jenis: R.jenis, status: R.status, halaman: R.hal, per_halaman: per });
  const hal = Math.max(1, Math.ceil(r.total / per));
  $("#isi").innerHTML = `<div class="kartu"><div class="tools"><input type="search" id="r-q" placeholder="Cari nama file…" value="${esc(R.q)}">
   <select id="r-j"><option value="">Semua jenis</option>${[["skrining", "Skrining"], ["tb06", "TB.06"], ["tb03so", "TB.03SO"], ["tb16rk", "TB.16RK"], ["tb15", "TB.15"], ["zoom", "Data Zoom"]].map(([a, b]) => `<option value="${a}" ${R.jenis == a ? "selected" : ""}>${b}</option>`).join("")}</select>
   <select id="r-s"><option value="">Semua status</option>${Object.entries(NAMA_STATUS).map(([a, b]) => `<option value="${a}" ${R.status == a ? "selected" : ""}>${b}</option>`).join("")}</select></div>
   ${r.data.length ? `<div class="tabel-wrap"><table><thead><tr><th class="kiri">Nama file</th><th class="kiri">Jenis laporan</th><th class="kiri">Diunggah</th><th class="kiri">Periode</th><th>Baris dibaca</th><th>Berhasil</th><th>Ditolak</th><th>Ganda dibuang</th><th class="kiri">Status</th><th></th></tr></thead><tbody>
   ${r.data.map(b => `<tr><td class="kiri">${b.berkas.map(x => esc(x.nama)).join("<br>")}</td><td class="kiri">${esc(b.nama_jenis)}</td><td class="kiri">${new Date(b.dibuat).toLocaleString("id-ID")}</td><td class="kiri">${esc(b.periode || "–")}</td><td>${fmt(b.baris_dibaca)}</td><td>${fmt(b.baris_berhasil)}</td><td>${fmt(b.baris_ditolak)}</td><td>${fmt(b.baris_ganda)}</td><td class="kiri"><span class="badge ${b.status}">${NAMA_STATUS[b.status] || b.status}</span>${b.aktif ? "" : b.diganti_oleh ? ' <span class="badge">diganti</span>' : ""}</td><td><button class="btn ghost kecil" data-detail="${b.id}">Detail</button></td></tr>`).join("")}</tbody></table></div>` : '<div class="kosong">Belum ada riwayat yang sesuai.</div>'}
   <div class="hal"><span class="muted">${fmt(r.total)} proses • halaman ${R.hal} dari ${hal}</span><button class="btn ghost kecil" id="r-prev" ${R.hal <= 1 ? "disabled" : ""}>‹ Sebelumnya</button><button class="btn ghost kecil" id="r-next" ${R.hal >= hal ? "disabled" : ""}>Berikutnya ›</button></div></div>`;
  let t; $("#r-q").oninput = e => { clearTimeout(t); t = setTimeout(() => { R.q = e.target.value; R.hal = 1; pgRiwayat(); }, 400); };
  $("#r-j").onchange = e => { R.jenis = e.target.value; R.hal = 1; pgRiwayat(); }; $("#r-s").onchange = e => { R.status = e.target.value; R.hal = 1; pgRiwayat(); };
  $("#r-prev").onclick = () => { R.hal--; pgRiwayat(); }; $("#r-next").onclick = () => { R.hal++; pgRiwayat(); };
  document.querySelectorAll("[data-detail]").forEach(b => b.onclick = () => detailBatch(b.dataset.detail));
}
async function detailBatch(id) {
  const [b, m] = await Promise.all([api("/api/batch/" + id), api(`/api/batch/${id}/masalah`)]);
  $("#modal-isi").innerHTML = `<h3 style="margin-top:0;color:var(--navy)">Detail Proses #${b.id} – ${esc(b.nama_jenis)}</h3>
   <p><span class="badge ${b.status}">${NAMA_STATUS[b.status] || b.status}</span> ${esc(b.pesan || "")}</p>
   <p class="muted">Periode: ${esc(b.periode || "–")} • Berhasil ${fmt(b.baris_berhasil)} • Ditolak ${fmt(b.baris_ditolak)} • Ganda dibuang ${fmt(b.baris_ganda)}</p>
   ${tabel(b.berkas.map(x => ({ nama: x.nama, ukuran: Math.round(x.ukuran / 1048576 * 10) / 10, baris: x.baris })), [{ k: "nama", l: "File" }, { k: "ukuran", l: "Ukuran (MB)" }, { k: "baris", l: "Baris" }], null)}
   <h4>Catatan validasi (${m.length})</h4>${m.length ? `<div class="tabel-wrap" style="max-height:220px"><table><thead><tr><th class="kiri">Baris</th><th class="kiri">Alasan</th></tr></thead><tbody>${m.slice(0, 200).map(x => `<tr><td class="kiri">${x.baris ?? "–"}</td><td class="kiri">${esc(x.pesan)}</td></tr>`).join("")}</tbody></table></div>` : '<p class="muted">Tidak ada masalah validasi.</p>'}
   <div class="tools"><a class="btn teal" href="/api/batch/${b.id}/masalah.xlsx">⬇ Unduh Laporan Validasi (Excel)</a></div>`;
  $("#modal").hidden = false;
}
$("#modal-tutup").onclick = $("#modal-kembali").onclick = () => $("#modal").hidden = true; $("#modal").onclick = e => { if (e.target.id == "modal") $("#modal").hidden = true; };


/* ---------- Contact Us ---------- */
const IK = (d) => `<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
const IKON_KONTAK = {
  instansi: IK('<path d="M3 21h18"/><path d="M5 21V10l7-5 7 5v11"/><path d="M10 21v-5h4v5"/>'),
  unit: IK('<circle cx="9" cy="8" r="3.2"/><path d="M3.5 19c.6-3 2.8-5 5.5-5s4.9 2 5.5 5"/><circle cx="17" cy="9" r="2.5"/><path d="M15.5 14.2c2.3.2 4 1.9 4.5 4.8"/>'),
  pengelola: IK('<circle cx="12" cy="8" r="3.6"/><path d="M5 20c.8-3.6 3.6-6 7-6s6.2 2.4 7 6"/>'),
  email: IK('<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3.5 6.5 8.5 6.5 8.5-6.5"/>'),
  telepon: IK('<path d="M5 4h3l2 5-2.5 1.5a11 11 0 0 0 6 6L15 14l5 2v3a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2"/>'),
  alamat: IK('<path d="M12 21s-6.5-6-6.5-11a6.5 6.5 0 0 1 13 0c0 5-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.4"/>'),
  website: IK('<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18"/>'),
  jam_layanan: IK('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
};
const KOLOM_KONTAK = [
  ["instansi", "Instansi", "[Nama Instansi]"], ["unit", "Unit Pengelola", "[Unit Pengelola]"], ["pengelola", "Pengelola Dashboard", "[Nama Pengelola]"],
  ["email", "Email", "[Alamat Email]"], ["telepon", "Telepon / WhatsApp", "[Nomor Kontak]"], ["alamat", "Alamat", "[Alamat Dinas Kesehatan Kabupaten Sragen]"],
  ["website", "Website", "[Alamat Website]"], ["jam_layanan", "Jam Layanan", "[Jam Layanan]"],
];
/* nomor 08xx / +62xx -> 628xx untuk tautan wa.me */
const nomorWa = t => { let d = String(t || "").replace(/\D/g, ""); if (d.startsWith("0")) d = "62" + d.slice(1); return d.length >= 8 ? d : ""; };
function tautanKontak(k, v) {
  if (!v) return null;
  if (k == "email") return "mailto:" + v;
  if (k == "telepon") { const w = nomorWa(v); return w ? "https://wa.me/" + w : "tel:" + v.replace(/\s/g, ""); }
  if (k == "alamat") return "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(v);
  if (k == "website") return v;
  return null;
}
async function pgKontak() {
  const k = await api("/api/kontak");
  const kartu = ([kunci, label, ph]) => {
    const v = k[kunci], url = tautanKontak(kunci, v), luar = url && /^https?:/.test(url);
    const isi = v
      ? (url ? `<a class="isi-k" href="${esc(url)}" ${luar ? 'target="_blank" rel="noopener"' : ""}>${esc(v)}</a>` : `<div class="isi-k">${esc(v)}</div>`)
      : `<div class="isi-k belum">${esc(ph)} <small>(belum diisi)</small></div>`;
    return `<div class="kontak-kartu"><div class="ikon-k">${IKON_KONTAK[kunci]}</div><div style="min-width:0"><div class="lbl-k">${esc(label)}</div>${isi}</div></div>`;
  };
  const wa = nomorWa(k.telepon);
  $("#isi").innerHTML = `<div class="kontak-kepala"><h2>Hubungi <em>Pengelola Dashboard</em></h2>
     <p>Untuk pertanyaan, masukan, atau bantuan terkait data dan penggunaan dashboard pemantauan program TBC Kabupaten Sragen.</p></div>
   <div class="kontak-grid">${KOLOM_KONTAK.map(kartu).join("")}</div>
   <div class="kontak-aksi">
     ${wa ? `<a class="btn wa" href="https://wa.me/${wa}?text=${encodeURIComponent("Halo, saya ingin bertanya tentang Dashboard TBC Kabupaten Sragen.")}" target="_blank" rel="noopener">💬 Chat WhatsApp</a>` : ""}
     ${k.email ? `<a class="btn teal" href="mailto:${esc(k.email)}?subject=${encodeURIComponent("Dashboard TBC Kabupaten Sragen")}">✉ Kirim Email</a>` : ""}
     <button class="btn ghost" id="kt-edit" type="button">✎ Edit Informasi Kontak</button></div>
   <div class="catatan" style="text-align:center;margin-top:18px">Kartu bertanda <i>(belum diisi)</i> dapat dilengkapi lewat tombol <b>Edit Informasi Kontak</b>. Perubahan langsung tersimpan di database.</div>`;
  $("#kt-edit").onclick = () => formKontak(k);
}
function formKontak(k) {
  const ket = { email: "Contoh: p2p.dinkes@sragenkab.go.id", telepon: "Contoh: 0812 3456 7890 (dipakai juga untuk tombol WhatsApp)", website: "Contoh: dinkes.sragenkab.go.id", jam_layanan: "Contoh: Senin - Jumat, 07.30 - 15.30 WIB" };
  $("#modal-isi").innerHTML = `<h3 style="margin:0 0 4px;color:var(--navy)">Edit Informasi Kontak</h3>
   <p class="muted" style="margin:0 0 14px;font-size:13.5px">Kosongkan isian yang belum diketahui; kartunya akan tampil "(belum diisi)".</p>
   <form class="form-crud" id="form-kontak" novalidate>
    ${KOLOM_KONTAK.map(([kunci, label, ph]) => `<label for="fk-${kunci}">${esc(label)}${ket[kunci] ? `<small>${esc(ket[kunci])}</small>` : ""}
      ${kunci == "alamat" ? `<textarea id="fk-${kunci}" rows="2" maxlength="300" placeholder="${esc(ph)}">${esc(k[kunci] || "")}</textarea>`
        : `<input type="${kunci == "email" ? "email" : kunci == "telepon" ? "tel" : "text"}" id="fk-${kunci}" maxlength="${kunci == "telepon" ? 40 : 200}" value="${esc(k[kunci] || "")}" placeholder="${esc(ph)}" autocomplete="off">`}</label>`).join("")}
    <div class="form-aksi"><button type="button" class="btn ghost" id="fk-batal">Batal</button><button type="submit" class="btn teal" id="fk-simpan">Simpan</button></div>
   </form>`;
  $("#modal").hidden = false; $("#fk-pengelola").focus();
  $("#fk-batal").onclick = () => $("#modal").hidden = true;
  $("#form-kontak").onsubmit = async e => {
    e.preventDefault();
    const data = Object.fromEntries(KOLOM_KONTAK.map(([kunci]) => [kunci, $("#fk-" + kunci).value.trim()]));
    const t = $("#fk-simpan"); t.disabled = true; t.textContent = "Menyimpan…";
    try { await api("/api/kontak", null, jsonOpt("PUT", data)); $("#modal").hidden = true; toast("Informasi kontak berhasil disimpan."); if (location.hash == "#kontak") pgKontak(); }
    catch (err) { toast(err.message, true); t.disabled = false; t.textContent = "Simpan"; }
  };
}

/* ---------- Upload Data ---------- */
let berkasPilih = [];
const mb = n => (n / 1048576).toFixed(1) + " MB";
async function pgUpload() {
  $("#isi").innerHTML = `<div class="kartu"><div class="drop" id="drop"><div class="ikon">📥</div><b>Seret dan lepas file Excel di sini</b><p class="muted">atau klik untuk memilih. Boleh banyak file sekaligus (.xlsx). Jenis laporan dikenali otomatis.</p><input type="file" id="berkas" multiple accept=".xlsx,.xlsm" hidden></div>
   <div class="daftar-file" id="daftar"></div><div class="tools"><button class="btn teal" id="kirim" disabled>Unggah dan Proses</button><button class="btn ghost" id="kosongkan" disabled>Kosongkan Pilihan</button></div>
   <div class="catatan">Jika periode laporan bertumpuk dengan data yang sudah aktif, sistem akan meminta Anda memilih <b>Ganti</b> (data lama tetap tersimpan sebagai riwayat) atau <b>Batalkan</b>. File yang sama persis tidak diproses dua kali. File Excel asli dihapus dari server setelah diolah.</div></div>
   <div id="hasil-upload"></div>`;
  const drop = $("#drop"), inp = $("#berkas");
  drop.onclick = () => inp.click(); inp.onchange = () => tambah([...inp.files]);
  ["dragover", "dragenter"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", e => tambah([...e.dataTransfer.files]));
  $("#kosongkan").onclick = () => { berkasPilih = []; segarDaftar(); }; $("#kirim").onclick = kirim; segarDaftar();
}
function tambah(fs) { fs.forEach(f => { if (!berkasPilih.some(x => x.name == f.name && x.size == f.size)) berkasPilih.push(f); }); segarDaftar(); }
function segarDaftar() {
  const d = $("#daftar"); if (!d) return;
  d.innerHTML = berkasPilih.map((f, i) => `<div><span>📄 ${esc(f.name)}</span><span class="muted">${mb(f.size)} <button class="btn ghost kecil" data-hapus="${i}">✕</button></span></div>`).join("");
  d.querySelectorAll("[data-hapus]").forEach(b => b.onclick = () => { berkasPilih.splice(+b.dataset.hapus, 1); segarDaftar(); });
  $("#kirim").disabled = $("#kosongkan").disabled = !berkasPilih.length;
}
async function kirim() {
  const fd = new FormData(); berkasPilih.forEach(f => fd.append("files", f)); fd.append("mode", "tambah");
  $("#kirim").disabled = true; $("#hasil-upload").innerHTML = '<div class="kartu"><div class="spin"></div><p class="muted" style="text-align:center">Mengunggah file…</p></div>';
  try { const r = await api("/api/upload", null, { method: "POST", body: fd }); berkasPilih = []; segarDaftar(); S.pantau = r.batch.map(b => b.id); tampilHasil(r); pantau(); }
  catch (e) { toast(e.message, true); $("#hasil-upload").innerHTML = ""; $("#kirim").disabled = false; }
}
function tampilHasil(r) {
  const lain = r.berkas.filter(x => !x.batch_id);
  $("#hasil-upload").innerHTML = `${lain.length ? `<div class="kartu" style="margin-top:16px"><h3>File yang tidak diproses</h3>${lain.map(x => `<div class="hasil-batch"><b>${esc(x.nama)}</b> <span class="badge ${x.status}">${{ duplikat: "Sudah pernah diunggah", ditolak: "Ditolak", tidak_dikenali: "Tidak dikenali" }[x.status] || x.status}</span><p class="muted" style="margin:6px 0 0">${esc(x.pesan || "")}</p></div>`).join("")}</div>` : ""}
   <div id="batch-box" style="margin-top:16px"></div>`;
  segarBatch(r.batch);
}
function segarBatch(bs) {
  const box = $("#batch-box"); if (!box) return;
  box.innerHTML = bs.map(b => `<div class="hasil-batch" id="b${b.id}"><h4>${esc(b.nama_jenis)} <span class="badge ${b.status}">${NAMA_STATUS[b.status] || b.status}</span></h4>
   <div class="muted">${b.berkas.map(x => esc(x.nama)).join(" • ")}${b.periode ? " • Periode " + esc(b.periode) : ""}</div>
   ${["diproses", "menunggu"].includes(b.status) ? `<div class="progres"><div style="width:${b.progres}%"></div></div><div class="muted">${b.progres}% • ${fmt(b.baris_dibaca)} baris dibaca</div>` : ""}
   ${b.status == "selesai" ? `<p>✅ ${fmt(b.baris_berhasil)} data berhasil diproses • ${fmt(b.baris_ditolak)} ditolak${b.baris_ganda ? ` • ${fmt(b.baris_ganda)} dibuang karena sama dengan file lain` : ""}.</p>` : ""}
   ${b.status == "gagal" ? `<p class="bad">❌ ${esc(b.pesan)}</p>` : ""}
   ${b.status == "menunggu_konfirmasi" ? `<p class="warn">⚠ ${esc(b.pesan)}</p><div class="tools"><button class="btn merah" data-k="ganti" data-id="${b.id}">Ganti Data Lama</button><button class="btn ghost" data-k="batal" data-id="${b.id}">Batalkan</button></div><div class="muted" style="font-size:12.5px">Opsi "tambahkan" tidak ditawarkan karena periodenya sudah ada dan akan membuat angka berlipat ganda.</div>` : ""}</div>`).join("");
  box.querySelectorAll("[data-k]").forEach(btn => btn.onclick = async () => {
    if (btn.dataset.k == "ganti" && !confirm("Data lama pada periode dan jenis laporan ini akan DIGANTI dengan data baru (data lama tetap tersimpan di riwayat). Lanjutkan?")) return;
    const fd = new FormData(); fd.append("aksi", btn.dataset.k);
    try { await api(`/api/batch/${btn.dataset.id}/konfirmasi`, null, { method: "POST", body: fd }); pantau(); } catch (e) { toast(e.message, true); }
  });
}
async function pantau() {
  clearTimeout(S.timer);
  if (location.hash != "#upload") return;
  const bs = await Promise.all((S.pantau || []).map(id => api("/api/batch/" + id))); segarBatch(bs);
  if (bs.some(b => ["diproses", "menunggu"].includes(b.status))) S.timer = setTimeout(pantau, 2000);
  else { await muatOpsi(); if (bs.some(b => b.status == "selesai")) toast("Pengolahan selesai. Dashboard sudah diperbarui."); const k = $("#kirim"); if (k) k.disabled = !berkasPilih.length; }
}

/* ---------- penggerak ---------- */
async function muatOpsi() {
  S.opsi = await api("/api/opsi-filter");
  $("#info-data").innerHTML = S.opsi.tanggal_akhir ? `Data sampai<br><b>${tglId(S.opsi.tanggal_akhir)}</b>` : "Belum ada data";
}
async function halaman() {
  clearTimeout(S.timer);
  const id = (location.hash || "#dashboard").slice(1), m = MENU.find(x => x[0] == id) || MENU[0];
  catatNav(m[0]); $("#kembali").hidden = m[0] == "dashboard";
  document.querySelectorAll("nav a").forEach(a => { const aktif = a.dataset.id == m[0]; a.classList.toggle("aktif", aktif); aktif ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current"); });
  try { tengahkanMenuAktif(); segarPanah(); } catch (e) { }
  $("#judul").textContent = m[0] == "dashboard" ? "TBC MONITORING DASHBOARD" : m[2];
  $("#subjudul").textContent = "KABUPATEN SRAGEN";
  const adaFilter = m[4]; $("#filter").hidden = !adaFilter || m[0] == "database";
  if (adaFilter && !$("#filter").hidden && !$("#f-tahun")) renderFilter();
  Object.values(S.charts).forEach(c => c.destroy()); S.charts = {};
  document.documentElement.classList.toggle("landing", m[0] == "dashboard"); $("#top").hidden = m[0] == "dashboard";
  $("#isi").before($("#filter"));
  loading();
  try { await m[3](); aktifkanReveal(); if (m[0] == "upload" && S.pantau) pantau(); window.scrollTo(0, 0); }
  catch (e) { $("#isi").innerHTML = `<div class="kartu kosong"><div class="ikon">⚠</div><h2>Terjadi kesalahan</h2><p>${esc(e.message)}</p><button class="btn teal" onclick="halaman()">Coba Lagi</button></div>`; }
  tutupMobile();
}
const SINGKAT = { dashboard: "Dashboard", upload: "Upload Data", skrining: "Skrining", terduga: "Terduga TBC", penemuan: "Penemuan Kasus", tb_anak: "TB Anak", enrolment: "Enrolment", hiv: "Status HIV", dm: "Status DM", tsr: "Sukses Rate", ik: "Investigasi Kontak", tpt: "TPT", tren: "Tren & Analisis", database: "Database", target: "Data Target", riwayat: "Riwayat Upload", kontak: "Contact Us" };
$("#nav").innerHTML = MENU.map(m => `<a href="#${m[0]}" data-id="${m[0]}" data-label="${SINGKAT[m[0]]}" aria-label="${SINGKAT[m[0]]}"><i aria-hidden="true">${m[1]}</i><span class="lbl">${SINGKAT[m[0]]}</span></a>`).join("");

/* ---------- sidebar (ciutkan/tampilkan, responsif) ---------- */
const MOBILE = window.matchMedia("(max-width:768px)"), TABLET = window.matchMedia("(max-width:1100px)");
const kunciPref = () => "sbKecil_" + (TABLET.matches ? "tablet" : "desktop");
const menuAtas = () => $("#app").classList.contains("menu-atas");
function aturSidebar(kecil, simpan) {
  if (menuAtas()) return;   // mode menu atas tidak mengenal mode ciut
  $("#app").classList.toggle("sb-kecil", kecil); $("#lipat").setAttribute("aria-expanded", String(!kecil));
  if (simpan) { try { localStorage.setItem(kunciPref(), kecil ? "1" : "0"); } catch (e) { } }
}
function sidebarAwal() {
  if (menuAtas()) { $("#app").classList.remove("sb-kecil"); return; }
  let p = null; try { p = localStorage.getItem(kunciPref()); } catch (e) { }
  aturSidebar(p == null ? TABLET.matches : p == "1", false);   // tablet: bawaan ciut, desktop: bawaan terbuka
}
function bukaMobile() { $("#sidebar").classList.add("buka"); $("#scrim").classList.add("buka"); $("#menu").setAttribute("aria-label", "Tutup menu"); }
function tutupMobile() { $("#sidebar").classList.remove("buka"); $("#scrim").classList.remove("buka"); $("#menu").setAttribute("aria-label", "Buka menu"); }
$("#menu").onclick = () => $("#sidebar").classList.contains("buka") ? tutupMobile() : bukaMobile();
$("#scrim").onclick = tutupMobile;
$("#lipat").onclick = () => MOBILE.matches ? tutupMobile() : aturSidebar(!$("#app").classList.contains("sb-kecil"), true);
$("#nav").addEventListener("click", e => { if (e.target.closest("a") && MOBILE.matches) tutupMobile(); });
[MOBILE, TABLET].forEach(q => q.addEventListener("change", () => { tutupMobile(); sidebarAwal(); }));
document.addEventListener("keydown", e => { if (e.key != "Escape") return; if (!$("#modal").hidden) $("#modal").hidden = true; else tutupMobile(); });
/* ---------- posisi menu: samping (sidebar) atau atas (bar melayang) ---------- */
function aturTata(atas, simpan) {
  $("#app").classList.toggle("menu-atas", atas);
  const teks = atas ? "Menu di samping" : "Menu di atas", b = $("#tata");
  $("#tata-teks").textContent = teks; b.dataset.label = teks; b.title = teks; b.setAttribute("aria-label", "Pindahkan " + teks.toLowerCase().replace("menu di", "menu ke"));
  sidebarAwal();
  if (typeof segarPanah == "function" && typeof navEl != "undefined") setTimeout(() => { segarPanah(); tengahkanMenuAktif(); }, 50);
  if (simpan) { try { localStorage.setItem("tataMenu", atas ? "atas" : "samping"); } catch (e) { } }
}
$("#tata").onclick = () => aturTata(!menuAtas(), true);
/* ---------- menu atas: satu baris, bisa digeser ke samping ---------- */
const navEl = $("#nav");
function segarPanah() {
  const aktif = menuAtas() && !MOBILE.matches, lebih = navEl.scrollWidth > navEl.clientWidth + 2;
  const kiri = $("#geser-kiri"), kanan = $("#geser-kanan");
  kiri.hidden = kanan.hidden = !(aktif && lebih);
  kiri.disabled = navEl.scrollLeft <= 2; kanan.disabled = navEl.scrollLeft + navEl.clientWidth >= navEl.scrollWidth - 2;
}
function tengahkanMenuAktif() {
  const a = navEl.querySelector("a.aktif"); if (!a || !menuAtas() || MOBILE.matches) return;
  const ar = a.getBoundingClientRect(), nr = navEl.getBoundingClientRect();
  if (ar.left < nr.left + 30 || ar.right > nr.right - 30) navEl.scrollLeft += (ar.left + ar.width / 2) - (nr.left + nr.width / 2);
}
$("#geser-kiri").onclick = () => navEl.scrollBy({ left: -navEl.clientWidth * 0.6, behavior: "smooth" });
$("#geser-kanan").onclick = () => navEl.scrollBy({ left: navEl.clientWidth * 0.6, behavior: "smooth" });
navEl.addEventListener("scroll", segarPanah, { passive: true });
navEl.addEventListener("wheel", e => {   // roda mouse naik/turun = geser menu ke kiri/kanan
  if (!menuAtas() || MOBILE.matches || navEl.scrollWidth <= navEl.clientWidth) return;
  if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) { navEl.scrollLeft += e.deltaY; e.preventDefault(); }
}, { passive: false });
window.addEventListener("resize", () => { segarPanah(); tengahkanMenuAktif(); });
{ let p = null; try { p = localStorage.getItem("tataMenu"); } catch (e) { } aturTata(p != "samping", false); }

/* ---------- tombol kembali ---------- */
const stackNav = [];   // halaman yang sudah dibuka; elemen terakhir = halaman sekarang
function catatNav(id) {
  if (S.dariKembali) { S.dariKembali = false; return; }
  if (stackNav[stackNav.length - 1] !== id) { stackNav.push(id); if (stackNav.length > 30) stackNav.shift(); }
}
function kembali() {
  stackNav.pop();
  const tujuan = stackNav[stackNav.length - 1] || "dashboard";   // tidak ada riwayat -> halaman utama
  if ("#" + tujuan === location.hash) return halaman();
  S.dariKembali = true; location.hash = "#" + tujuan;
}
$("#kembali").onclick = kembali;
window.addEventListener("hashchange", halaman);
muatOpsi().then(halaman).catch(e => { $("#isi").innerHTML = `<div class="kartu kosong"><h2>Server tidak dapat dihubungi</h2><p>${esc(e.message)}</p></div>`; });
