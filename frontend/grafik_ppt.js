"use strict";
/* ==========================================================================
   Grafik gaya slide "Rakor Kapus" (PowerPoint) untuk TBC Monitoring Sragen.
   - Kolom vertikal, warna Office (biru #4472C4, oranye #ED7D31, dst.)
   - Legenda di atas, judul tebal di tengah, "Data Table" di bawah grafik
   - Urutan puskesmas = urutan kecamatan seperti di slide (kecuali Skrining: terbanyak dulu)
   Dipakai langsung oleh app.js lewat window.PPT (bukan lagi menimpa fungsi lama),
   sehingga tidak bisa diam-diam kembali ke grafik lama bila ada kesalahan.
   ========================================================================== */
(function () {
  const W = { biru: "#4472C4", oranye: "#ED7D31", peach: "#F4B183", kuning: "#FFC000", merah: "#E5322D", ungu: "#7F60A8", abu: "#A5A5A5", biruTua: "#0070C0" };
  const T_BARIS = 18;   // tinggi satu baris tabel data (px)

  /* urutan puskesmas seperti di slide (urutan kecamatan), bukan abjad */
  const URUT = ["kalijambe", "plupuh i", "plupuh ii", "masaran i", "masaran ii", "kedawung i", "kedawung ii", "sambirejo", "gondang",
    "sambungmacan i", "sambungmacan ii", "ngrampal", "karangmalang", "sragen", "sidoharjo", "tanon i", "tanon ii", "gemolong",
    "miri", "sumberlawang", "mondokan", "sukodono", "gesi", "tangen", "jenar"];
  const inti = n => String(n || "").toLowerCase().replace(/^puskesmas\s+/, "").replace("karang malang", "karangmalang").replace(/\s+/g, " ").trim();
  const urut = d => [...d].sort((a, b) => {
    const i = URUT.indexOf(inti(a.nama)), j = URUT.indexOf(inti(b.nama));
    return (i < 0 ? 99 : i) - (j < 0 ? 99 : j) || String(a.nama).localeCompare(String(b.nama));
  });
  const label = n => String(n || "").replace(/^Puskesmas\s+/i, "");
  const f0 = v => v == null ? "–" : Number(v).toLocaleString("id-ID", { maximumFractionDigits: 0 });
  const fp = v => v == null ? "–" : Math.round(v) + "%";
  const persen = (a, b) => (b ? 100 * a / b : null);

  /* ---------- gaya ---------- */
  const st = document.createElement("style");
  st.textContent = `
  .kartu.ppt{padding:18px 18px 10px;grid-column:1/-1}
  .ppt .kartu-kepala{align-items:flex-start}
  .ppt-judul{flex:1;text-align:center;color:#111;line-height:1.25}
  .ppt-judul .l1,.ppt-judul .l2{font-weight:800;font-size:clamp(16px,2.1vw,24px);text-transform:uppercase}
  .ppt-judul .l3{font-weight:700;font-size:clamp(12.5px,1.4vw,15px);margin-top:2px}
  .ppt-geser{overflow-x:auto;padding-bottom:6px}
  .ppt-geser .chart-box{margin-top:6px}
  .ppt-multi{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,520px),1fr));gap:10px 18px;margin-top:8px}
  .ppt-multi .chart-box{height:300px}
  .ppt-legenda{display:flex;flex-wrap:wrap;gap:6px 14px;justify-content:center;font-size:11.5px;color:#404040;margin-top:6px}
  .ppt-legenda i{display:inline-block;width:10px;height:10px;margin-right:4px;vertical-align:-1px}
  .tabel-ppt th,.tabel-ppt td{font-size:12.5px}
  .tabel-ppt td.nol{background:#ffd6d6;color:#b00020}`;
  document.head.appendChild(st);

  /* ---------- plugin Chart.js ---------- */
  const NILAI = {   // angka di atas batang
    id: "nilaiBatang",
    afterDatasetsDraw(ch, _a, o) {
      if (!o || !o.tampil) return;
      const { ctx } = ch;
      ctx.save(); ctx.font = "10.5px 'Segoe UI',Calibri,sans-serif"; ctx.fillStyle = "#404040"; ctx.textAlign = "center"; ctx.textBaseline = "bottom";
      ch.data.datasets.forEach((ds, i) => {
        if (o.seri && !o.seri.includes(i)) return;
        const meta = ch.getDatasetMeta(i); if (meta.hidden) return;
        meta.data.forEach((bar, j) => { const v = ds.data[j]; if (v != null) ctx.fillText(o.fmt ? o.fmt(v) : v, bar.x, bar.y - 3); });
      });
      ctx.restore();
    }
  };
  const TABEL = {   // "Data Table" di bawah grafik; ikut tersimpan saat unduh PNG
    id: "tabelData",
    afterDatasetsDraw(ch, _a, o) {
      if (!o || !o.baris || !o.baris.length) return;
      const { ctx, chartArea: ca } = ch, x = ch.scales.x, n = ch.data.labels.length, H = T_BARIS;
      const px = ch.data.labels.map((_, i) => x.getPixelForValue(i));
      const lebar = n > 1 ? px[1] - px[0] : ca.right - ca.left;
      const y0 = x.bottom, kiri = 4, tinggi = o.baris.length * H;
      ctx.save(); ctx.strokeStyle = "#d0d0d0"; ctx.lineWidth = 1; ctx.beginPath();
      for (let r = 0; r <= o.baris.length; r++) { ctx.moveTo(kiri, y0 + r * H + .5); ctx.lineTo(ca.right, y0 + r * H + .5); }
      ctx.moveTo(kiri + .5, y0); ctx.lineTo(kiri + .5, y0 + tinggi);
      for (let i = 0; i <= n; i++) { const vx = Math.round(ca.left + i * lebar) + .5; ctx.moveTo(vx, y0); ctx.lineTo(vx, y0 + tinggi); }
      ctx.stroke();
      ctx.font = "10px 'Segoe UI',Calibri,sans-serif"; ctx.textBaseline = "middle";
      o.baris.forEach((b, r) => {
        const yc = y0 + r * H + H / 2;
        ctx.fillStyle = b.color; ctx.fillRect(kiri + 6, yc - 3.5, 7, 7);
        ctx.fillStyle = "#404040"; ctx.textAlign = "left"; ctx.fillText(b.label, kiri + 18, yc);
        ctx.textAlign = "center";
        b.data.forEach((v, i) => ctx.fillText(v == null ? "–" : b.fmt(v), px[i], yc));
      });
      ctx.restore();
    }
  };
  const GARIS_TARGET = {   // garis putus-putus target (mis. 95%, 100%)
    id: "garisTarget",
    afterDatasetsDraw(ch, _a, o) {
      if (!o || o.nilai == null) return;
      const { ctx, chartArea: ca } = ch, y = ch.scales.y.getPixelForValue(o.nilai);
      ctx.save(); ctx.strokeStyle = o.warna || "#C00000"; ctx.setLineDash([6, 4]); ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(ca.left, y); ctx.lineTo(ca.right, y); ctx.stroke();
      ctx.setLineDash([]); ctx.fillStyle = o.warna || "#C00000"; ctx.font = "bold 11px 'Segoe UI',sans-serif"; ctx.textAlign = "right"; ctx.textBaseline = "bottom";
      ctx.fillText(o.teks || ("Target " + o.nilai), ca.right - 2, y - 2); ctx.restore();
    }
  };

  /* ---------- konfigurasi grafik ---------- */
  function konfigurasi(s) {
    const tampil = s.seri.filter(x => !x.hanyaTabel), klaster = tampil.length > 1;
    const ds = tampil.map(x => ({
      label: x.label, data: x.data, backgroundColor: x.color, borderWidth: 0,
      barPercentage: klaster ? 0.85 : (s.lebarBatang || 0.55), categoryPercentage: klaster ? 0.8 : 0.9
    }));
    const baris = (s.tabel !== false && (klaster || s.tabel)) ? s.seri.map(x => ({ label: x.label, color: x.color, data: x.data, fmt: x.fmt || f0 })) : [];
    const kiri = baris.length ? 128 : 4;
    return {
      type: "bar", data: { labels: s.label, datasets: ds }, plugins: [NILAI, TABEL, GARIS_TARGET],
      options: {
        responsive: true, maintainAspectRatio: false, animation: { duration: 400 },
        layout: { padding: { left: kiri, right: 8, top: 14, bottom: baris.length ? baris.length * T_BARIS + 4 : 4 } },
        scales: {
          x: { grid: { display: false }, ticks: { autoSkip: false, maxRotation: s.miring ?? 45, minRotation: s.miring ?? 45, font: { size: 10.5 }, color: "#404040" } },
          y: Object.assign({ beginAtZero: true, border: { display: false }, grid: { color: "#d9d9d9" }, ticks: { font: { size: 10 }, color: "#595959" } }, s.sumbuY || {})
        },
        plugins: {
          legend: { display: klaster || !!s.legenda, position: "top", labels: { boxWidth: 10, boxHeight: 10, font: { size: 11 }, color: "#404040" } },
          tooltip: {
            callbacks: Object.assign({
              title: it => it.length ? (s.judulTooltip ? s.judulTooltip(it[0].dataIndex) : it[0].label) : "",
              label: c => `${c.dataset.label}: ${(s.seri.find(x => x.label == c.dataset.label)?.fmt || f0)(c.raw)}`
            }, s.footer ? { footer: it => it.length ? s.footer(it[0].dataIndex) : "" } : {})
          },
          nilaiBatang: { tampil: !!s.fmtNilai, fmt: s.fmtNilai, seri: s.seriNilai },
          tabelData: { baris },
          garisTarget: s.garis || {}
        }
      }
    };
  }

  /* ---------- kartu ---------- */
  function htmlKartu(s, tgl) {
    const thn = tgl ? tgl.split("-")[0] : String(new Date().getFullYear());
    const n = s.label.length, nBaris = (s.tabel !== false && (s.seri.filter(x => !x.hanyaTabel).length > 1 || s.tabel)) ? s.seri.length : 0;
    const sub = (s.sub || []).map(t => `<div class="l3">${esc(t)}</div>`).join("");
    const tinggi = (s.tinggi || 360) + 70 + nBaris * T_BARIS;
    return `<div class="kartu ppt" id="k-${s.id}"><div class="kartu-kepala"><div class="ppt-judul">
        <div class="l1">${esc(s.judul)}</div>${s.tanpaKab ? "" : `<div class="l2">KABUPATEN SRAGEN TAHUN ${esc(thn)}</div>`}${sub}
        <div class="l3">(${s.periode ? esc(s.periode) : "s.d. " + esc(tglId(tgl))})</div></div>
        <button class="btn ghost kecil" data-png="${s.id}" data-nama="${esc(s.judul)}">⬇ PNG</button></div>
      <div class="ppt-geser"><div style="min-width:${Math.max(860, n * (s.lebarKolom || 58) + 150)}px">
        <div class="chart-box" style="height:${tinggi}px"><canvas id="${s.id}"></canvas></div></div></div>
      ${s.catatan ? `<div class="muted" style="font-size:12px;text-align:center;margin-top:4px">${esc(s.catatan)}</div>` : ""}</div>`;
  }

  /* ---------- daftar grafik per halaman ---------- */
  function spesifikasi(k, data, ctx) {
    const d = urut(data), nama = d.map(x => label(x.nama)), B = (ctx.bulan || "").toUpperCase();
    const ambil = kol => d.map(x => x[kol]);
    const dua = (id, judul, kt, kv, lt, lv, warna2, opsi) => {
      const seri = [];
      if (kt && d.some(x => x[kt] != null)) seri.push({ label: lt, data: ambil(kt), color: W.biru });
      seri.push({ label: lv, data: ambil(kv), color: warna2 || W.oranye });
      return Object.assign({ id, judul, label: nama, seri, judulTooltip: i => d[i].nama }, opsi || {});
    };
    switch (k) {
      case "skrining": {   // slide 16: satu seri, terbanyak dulu, angka di atas batang
        const u = [...data].sort((a, b) => b.skrining - a.skrining);
        return [{ id: "g-ppt1", judul: "CAPAIAN SKRINING TB", label: u.map(x => /^puskesmas/i.test(x.nama) ? x.nama : "Puskesmas " + x.nama),
          seri: [{ label: "CAPAIAN", data: u.map(x => x.skrining), color: W.biru }], fmtNilai: f0, tabel: false, lebarBatang: 0.5 }];
      }
      case "terduga":      // slide 17 & 18
        return [dua("g-ppt1", "CAPAIAN TERDUGA TB", "t_terduga", "terduga", "TARGET TAHUNAN", "TERDUGA", W.oranye,
                    { seri: [{ label: "TARGET TAHUNAN", data: ambil("t_terduga"), color: W.biru }, { label: "TERDUGA", data: ambil("terduga"), color: W.oranye }],
                      footer: i => d[i].pct_terduga_th == null ? "" : "Capaian thd target tahunan: " + fmt(d[i].pct_terduga_th) + "%" }),
                dua("g-ppt2", "CAPAIAN TERDUGA TB (BULANAN)", "t_terduga_sd", "terduga", "TARGET S.D. " + B, "CAPAIAN S.D. " + B, W.oranye,
                    { footer: i => d[i].pct_terduga == null ? "" : "Capaian: " + fmt(d[i].pct_terduga) + "%",
                      catatan: `Target s.d. ${ctx.bulan} = target tahunan ÷ 12 × ${ctx.nBulan}, dibulatkan ke puluhan (sama seperti slide).` })];
      case "penemuan":     // slide 19 (+ slide 20-23 dibuat terpisah: perkembangan)
        return [dua("g-ppt1", "CAPAIAN PENEMUAN KASUS TB (TREATMENT COVERAGE)", "t_penemuan", "penemuan", "TARGET TAHUNAN", "PENEMUAN", W.oranye,
                    { footer: i => d[i].pct_penemuan == null ? "" : "Treatment coverage: " + fmt(d[i].pct_penemuan) + "%" })];
      case "tb_anak":      // slide 27
        return [dua("g-ppt1", "CAPAIAN PENEMUAN TB ANAK", "t_tb_anak", "tb_anak", "TARGET (Th)", "PENEMUAN", W.oranye,
                    { footer: i => d[i].pct_tb_anak == null ? "" : "Capaian: " + fmt(d[i].pct_tb_anak) + "%" })];
      case "enrolment": {  // slide 24
        const t = ctx.target || 95;
        return [{ id: "g-ppt1", judul: "PENEMUAN KASUS YANG DIOBATI OLEH PUSKESMAS", tanpaKab: false, sub: [`(Target ${t}%)`], label: nama,
          seri: [{ label: "ENROLLMENT KASUS", data: ambil("pct_enrolment"), color: W.biru, fmt: fp }], fmtNilai: fp, tabel: false, legenda: true,
          sumbuY: { min: 0, max: 110, ticks: { stepSize: 10, font: { size: 10 }, color: "#595959", callback: v => v > 100 ? "" : v + "%" } },
          garis: { nilai: t, teks: `Target ${t}%` },
          judulTooltip: i => d[i].nama, footer: i => `Diobati ${f0(d[i].enrolment)} dari ${f0(d[i].penemuan)} kasus` }];
      }
      case "hiv": case "dm": {   // slide 25 & 26
        const H = k == "hiv", kol = H ? "tb03so_hiv_tahu" : "tb03so_dm_tahu", kp = H ? "pct_hiv" : "pct_dm";
        return [{ id: "g-ppt1", judul: `CAPAIAN PASIEN TBC MENGETAHUI STATUS ${H ? "HIV" : "DM"}`, sub: [`TARGET ${ctx.target || 100}%`], label: nama,
          seri: [{ label: "JUMLAH PASIEN TB", data: ambil("tb03so_kasus"), color: W.biru },
                 { label: `TAU STATUS ${H ? "HIV" : "DM"}`, data: ambil(kol), color: W.peach },
                 { label: "PERSENTASE", data: ambil(kp), color: W.ungu, hanyaTabel: true, fmt: fp }],
          judulTooltip: i => d[i].nama, footer: i => d[i][kp] == null ? "" : "Capaian: " + fmt(d[i][kp]) + "%" }];
      }
      case "ik": {         // slide 30
        return [{ id: "g-ppt1", judul: "CAPAIAN INVESTIGASI KONTAK (IK)", label: nama, seri: [
          { label: "TOTAL KASUS", data: ambil("ik_indeks"), color: W.biru },
          { label: "SUDAH IK", data: ambil("ik_sudah"), color: W.kuning },
          { label: "BELUM IK", data: ambil("ik_belum"), color: W.merah },
          { label: "PERSENTASE", data: ambil("pct_ik"), color: W.ungu, hanyaTabel: true, fmt: fp }],
          judulTooltip: i => d[i].nama, footer: i => d[i].pct_ik == null ? "" : "Capaian IK: " + fmt(d[i].pct_ik) + "%" }];
      }
      case "tsr": {        // slide 28
        const t = ctx.target || 90;
        return [{ id: "g-ppt1", judul: "CAPAIAN SUKSES RATE", tanpaKab: true, sub: [`(Target ${t}%)`], periode: ctx.periode, label: nama, seri: [
          { label: "TARGET", data: d.map(() => t), color: W.biru },
          { label: "CAPAIAN", data: d.map(x => x.pct == null ? null : Math.round(x.pct * 10) / 10), color: W.kuning, fmt: v => fmt(Math.round(v)) },
          { label: "BELUM DI EVALUASI", data: ambil("belum_evaluasi"), color: W.merah }],
          fmtNilai: f0, seriNilai: [2], sumbuY: { min: 0, max: 100, ticks: { stepSize: 10, font: { size: 10 }, color: "#595959" } },
          judulTooltip: i => d[i].nama, footer: i => `Sembuh ${f0(d[i].sembuh)} + Lengkap ${f0(d[i].lengkap)} dari ${f0(d[i].diobati)} pasien` }];
      }
      default: return [];
    }
  }

  /* ---------- perkembangan penemuan per puskesmas (slide 20-23) ---------- */
  const GRADASI = ["#c6dbef", "#9ecae1", "#6baed6", "#4292c6", "#2171b5", "#a1d99b", "#74c476", "#41ab5d", "#fdae6b", "#fd8d3c", "#e6550d", "#a63603"];
  function perkembangan(wadah, tp, tgl) {
    const d = urut(tp.data), bulan = tp.bulan;
    const warna = bulan.map((_, i) => GRADASI[i % GRADASI.length]);
    const kelompok = []; for (let i = 0; i < d.length; i += 5) kelompok.push(d.slice(i, i + 5));
    const thn = tgl ? tgl.split("-")[0] : "";
    wadah.innerHTML = `<div class="kartu ppt"><div class="kartu-kepala"><div class="ppt-judul"><div class="l1">PERKEMBANGAN PENEMUAN KASUS TB (TREATMENT COVERAGE)</div>
       <div class="l2">KABUPATEN SRAGEN TAHUN ${esc(thn)}</div><div class="l3">Kumulatif per akhir bulan dibanding target tahunan (s.d. ${esc(tglId(tgl))})</div></div></div>
       <div class="ppt-legenda">${bulan.map((b, i) => `<span><i style="background:${warna[i]}"></i>PENEMUAN s.d. ${esc(blnPendek(b))}</span>`).join("")}<span><i style="background:${W.biruTua}"></i>TARGET</span></div>
       <div class="ppt-multi">${kelompok.map((_, i) => `<div><div class="chart-box"><canvas id="g-pk-${i}"></canvas></div></div>`).join("")}</div></div>`;
    kelompok.forEach((g, gi) => {
      const ds = bulan.map((b, bi) => ({ label: "s.d. " + blnPendek(b), data: g.map(x => x.nilai[bi]), backgroundColor: warna[bi], barPercentage: .95, categoryPercentage: .85 }));
      ds.push({ label: "TARGET", data: g.map(x => x.target), backgroundColor: W.biruTua, barPercentage: .95, categoryPercentage: .85 });
      buatGrafik("g-pk-" + gi, { type: "bar", data: { labels: g.map(x => label(x.nama)), datasets: ds },
        options: { plugins: { legend: { display: false }, tooltip: { mode: "index", intersect: false } },
          scales: { x: { grid: { display: false }, ticks: { font: { size: 11 }, color: "#404040" } }, y: { beginAtZero: true, grid: { color: "#e3e3e3" }, ticks: { font: { size: 10 } } } } } });
    });
  }

  /* ---------- API untuk app.js ---------- */
  window.PPT = {
    urut, label,
    /** Gambar semua grafik slide untuk halaman `k` di dalam elemen `wadah`. */
    gambar(wadah, k, data, ctx) {
      const spek = spesifikasi(k, data, ctx || {});
      wadah.innerHTML = spek.map(s => htmlKartu(s, (ctx || {}).tgl)).join("");
      spek.forEach(s => buatGrafik(s.id, konfigurasi(s)));
      return spek.length;
    },
    perkembangan
  };
})();
