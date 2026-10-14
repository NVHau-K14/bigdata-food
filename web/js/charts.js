/**
 * Vẽ biểu đồ và sơ đồ bằng SVG thuần, chạy offline, không phụ thuộc thư viện ngoài.
 * Mọi số đi qua FormatUtils (một hàm định dạng duy nhất) và mọi giá trị đến từ tham số dữ liệu truyền vào,
 * không viết cứng số liệu trong file này.
 * Màu: xanh lá đậm cho chuỗi chính, xám trung tính cho chuỗi đối chiếu (khác nhau rõ về độ sáng, đọc được ở thang xám);
 * cam chỉ dùng làm điểm nhấn nhỏ cho số dòng bị loại.
 */

(function (window) {
  "use strict";

  const F = window.FormatUtils;

  const T = {
    font: "'Source Sans 3', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
    text: "#182218",
    textSecondary: "#364336",
    grid: "#D8DFD8",
    axis: "#364336",
    primary: "#1A5336",   // xanh lá đậm: độ chói 0,076
    neutral: "#858A85",   // xám trung tính: độ chói khoảng 0,25, tương phản 3,5:1 với nền trắng
    track: "#EEF2EE",
    accent: "#B24E10"     // cam: điểm nhấn nhỏ
  };

  function el(tag, attrs, text) {
    const e = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs || {})) e.setAttribute(k, v);
    if (text !== undefined) e.textContent = text;
    return e;
  }

  function makeSvg(container, minW, minH) {
    container.innerHTML = "";
    const rect = container.getBoundingClientRect();
    const width = Math.max(rect.width || minW, minW);
    const height = Math.max(rect.height || minH, minH);
    const svg = el("svg", {
      width: "100%",
      height: "100%",
      viewBox: `0 0 ${width} ${height}`,
      preserveAspectRatio: "xMinYMin meet",
      style: `font-family: ${T.font}; display: block;`
    });
    container.appendChild(svg);
    return { svg, width, height };
  }

  function txt(svg, x, y, content, opts) {
    const o = Object.assign({ size: 13, weight: 400, fill: T.text, anchor: "start" }, opts || {});
    svg.appendChild(el("text", {
      x, y, fill: o.fill, "font-size": o.size, "font-weight": o.weight, "text-anchor": o.anchor
    }, content));
  }

  // =========================================================================
  // Trang 1: phễu làm sạch dữ liệu
  // =========================================================================
  function funnelRows(branch, steps, ctx) {
    const labels = {
      vifoodrec: {
        raw: "Dữ liệu thô",
        scale: "Lọc thang điểm",
        fk: "Khóa ngoại với danh mục món",
        kcore: "Lọc K-core"
      },
      food_com: {
        raw: "Dữ liệu thô",
        zero: "Loại điểm 0",
        kcore: "Lọc K-core"
      }
    }[branch];

    return steps.map((s, i) => {
      let note = "";
      if (s.key === "scale") {
        note = s.dropped > 0
          ? `Loại ${F.fmt(s.dropped)} dòng`
          : `Giữ cả ${F.fmt(s.levels)} mức điểm ${F.fmt(ctx.ratingMin, 1)} đến ${F.fmt(ctx.ratingMax, 1)}`;
      } else if (s.key === "fk") {
        note = s.dropped > 0 ? `Loại ${F.fmt(s.dropped)} dòng có mã món ngoài danh mục` : "Không loại dòng nào";
      } else if (s.key === "zero") {
        note = `Loại ${F.fmt(s.dropped)} dòng có điểm 0`;
      } else if (s.key === "kcore") {
        note = s.dropped > 0
          ? `Loại ${F.fmt(s.dropped)} dòng sau ${F.fmt(s.rounds)} vòng`
          : `Đã hội tụ sau ${F.fmt(s.rounds)} vòng`;
      }
      return { label: labels[s.key], count: s.count, dropped: s.dropped, note, isLast: i === steps.length - 1 };
    });
  }

  function renderCleaningFunnel(containerId, funnel, ctx) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const { svg, width, height } = makeSvg(container, 520, 320);

    const branches = [
      { title: "ViFoodRec", rows: funnelRows("vifoodrec", funnel.vifoodrec, ctx), color: T.primary },
      { title: "Food.com", rows: funnelRows("food_com", funnel.food_com, ctx), color: T.neutral }
    ];

    const pad = { top: 6, left: 4, right: 8 };
    const labelW = Math.min(200, width * 0.27);
    const barX = pad.left + labelW;
    const barW = Math.min(170, width * 0.22);
    const countX = barX + barW + 12;
    const noteX = countX + 78;

    // Chiều cao mỗi nhánh theo số hàng, nhánh dùng hết chiều cao khả dụng
    const totalRows = branches.reduce((n, b) => n + b.rows.length, 0);
    const titleH = 26;
    const gapBranch = 14;
    const avail = height - pad.top - 2 * titleH - gapBranch;
    const rowH = Math.min(62, avail / totalRows);
    const barH = Math.min(26, rowH * 0.55);

    let y = pad.top;
    branches.forEach((b, bi) => {
      txt(svg, pad.left, y + 18, `${b.title}: thanh so với số dòng thô của chính bộ`, { size: 15, weight: 700 });
      y += titleH;
      b.rows.forEach((r) => {
        const cy = y + (rowH - barH) / 2;
        txt(svg, pad.left, cy + barH - 5, r.label, { size: 13.5, weight: 500 });
        svg.appendChild(el("rect", { x: barX, y: cy, width: barW, height: barH, fill: T.track, rx: 2 }));
        svg.appendChild(el("rect", {
          x: barX, y: cy, width: Math.max((r.count / b.rows[0].count) * barW, 3), height: barH, fill: b.color, rx: 2
        }));
        txt(svg, countX, cy + barH - 5, F.fmt(r.count), { size: 13.5, weight: 600 });
        if (r.note) {
          txt(svg, noteX, cy + barH - 5, r.note, {
            size: 13, weight: r.dropped > 0 ? 600 : 500, fill: r.dropped > 0 ? T.accent : T.primary
          });
        }
        y += rowH;
      });
      if (bi === 0) {
        svg.appendChild(el("line", {
          x1: pad.left, y1: y + gapBranch / 2, x2: width - pad.right, y2: y + gapBranch / 2,
          stroke: T.grid, "stroke-width": 1
        }));
        y += gapBranch;
      }
    });
  }

  // =========================================================================
  // Trang 1: phân phối điểm đánh giá
  // =========================================================================
  function renderRatingDist(containerId, vnDist, fcDist) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const { svg, width, height } = makeSvg(container, 380, 200);

    // Chung một thang trục y cho hai bộ để so sánh công bằng
    const maxPct = Math.max(...vnDist.map((d) => d.pct), ...fcDist.map((d) => d.pct));
    const yMax = Math.ceil(maxPct / 20) * 20;
    const gap = 16;
    const total = vnDist.length + fcDist.length;
    const plotW = width - 34 - gap;
    const vnW = (plotW * vnDist.length) / total;
    const fcW = plotW - vnW;
    const pad = { top: 26, bottom: 28 };
    const chartH = height - pad.top - pad.bottom;

    function sub(offsetX, w, title, data, color, decimals) {
      txt(svg, offsetX, 14, title, { size: 14, weight: 700 });
      const slot = w / data.length;
      const barW = Math.max(slot * 0.68, 6);
      [0, yMax / 2, yMax].forEach((tick) => {
        const y = pad.top + chartH - (tick / yMax) * chartH;
        svg.appendChild(el("line", { x1: offsetX, y1: y, x2: offsetX + w, y2: y, stroke: T.grid, "stroke-width": 1 }));
        if (offsetX < 40) txt(svg, offsetX - 4, y + 4, F.fmtPct(tick, 0), { size: 12, anchor: "end", fill: T.textSecondary });
      });
      svg.appendChild(el("line", {
        x1: offsetX, y1: pad.top + chartH, x2: offsetX + w, y2: pad.top + chartH, stroke: T.axis, "stroke-width": 1
      }));
      data.forEach((d, i) => {
        const h = Math.max((d.pct / yMax) * chartH, 2);
        const x = offsetX + i * slot + (slot - barW) / 2;
        const y = pad.top + chartH - h;
        svg.appendChild(el("rect", { x, y, width: barW, height: h, fill: color }));
        txt(svg, x + barW / 2, pad.top + chartH + 16, F.fmt(d.rating, decimals), {
          size: 12.5, weight: 500, anchor: "middle"
        });
        if (d.pct >= 30) {
          txt(svg, x + barW / 2, y - 4, F.fmtPct(d.pct, 1), { size: 12.5, weight: 700, anchor: "middle" });
        }
      });
    }

    sub(34, vnW, "ViFoodRec: phần trăm đánh giá theo mức điểm", vnDist, T.primary, 1);
    sub(34 + vnW + gap, fcW, "Food.com", fcDist, T.neutral, 0);
  }

  // =========================================================================
  // Trang 2: sơ đồ kiến trúc, biểu đồ lưu trữ, biểu đồ mở rộng quy mô
  // =========================================================================
  function renderArchitecture(containerId, info) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const { svg, width, height } = makeSvg(container, 520, 180);

    const hd = info.hdfs;
    const sp = info.spark;
    const fsckAll = hd.fsck.map((f) => f.under_replicated).reduce((a, b) => a + b, 0);
    const fsckOk = hd.fsck.every((f) => f.status === "HEALTHY");

    const stages = [
      { title: "Nguồn thô", tech: "CSV", detail: ["RAW_recipes", "RAW_interactions", "foods", "ratings"], color: T.axis },
      {
        title: "Lưu trữ", tech: `HDFS ${hd.version}`,
        detail: [`${F.fmt(hd.namenodes)} NameNode`, `${F.fmt(hd.datanodes)} DataNode`, `Replication ${F.fmt(hd.replication)}`,
          `fsck ${fsckOk ? "HEALTHY" : "có lỗi"}`, `Thiếu bản sao ${F.fmt(fsckAll)}`],
        color: T.primary
      },
      {
        title: "Xử lý", tech: `Spark ${sp.version}`,
        detail: [`${F.fmt(sp.masters)} Master`, `${F.fmt(sp.workers)} Worker`, `${F.fmt(sp.worker_cores)} nhân mỗi Worker`,
          `${F.fmt(sp.worker_ram_mb / 1000, 1)} GB mỗi Worker`, `Tổng ${F.fmt(sp.total_cores)} nhân, ${F.fmt(sp.total_ram_mb / 1000, 0)} GB`],
        color: T.primary
      },
      { title: "Kết quả", tech: "Parquet Snappy", detail: ["Nén nhỏ hơn CSV", "Lưu theo cột", "Đọc nhanh hơn"], color: T.neutral },
      { title: "Trình diễn", tech: "Dashboard web", detail: ["HTML, CSS, JS", "Chạy offline"], color: T.primary }
    ];

    const n = stages.length;
    const gap = 18;
    const boxW = (width - 4 - gap * (n - 1)) / n;
    const maxLines = Math.max(...stages.map((x) => x.detail.length));
    // Hệ số phóng theo chiều cao khung: màn hình cao thì khối và chữ lớn hơn, không để khối rỗng
    const k = Math.min(1.6, Math.max(1, height / 178));
    const headH = 26 * k;
    const lineH = 20 * k;
    const boxH = Math.min(height, headH + 30 * k + maxLines * lineH + 12 * k);
    const y0 = Math.max((height - boxH) / 2, 0);

    stages.forEach((s, i) => {
      const x = 2 + i * (boxW + gap);
      svg.appendChild(el("rect", { x, y: y0, width: boxW, height: boxH, fill: "#FFFFFF", stroke: s.color, "stroke-width": 1.5 }));
      svg.appendChild(el("rect", { x, y: y0, width: boxW, height: headH, fill: s.color }));
      txt(svg, x + boxW / 2, y0 + headH * 0.68, s.title, { size: 13.5 * k, weight: 700, fill: "#FFFFFF", anchor: "middle" });
      txt(svg, x + 8, y0 + headH + 20 * k, s.tech, { size: 14 * k, weight: 700, fill: s.color === T.neutral ? T.text : s.color });
      s.detail.forEach((d, j) => {
        txt(svg, x + 8, y0 + headH + 20 * k + 22 * k + j * lineH, d, { size: 12 * k, weight: 400 });
      });
      if (i < n - 1) {
        const ax1 = x + boxW + 3;
        const ax2 = x + boxW + gap - 3;
        const ay = y0 + boxH / 2;
        svg.appendChild(el("line", { x1: ax1, y1: ay, x2: ax2 - 4, y2: ay, stroke: T.axis, "stroke-width": 1.5 }));
        svg.appendChild(el("polygon", {
          points: `${ax2},${ay} ${ax2 - 6},${ay - 4} ${ax2 - 6},${ay + 4}`, fill: T.axis
        }));
      }
    });
  }

  function renderStorageRatios(containerId, rows) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const { svg, width, height } = makeSvg(container, 320, 110);
    const maxRatio = Math.max(...rows.map((r) => r.ratio));
    const labelW = 120;
    const valW = 70;
    const barMax = width - labelW - valW - 8;
    const rowH = Math.min(64, (height - 4) / rows.length);
    const fs = rowH > 50 ? 16 : (rowH > 34 ? 15 : 13);
    rows.forEach((r, i) => {
      const y = 2 + i * rowH;
      const bh = Math.min(34, rowH * 0.6);
      txt(svg, 0, y + bh - 2, r.label, { size: fs });
      svg.appendChild(el("rect", {
        x: labelW, y, width: Math.max((r.ratio / maxRatio) * barMax, 3), height: bh, fill: T.primary
      }));
      txt(svg, labelW + (r.ratio / maxRatio) * barMax + 6, y + bh - 2, `${F.fmt(r.ratio, 2)} lần`, { size: fs, weight: 700 });
    });
  }

  // "2 Workers (4 Cores)" trong dữ liệu nguồn thành "2 Worker, 4 nhân"
  function resourceLabel(res) {
    const m = /(\d+) Workers? \((\d+) Cores?\)/.exec(res);
    return m ? `${m[1]} Worker, ${m[2]} nhân` : res;
  }

  function renderScalability(containerId, points) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const { svg, width, height } = makeSvg(container, 360, 200);

    const resources = [...new Set(points.map((p) => p.resource))];
    const ratios = [...new Set(points.map((p) => p.ratio))];
    const pad = { top: 34, bottom: 34, left: 46, right: 24 };
    const chartW = width - pad.left - pad.right;
    const chartH = height - pad.top - pad.bottom;
    const maxT = Math.ceil(Math.max(...points.map((p) => p.avg_time)) / 5) * 5;

    for (let s = 0; s <= maxT; s += 5) {
      const y = pad.top + chartH - (s / maxT) * chartH;
      svg.appendChild(el("line", { x1: pad.left, y1: y, x2: pad.left + chartW, y2: y, stroke: T.grid, "stroke-width": 1 }));
      txt(svg, pad.left - 6, y + 4, F.fmtUnit(s, "s", 0), { size: 12, anchor: "end", fill: T.textSecondary });
    }
    svg.appendChild(el("line", {
      x1: pad.left, y1: pad.top + chartH, x2: pad.left + chartW, y2: pad.top + chartH, stroke: T.axis, "stroke-width": 1
    }));

    const colors = [T.primary, T.neutral];
    resources.forEach((res, ri) => {
      const series = ratios.map((r) => points.find((p) => p.resource === res && p.ratio === r));
      let d = "";
      series.forEach((p, i) => {
        const x = pad.left + (i / (ratios.length - 1)) * chartW;
        const y = pad.top + chartH - (p.avg_time / maxT) * chartH;
        d += (i === 0 ? "M " : " L ") + `${x} ${y}`;
      });
      svg.appendChild(el("path", {
        d, fill: "none", stroke: colors[ri % 2], "stroke-width": 2.5, "stroke-dasharray": ri === 0 ? "none" : "6 4"
      }));
      series.forEach((p, i) => {
        const x = pad.left + (i / (ratios.length - 1)) * chartW;
        const y = pad.top + chartH - (p.avg_time / maxT) * chartH;
        svg.appendChild(el("circle", { cx: x, cy: y, r: 4, fill: colors[ri % 2] }));
        // Nhãn của chuỗi cao hơn đặt phía trên điểm, của chuỗi thấp hơn đặt phía dưới, để không chồng nhau
        const others = resources.filter((r2) => r2 !== res).map((r2) => points.find((q) => q.resource === r2 && q.ratio === p.ratio).avg_time);
        const above = others.every((o) => p.avg_time >= o);
        const anchor = i === 0 ? "start" : (i === ratios.length - 1 ? "end" : "middle");
        txt(svg, x + (i === 0 ? 8 : (i === ratios.length - 1 ? -4 : 0)), y + (above ? -10 : 19), F.fmtUnit(p.avg_time, "s", 1), { size: 12, weight: 700, anchor });
      });
      // Chú thích chuỗi
      const lx = pad.left + ri * 190;
      svg.appendChild(el("line", {
        x1: lx, y1: 14, x2: lx + 26, y2: 14, stroke: colors[ri % 2], "stroke-width": 2.5, "stroke-dasharray": ri === 0 ? "none" : "6 4"
      }));
      txt(svg, lx + 32, 18, resourceLabel(res), { size: 13, weight: 600 });
    });

    ratios.forEach((r, i) => {
      const x = pad.left + (i / (ratios.length - 1)) * chartW;
      const rows = points.find((p) => p.ratio === r).rows;
      const anchor = i === 0 ? "start" : (i === ratios.length - 1 ? "end" : "middle");
      const dx = i === 0 ? -pad.left + 6 : (i === ratios.length - 1 ? 6 : 0);
      txt(svg, x + dx, pad.top + chartH + 16, r, { size: 13, weight: 600, anchor });
      txt(svg, x + dx, pad.top + chartH + 30, `${F.fmt(rows)} dòng`, { size: 11.5, anchor, fill: T.textSecondary });
    });
  }

  // =========================================================================
  // Trang 3: độ lệch đặc trưng của cụm so với trung bình hệ thống
  // =========================================================================
  function renderClusterDeviation(containerId, features, banner) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const { svg, width, height } = makeSvg(container, 480, 260);

    const topPad = banner ? 56 : 14;
    if (banner) {
      svg.appendChild(el("rect", { x: 0, y: 4, width: width - 2, height: 44, fill: "#F5F7F5", stroke: T.grid, "stroke-width": 1 }));
      const lines = Array.isArray(banner) ? banner : [banner];
      lines.forEach((line, i) => txt(svg, 10, 22 + i * 18, line, { size: 13, weight: i === 0 ? 700 : 400 }));
    }

    const pad = { top: topPad, bottom: 30, left: 250, right: 40 };
    const chartW = width - pad.left - pad.right;
    const chartH = height - pad.top - pad.bottom;
    const maxAbs = Math.max(...features.map((f) => Math.abs(f.devPct)), 10);
    const axisMax = Math.max(Math.ceil(maxAbs / 10) * 10, 10);
    const midX = pad.left + chartW / 2;
    const scale = chartW / 2 / axisMax;

    const ticks = [-axisMax, -axisMax / 2, 0, axisMax / 2, axisMax];
    ticks.forEach((tv) => {
      const x = midX + tv * scale;
      svg.appendChild(el("line", {
        x1: x, y1: pad.top, x2: x, y2: pad.top + chartH,
        stroke: tv === 0 ? T.axis : T.grid, "stroke-width": tv === 0 ? 1.5 : 1
      }));
      txt(svg, x, pad.top + chartH + 18, tv === 0 ? "0%" : F.fmtSigned(tv, 0), { size: 12, anchor: "middle", fill: T.textSecondary });
    });

    const rowH = chartH / features.length;
    const barH = Math.min(22, rowH * 0.6);
    features.forEach((f, i) => {
      const y = pad.top + i * rowH + (rowH - barH) / 2;
      txt(svg, pad.left - 12, y + barH - 5, f.name, { size: 13.5, weight: 600, anchor: "end" });
      const len = Math.abs(f.devPct) * scale;
      const x = f.devPct >= 0 ? midX : midX - len;
      svg.appendChild(el("rect", { x, y, width: Math.max(len, 2), height: barH, fill: f.devPct >= 0 ? T.primary : T.neutral }));
      txt(svg, f.devPct >= 0 ? midX + len + 6 : midX - len - 6, y + barH - 5, F.fmtSigned(f.devPct, 1), {
        size: 12.5, weight: 700, anchor: f.devPct >= 0 ? "start" : "end"
      });
    });
  }

  // =========================================================================
  // Trang 5: phân rã RMSE theo mức điểm thật
  // =========================================================================
  function renderRmseBreakdown(containerId, series, levels, opts) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const { svg, width, height } = makeSvg(container, 420, 260);

    const pad = { top: 40, bottom: 44, left: 56, right: 10 };
    const chartW = width - pad.left - pad.right;
    const chartH = height - pad.top - pad.bottom;
    const maxV = Math.ceil(Math.max(...series.flatMap((s) => s.values.filter((v) => v !== null))));

    // Tiêu đề trục y (C2)
    const yTitle = el("text", {
      x: 14, y: pad.top + chartH / 2, fill: T.textSecondary, "font-size": 13, "font-weight": 600,
      "text-anchor": "middle", transform: `rotate(-90 14 ${pad.top + chartH / 2})`
    }, opts.yTitle);
    svg.appendChild(yTitle);

    for (let v = 0; v <= maxV; v += 1) {
      const y = pad.top + chartH - (v / maxV) * chartH;
      svg.appendChild(el("line", { x1: pad.left, y1: y, x2: pad.left + chartW, y2: y, stroke: T.grid, "stroke-width": 1 }));
      txt(svg, pad.left - 6, y + 4, F.fmt(v, 1), { size: 12, anchor: "end", fill: T.textSecondary });
    }
    svg.appendChild(el("line", {
      x1: pad.left, y1: pad.top + chartH, x2: pad.left + chartW, y2: pad.top + chartH, stroke: T.axis, "stroke-width": 1
    }));

    const slotW = chartW / levels.length;
    const barW = Math.max(Math.min(slotW * 0.36, 26), 6);
    const colors = [T.neutral, T.primary];
    levels.forEach((lvl, i) => {
      const cx = pad.left + i * slotW + slotW / 2;
      series.forEach((s, si) => {
        const v = s.values[i];
        if (v === null || v === undefined) return;
        const h = Math.max((v / maxV) * chartH, 1);
        const x = si === 0 ? cx - barW - 1 : cx + 1;
        svg.appendChild(el("rect", { x, y: pad.top + chartH - h, width: barW, height: h, fill: colors[si % 2] }));
      });
      txt(svg, cx, pad.top + chartH + 16, F.fmt(lvl, opts.levelDecimals), { size: 12.5, weight: 600, anchor: "middle" });
    });
    txt(svg, pad.left + chartW / 2, height - 6, opts.xTitle, { size: 13, weight: 600, anchor: "middle", fill: T.textSecondary });

    // Chú thích chuỗi
    series.forEach((s, si) => {
      const lx = pad.left + si * 210;
      svg.appendChild(el("rect", { x: lx, y: 8, width: 14, height: 12, fill: colors[si % 2] }));
      txt(svg, lx + 20, 19, s.name, { size: 13, weight: 600 });
    });
  }

  window.DashboardCharts = {
    renderCleaningFunnel,
    renderRatingDist,
    renderArchitecture,
    renderStorageRatios,
    renderScalability,
    renderClusterDeviation,
    renderRmseBreakdown,
    theme: T
  };
})(window);
