/**
 * Module vẽ biểu đồ và đồ họa thông tin khoa học bằng SVG thuần (Pure SVG).
 * - Hoàn toàn không phụ thuộc thư viện bên ngoài (Zero Dependency), 100% chạy offline.
 * - Mã nguồn tinh gọn, trực quan, sinh viên dễ dàng đọc hiểu và bảo vệ trước giảng viên.
 * - Đảm bảo kích thước chữ nhãn >= 14px, tương phản cao, phân biệt được trên máy chiếu và thang xám.
 */

(function (window) {
  "use strict";

  const CHART_THEME = {
    fontFamily: "'Source Sans 3', system-ui, -apple-system, sans-serif",
    fontSizeAxis: 13,
    fontSizeValue: 13,
    fontSizeTitle: 14,
    textColor: "#182218",
    secondaryText: "#364336",
    gridColor: "#D8DFD8",
    axisColor: "#364336",
    colorVn: "#1A5336",       // Xanh lá đậm chủ đạo (độ chói 0.076)
    colorFc: "#4B735B",       // Xanh lá phiến đá (độ chói 0.165)
    colorDrop: "#C85A17",     // Cam nhấn biểu thị dữ liệu bị loại (độ chói 0.165)
    colorMuted: "#86A391",
  };

  /**
   * Tạo phần tử SVG với thuộc tính đi kèm.
   */
  function createSvgElement(tag, attrs) {
    const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key, val] of Object.entries(attrs)) {
      el.setAttribute(key, val);
    }
    return el;
  }

  /**
   * Vẽ phễu làm sạch dữ liệu (Data Cleaning Funnel) dạng thanh ngang hai nhánh.
   * Minh bạch số lượng dòng bị loại và lý do kỹ thuật.
   * Căn gióng theo cột khoa học: Nhãn bước | Thanh đo | Số bản ghi | Lý do mất dòng.
   */
  function renderCleaningFunnel(containerId, cleaningRecords) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";

    const rect = container.getBoundingClientRect();
    const width = Math.max(rect.width || 680, 500);
    const height = Math.max(rect.height || 420, 360);

    const svg = createSvgElement("svg", {
      width: "100%",
      height: "100%",
      viewBox: `0 0 ${width} ${height}`,
      style: `font-family: ${CHART_THEME.fontFamily}; display: block;`
    });

    // Dữ liệu 2 nhánh: ViFoodRec và Food.com
    const vnSteps = [
      { name: "1. Dữ liệu thô (ratings.csv)", count: 182678, dropped: 0, note: "Khảo sát 101 người dùng" },
      { name: "2. Lọc thang điểm [1, 5]", count: 149467, dropped: 33211, note: "Loại 16.509 điểm 0 và 16.702 điểm 0,5" },
      { name: "3. Khóa ngoại danh mục foods", count: 149431, dropped: 36, note: "Loại 36 dòng food_id=4000 không khớp" },
      { name: "4. Lọc K-core (K=3)", count: 149431, dropped: 0, note: "Hội tụ ngay vòng 1 (100% thỏa mãn)" }
    ];

    const fcSteps = [
      { name: "1. Dữ liệu thô (RAW_interactions)", count: 1132367, dropped: 0, note: "Kaggle 2000-2018" },
      { name: "2. Loại đánh giá 0 sao", count: 1071520, dropped: 60847, note: "Chỉ xem/bình luận, không chấm sao" },
      { name: "3. Lọc K-core lặp (K=3)", count: 706514, dropped: 365006, note: "Hội tụ sau 5 vòng lặp phân tán" },
      { name: "4. Bộ tương tác sạch", count: 706514, dropped: 0, note: "30.836 users và 78.171 công thức" }
    ];

    const padding = { top: 8, left: 14, right: 14, bottom: 6 };
    const sectionHeight = (height - padding.top - padding.bottom) / 2;

    // Cấu hình tọa độ cột căn gióng chuẩn
    const colStepNameW = Math.min(195, width * 0.25);
    const barStartX = padding.left + colStepNameW;
    const maxBarW = Math.min(175, width * 0.22);
    const countColX = barStartX + maxBarW + 10;
    const notesColX = countColX + 72;

    function renderBranch(title, steps, startY, color, maxCount) {
      // Tiêu đề nhánh
      const t = createSvgElement("text", {
        x: padding.left,
        y: startY + 16,
        fill: CHART_THEME.textColor,
        "font-size": CHART_THEME.fontSizeTitle,
        "font-weight": "700"
      });
      t.textContent = title;
      svg.appendChild(t);

      const barStartY = startY + 28;
      const barH = 20;
      const gapY = (sectionHeight - 34) / steps.length;

      steps.forEach((step, idx) => {
        const y = barStartY + idx * gapY;
        const barW = Math.max((step.count / maxCount) * maxBarW, 8);

        // Nhãn tên bước bên trái
        const label = createSvgElement("text", {
          x: padding.left,
          y: y + barH - 5,
          fill: CHART_THEME.textColor,
          "font-size": CHART_THEME.fontSizeAxis,
          "font-weight": "500"
        });
        label.textContent = step.name;
        svg.appendChild(label);

        // Nền thanh mờ
        const bgBar = createSvgElement("rect", {
          x: barStartX,
          y: y,
          width: maxBarW,
          height: barH,
          fill: "#EEF2EE",
          rx: 2
        });
        svg.appendChild(bgBar);

        // Thanh tiến trình giá trị
        const bar = createSvgElement("rect", {
          x: barStartX,
          y: y,
          width: barW,
          height: barH,
          fill: color,
          rx: 2
        });
        svg.appendChild(bar);

        // Số dòng giữ lại trong cột thẳng hàng
        const valText = createSvgElement("text", {
          x: countColX,
          y: y + barH - 5,
          fill: CHART_THEME.textColor,
          "font-size": CHART_THEME.fontSizeValue,
          "font-weight": "600"
        });
        valText.textContent = window.FormatUtils.formatNumber(step.count);
        svg.appendChild(valText);

        // Ghi chú dòng bị loại nếu có, căn thẳng hàng
        if (step.dropped > 0) {
          const dropText = createSvgElement("text", {
            x: notesColX,
            y: y + barH - 5,
            fill: CHART_THEME.colorDrop,
            "font-size": 12.5,
            "font-weight": "600"
          });
          dropText.textContent = `Mất -${window.FormatUtils.formatNumber(step.dropped)}: ${step.note}`;
          svg.appendChild(dropText);
        } else if (step.note && idx === steps.length - 1) {
          const okText = createSvgElement("text", {
            x: notesColX,
            y: y + barH - 5,
            fill: CHART_THEME.colorVn,
            "font-size": 12.5,
            "font-weight": "500"
          });
          okText.textContent = `✓ ${step.note}`;
          svg.appendChild(okText);
        }
      });
    }

    // Nhánh 1: ViFoodRec
    renderBranch("Nhánh 1: ViFoodRec (Món Việt) — Tinh lọc 4 bước", vnSteps, padding.top, CHART_THEME.colorVn, 182678);

    // Đường kẻ phân vùng mảnh giữa 2 nhánh
    const divLine = createSvgElement("line", {
      x1: padding.left,
      y1: padding.top + sectionHeight + 2,
      x2: width - padding.right,
      y2: padding.top + sectionHeight + 2,
      stroke: CHART_THEME.gridColor,
      "stroke-width": 1
    });
    svg.appendChild(divLine);

    // Nhánh 2: Food.com
    renderBranch("Nhánh 2: Food.com (Kaggle) — Tinh lọc K-core 5 vòng", fcSteps, padding.top + sectionHeight + 8, CHART_THEME.colorFc, 1132367);

    container.appendChild(svg);
  }

  /**
   * Vẽ hai biểu đồ cột mini phân phối điểm đánh giá đặt cạnh nhau cùng thang đo [0% - 85%].
   * Sửa lỗi thang đo: pct ở thang [0, 100] (ví dụ: 10.98% và 78.4%).
   */
  function renderRatingDistComparison(containerId, vnDist, fcDist) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";

    const rect = container.getBoundingClientRect();
    const width = Math.max(rect.width || 460, 360);
    const height = Math.max(rect.height || 180, 150);

    const svg = createSvgElement("svg", {
      width: "100%",
      height: "100%",
      viewBox: `0 0 ${width} ${height}`,
      style: `font-family: ${CHART_THEME.fontFamily}; display: block;`
    });

    const halfW = (width - 24) / 2;
    const padding = { top: 20, bottom: 28, left: 32, right: 8 };
    const chartH = height - padding.top - padding.bottom;
    const maxPct = 85.0; // Thang đo trục Y tối đa 85%

    // Hàm vẽ một biểu đồ cột con
    function drawSubChart(offsetX, title, data, color, isStepsOfHalf) {
      // Tiêu đề biểu đồ con
      const t = createSvgElement("text", {
        x: offsetX + padding.left,
        y: 15,
        fill: CHART_THEME.textColor,
        "font-size": 13.5,
        "font-weight": "700"
      });
      t.textContent = title;
      svg.appendChild(t);

      // Trục Y kẻ lưới (0%, 25%, 50%, 75%)
      const yTicks = [0, 25, 50, 75];
      yTicks.forEach((tickVal) => {
        const y = padding.top + chartH - (tickVal / maxPct) * chartH;
        // Đường kẻ mờ
        const line = createSvgElement("line", {
          x1: offsetX + padding.left,
          y1: y,
          x2: offsetX + halfW - padding.right,
          y2: y,
          stroke: CHART_THEME.gridColor,
          "stroke-width": 1
        });
        svg.appendChild(line);

        // Nhãn Y
        const yLabel = createSvgElement("text", {
          x: offsetX + padding.left - 5,
          y: y + 4,
          fill: CHART_THEME.secondaryText,
          "font-size": 11,
          "text-anchor": "end"
        });
        yLabel.textContent = `${tickVal}%`;
        svg.appendChild(yLabel);
      });

      // Trục hoành X
      const xAxis = createSvgElement("line", {
        x1: offsetX + padding.left,
        y1: padding.top + chartH,
        x2: offsetX + halfW - padding.right,
        y2: padding.top + chartH,
        stroke: CHART_THEME.axisColor,
        "stroke-width": 1
      });
      svg.appendChild(xAxis);

      // Cột dữ liệu
      const chartW = halfW - padding.left - padding.right;
      const numBars = data.length;
      const barSlot = chartW / numBars;
      const barW = Math.max(barSlot * 0.72, 6);

      data.forEach((d, idx) => {
        const pct = Number(d.pct); // [0, 100]
        const barH = Math.max((pct / maxPct) * chartH, 2);
        const x = offsetX + padding.left + idx * barSlot + (barSlot - barW) / 2;
        const y = padding.top + chartH - barH;

        // Cột hình chữ nhật
        const bar = createSvgElement("rect", {
          x: x,
          y: y,
          width: barW,
          height: barH,
          fill: color,
          rx: 1
        });
        svg.appendChild(bar);

        // Nhãn mức sao bên dưới trục X
        const xLabel = createSvgElement("text", {
          x: x + barW / 2,
          y: padding.top + chartH + 15,
          fill: CHART_THEME.textColor,
          "font-size": isStepsOfHalf ? 10.5 : 12,
          "font-weight": "500",
          "text-anchor": "middle"
        });
        const ratingNum = Number(d.rating);
        const ratingStr = isStepsOfHalf ? ratingNum.toFixed(1) : Math.round(ratingNum).toString();
        xLabel.textContent = ratingStr;
        svg.appendChild(xLabel);

        // Giá trị phần trăm trên đầu cột nếu cột cao hoặc đặc biệt
        if (pct >= 15 || (!isStepsOfHalf && pct >= 10)) {
          const valLabel = createSvgElement("text", {
            x: x + barW / 2,
            y: y - 3,
            fill: CHART_THEME.textColor,
            "font-size": 11,
            "font-weight": "700",
            "text-anchor": "middle"
          });
          valLabel.textContent = `${pct.toFixed(1).replace(".", ",")}%`;
          svg.appendChild(valLabel);
        }
      });
    }

    // Biểu đồ con 1: ViFoodRec (9 bậc điểm 1.0 - 5.0 bước 0.5)
    drawSubChart(0, "ViFoodRec (Đều ~11%/bậc)", vnDist, CHART_THEME.colorVn, true);

    // Biểu đồ con 2: Food.com (5 bậc điểm 1.0 - 5.0, lệch mạnh 5 sao 78,4%)
    drawSubChart(halfW + 12, "Food.com (5 sao chiếm 78,4%)", fcDist, CHART_THEME.colorFc, false);

    container.appendChild(svg);
  }

  /**
   * Vẽ sơ đồ kiến trúc hệ thống phân tán Docker HDFS + Spark bằng SVG thuần.
   * Phản ánh ĐÚNG 100% hạ tầng thật trong stage_P2.md:
   * HDFS 3.3.6 (NameNode, 2 DataNodes) + Spark 3.5.0 (Master, 2 Workers x 2 Cores/3.5GB RAM).
   */
  function renderArchitectureDiagram(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";

    const rect = container.getBoundingClientRect();
    const width = Math.max(rect.width || 680, 500);
    const height = Math.max(rect.height || 260, 220);

    const svg = createSvgElement("svg", {
      width: "100%",
      height: "100%",
      viewBox: `0 0 ${width} ${height}`,
      style: `font-family: ${CHART_THEME.fontFamily}; display: block;`
    });

    const boxW = Math.min(115, (width - 70) / 5);
    const boxH = height - 50;
    const startY = 25;
    const gap = (width - 30 - boxW * 5) / 4;

    const stages = [
      {
        title: "1. Nguồn thô",
        tech: "CSV / Kaggle",
        detail: ["RAW_recipes", "RAW_interactions", "foods.csv (4.000)", "ratings (101 user)"],
        color: "#364336"
      },
      {
        title: "2. Lưu trữ HDFS",
        tech: "Hadoop 3.3.6",
        detail: ["NameNode :9000", "DataNode 1 :9864", "DataNode 2 :9865", "Replication = 2"],
        color: CHART_THEME.colorVn
      },
      {
        title: "3. Xử lý phân tán",
        tech: "Spark 3.5.0",
        detail: ["Spark Master :7077", "Worker 1: 2C/3.5G", "Worker 2: 2C/3.5G", "Tổng: 4 Cores, 7GB"],
        color: CHART_THEME.colorVn
      },
      {
        title: "4. Lưu trữ đích",
        tech: "Parquet Snappy",
        detail: ["Nén 4x - 7x", "Tách cột tối ưu", "Hợp đồng dữ liệu", "app/data/*.parquet"],
        color: CHART_THEME.colorFc
      },
      {
        title: "5. Trình diễn",
        tech: "Web Dashboard",
        detail: ["HTML / CSS / JS", "Zero-dependency", "100% Chạy Offline", "1 Màn hình phẳng"],
        color: CHART_THEME.colorVn
      }
    ];

    stages.forEach((stg, i) => {
      const x = 15 + i * (boxW + gap);

      // Khung chữ nhật bao quanh giai đoạn
      const box = createSvgElement("rect", {
        x: x,
        y: startY,
        width: boxW,
        height: boxH,
        fill: "#F8FAF8",
        stroke: stg.color,
        "stroke-width": 1.5,
        rx: 3
      });
      svg.appendChild(box);

      // Dải tiêu đề trên
      const headBg = createSvgElement("rect", {
        x: x,
        y: startY,
        width: boxW,
        height: 24,
        fill: stg.color,
        rx: 2
      });
      svg.appendChild(headBg);

      const titleTxt = createSvgElement("text", {
        x: x + boxW / 2,
        y: startY + 16,
        fill: "#FFFFFF",
        "font-size": 12,
        "font-weight": "700",
        "text-anchor": "middle"
      });
      titleTxt.textContent = stg.title;
      svg.appendChild(titleTxt);

      // Công nghệ
      const techTxt = createSvgElement("text", {
        x: x + boxW / 2,
        y: startY + 42,
        fill: stg.color,
        "font-size": 12.5,
        "font-weight": "700",
        "text-anchor": "middle"
      });
      techTxt.textContent = stg.tech;
      svg.appendChild(techTxt);

      // Các gạch đầu dòng chi tiết
      stg.detail.forEach((dt, j) => {
        const dTxt = createSvgElement("text", {
          x: x + 8,
          y: startY + 62 + j * 18,
          fill: CHART_THEME.textColor,
          "font-size": 11,
          "font-weight": "500"
        });
        dTxt.textContent = `• ${dt}`;
        svg.appendChild(dTxt);
      });

      // Mũi tên liên kết giữa các khối
      if (i < stages.length - 1) {
        const arrowX1 = x + boxW + 4;
        const arrowX2 = x + boxW + gap - 4;
        const arrowY = startY + boxH / 2;

        const line = createSvgElement("line", {
          x1: arrowX1,
          y1: arrowY,
          x2: arrowX2,
          y2: arrowY,
          stroke: CHART_THEME.axisColor,
          "stroke-width": 1.5
        });
        svg.appendChild(line);

        const head = createSvgElement("polygon", {
          points: `${arrowX2},${arrowY} ${arrowX2 - 5},${arrowY - 3.5} ${arrowX2 - 5},${arrowY + 3.5}`,
          fill: CHART_THEME.axisColor
        });
        svg.appendChild(head);
      }
    });

    container.appendChild(svg);
  }

  /**
   * Vẽ biểu đồ đường mở rộng quy mô (Scalability Line Chart) 1 Worker vs 2 Workers.
   * Phản ánh trung thực: thời gian không đơn điệu (10% chậm do cold-start).
   */
  function renderScalabilityChart(containerId, scalabilityData) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";

    const rect = container.getBoundingClientRect();
    const width = Math.max(rect.width || 460, 360);
    const height = Math.max(rect.height || 260, 200);

    const svg = createSvgElement("svg", {
      width: "100%",
      height: "100%",
      viewBox: `0 0 ${width} ${height}`,
      style: `font-family: ${CHART_THEME.fontFamily}; display: block;`
    });

    const padding = { top: 32, bottom: 34, left: 40, right: 20 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    // Dữ liệu đo đạc thực tế:
    // 2 Workers (4 Cores): 10% -> 11.99s, 25% -> 8.39s, 50% -> 7.17s, 100% -> 7.93s
    // 1 Worker (2 Cores): 10% -> 10.58s, 25% -> 7.29s, 50% -> 8.24s, 100% -> 9.89s
    const points2W = [
      { ratio: "10%", time: 11.99, x: 0 },
      { ratio: "25%", time: 8.39, x: 0.333 },
      { ratio: "50%", time: 7.17, x: 0.666 },
      { ratio: "100%", time: 7.93, x: 1.0 }
    ];

    const points1W = [
      { ratio: "10%", time: 10.58, x: 0 },
      { ratio: "25%", time: 7.29, x: 0.333 },
      { ratio: "50%", time: 8.24, x: 0.666 },
      { ratio: "100%", time: 9.89, x: 1.0 }
    ];

    const maxTime = 15.0; // 15 giây thang Y

    // Trục Y và đường lưới
    [0, 5, 10, 15].forEach((sec) => {
      const y = padding.top + chartH - (sec / maxTime) * chartH;
      const grid = createSvgElement("line", {
        x1: padding.left,
        y1: y,
        x2: padding.left + chartW,
        y2: y,
        stroke: CHART_THEME.gridColor,
        "stroke-width": 1
      });
      svg.appendChild(grid);

      const yLabel = createSvgElement("text", {
        x: padding.left - 6,
        y: y + 4,
        fill: CHART_THEME.secondaryText,
        "font-size": 12,
        "text-anchor": "end"
      });
      yLabel.textContent = `${sec}s`;
      svg.appendChild(yLabel);
    });

    // Trục X
    const xAxis = createSvgElement("line", {
      x1: padding.left,
      y1: padding.top + chartH,
      x2: padding.left + chartW,
      y2: padding.top + chartH,
      stroke: CHART_THEME.axisColor,
      "stroke-width": 1
    });
    svg.appendChild(xAxis);

    // Vẽ đường
    function drawLine(pts, color, isDashed) {
      let pathD = "";
      pts.forEach((pt, i) => {
        const cx = padding.left + pt.x * chartW;
        const cy = padding.top + chartH - (pt.time / maxTime) * chartH;
        pathD += (i === 0 ? "M " : " L ") + `${cx} ${cy}`;
      });

      const path = createSvgElement("path", {
        d: pathD,
        fill: "none",
        stroke: color,
        "stroke-width": 2,
        "stroke-dasharray": isDashed ? "4 3" : "none"
      });
      svg.appendChild(path);

      // Điểm tròn và nhãn số
      pts.forEach((pt) => {
        const cx = padding.left + pt.x * chartW;
        const cy = padding.top + chartH - (pt.time / maxTime) * chartH;
        const circle = createSvgElement("circle", {
          cx: cx,
          cy: cy,
          r: 4,
          fill: color
        });
        svg.appendChild(circle);

        const valTxt = createSvgElement("text", {
          x: cx,
          y: cy - 7,
          fill: CHART_THEME.textColor,
          "font-size": 11.5,
          "font-weight": "700",
          "text-anchor": "middle"
        });
        valTxt.textContent = `${pt.time.toFixed(1).replace(".", ",")}s`;
        svg.appendChild(valTxt);
      });
    }

    // Đường 2 Workers: Xanh lá đậm liền nét
    drawLine(points2W, CHART_THEME.colorVn, false);
    // Đường 1 Worker: Xanh lá phiến đá nét đứt
    drawLine(points1W, CHART_THEME.colorFc, true);

    // Nhãn trục X
    points2W.forEach((pt) => {
      const cx = padding.left + pt.x * chartW;
      const xLbl = createSvgElement("text", {
        x: cx,
        y: padding.top + chartH + 18,
        fill: CHART_THEME.textColor,
        "font-size": 12.5,
        "font-weight": "600",
        "text-anchor": "middle"
      });
      xLbl.textContent = pt.ratio;
      svg.appendChild(xLbl);
    });

    // Chú thích legend góc trên
    const legY = 16;
    // 2 Workers
    const l1 = createSvgElement("line", { x1: padding.left, y1: legY, x2: padding.left + 24, y2: legY, stroke: CHART_THEME.colorVn, "stroke-width": 2.5 });
    svg.appendChild(l1);
    const l1Txt = createSvgElement("text", { x: padding.left + 30, y: legY + 4, fill: CHART_THEME.textColor, "font-size": 12, "font-weight": "600" });
    l1Txt.textContent = "2 Workers (4 Cores)";
    svg.appendChild(l1Txt);

    // 1 Worker
    const l2 = createSvgElement("line", { x1: padding.left + 170, y1: legY, x2: padding.left + 194, y2: legY, stroke: CHART_THEME.colorFc, "stroke-width": 2.5, "stroke-dasharray": "4 3" });
    svg.appendChild(l2);
    const l2Txt = createSvgElement("text", { x: padding.left + 200, y: legY + 4, fill: CHART_THEME.textColor, "font-size": 12, "font-weight": "600" });
    l2Txt.textContent = "1 Worker (2 Cores)";
    svg.appendChild(l2Txt);

    container.appendChild(svg);
  }

  /**
   * Vẽ biểu đồ độ lệch đặc trưng cụm (Cluster Deviation Chart).
   * Áp dụng quy tắc trung thực: Nếu ViFoodRec users độ lệch < 10% trên mọi đặc trưng,
   * hiển thị thông báo rõ ràng "các cụm chưa phân biệt rõ".
   */
  function renderClusterDeviationChart(containerId, clusterData, isViFoodRecUser) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";

    const rect = container.getBoundingClientRect();
    const width = Math.max(rect.width || 640, 500);
    const height = Math.max(rect.height || 360, 300);

    const svg = createSvgElement("svg", {
      width: "100%",
      height: "100%",
      viewBox: `0 0 ${width} ${height}`,
      style: `font-family: ${CHART_THEME.fontFamily}; display: block;`
    });

    // Nếu là cụm người dùng ViFoodRec: kiểm tra xem độ lệch có < 10%
    if (isViFoodRecUser) {
      // Banner cảnh báo dữ liệu thật
      const bannerH = 34;
      const banner = createSvgElement("rect", {
        x: 16,
        y: 12,
        width: width - 32,
        height: bannerH,
        fill: "#FDF4EB",
        stroke: CHART_THEME.colorDrop,
        "stroke-width": 1,
        rx: 2
      });
      svg.appendChild(banner);

      const warnTxt = createSvgElement("text", {
        x: 28,
        y: 12 + 22,
        fill: CHART_THEME.colorDrop,
        "font-size": 13,
        "font-weight": "700"
      });
      warnTxt.textContent = "Dữ liệu thật: Độ lệch giữa các cụm trên mọi đặc trưng < 10% (các cụm chưa phân biệt rõ). Giữ tên Cụm 1, 2, 3.";
      svg.appendChild(warnTxt);
    }

    const startY = isViFoodRecUser ? 58 : 20;
    const padding = { top: startY, bottom: 24, left: 140, right: 30 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    // Trục giữa: 0% (Mức trung bình hệ thống)
    const midX = padding.left + chartW / 2;

    const zeroLine = createSvgElement("line", {
      x1: midX,
      y1: padding.top,
      x2: midX,
      y2: padding.top + chartH,
      stroke: CHART_THEME.axisColor,
      "stroke-width": 1.5
    });
    svg.appendChild(zeroLine);

    const zeroLbl = createSvgElement("text", {
      x: midX,
      y: padding.top + chartH + 16,
      fill: CHART_THEME.secondaryText,
      "font-size": 12,
      "font-weight": "600",
      "text-anchor": "middle"
    });
    zeroLbl.textContent = "0% (Trung bình hệ thống)";
    svg.appendChild(zeroLbl);

    // Kẻ lưới -50%, -25%, +25%, +50%
    [-50, -25, 25, 50].forEach((pctVal) => {
      const gx = midX + (pctVal / 60) * (chartW / 2);
      const gLine = createSvgElement("line", {
        x1: gx,
        y1: padding.top,
        x2: gx,
        y2: padding.top + chartH,
        stroke: CHART_THEME.gridColor,
        "stroke-width": 1
      });
      svg.appendChild(gLine);

      const gLbl = createSvgElement("text", {
        x: gx,
        y: padding.top + chartH + 16,
        fill: CHART_THEME.secondaryText,
        "font-size": 11,
        "text-anchor": "middle"
      });
      gLbl.textContent = `${pctVal > 0 ? "+" : ""}${pctVal}%`;
      svg.appendChild(gLbl);
    });

    // Vẽ các thanh đặc trưng
    const features = clusterData.features || [];
    const numRows = features.length;
    if (numRows > 0) {
      const rowH = chartH / numRows;
      const barH = Math.min(18, rowH * 0.65);

      features.forEach((feat, idx) => {
        const y = padding.top + idx * rowH + (rowH - barH) / 2;

        // Tên đặc trưng bên trái
        const fTxt = createSvgElement("text", {
          x: padding.left - 12,
          y: y + barH - 4,
          fill: CHART_THEME.textColor,
          "font-size": 12.5,
          "font-weight": "600",
          "text-anchor": "end"
        });
        fTxt.textContent = feat.name;
        svg.appendChild(fTxt);

        // Thanh độ lệch
        const devPct = Number(feat.devPct); // ví dụ: -15.2 hoặc +32.5
        const barLen = (Math.abs(devPct) / 60) * (chartW / 2);
        const bx = devPct >= 0 ? midX : midX - barLen;
        const barColor = devPct >= 0 ? CHART_THEME.colorVn : CHART_THEME.colorFc;

        const bar = createSvgElement("rect", {
          x: bx,
          y: y,
          width: Math.max(barLen, 3),
          height: barH,
          fill: isViFoodRecUser ? "#86A391" : barColor,
          rx: 1
        });
        svg.appendChild(bar);

        // Số phần trăm hiển thị
        const valTxt = createSvgElement("text", {
          x: devPct >= 0 ? midX + barLen + 6 : midX - barLen - 6,
          y: y + barH - 4,
          fill: CHART_THEME.textColor,
          "font-size": 11.5,
          "font-weight": "700",
          "text-anchor": devPct >= 0 ? "start" : "end"
        });
        valTxt.textContent = `${devPct >= 0 ? "+" : ""}${devPct.toFixed(1).replace(".", ",")}%`;
        svg.appendChild(valTxt);
      });
    }

    container.appendChild(svg);
  }

  /**
   * Vẽ biểu đồ cột nhóm phân rã RMSE theo từng thang điểm thật (1 đến 5 sao).
   * Đối đầu Baseline vs ALS Matrix Factorization.
   */
  function renderRmseBreakdownChart(containerId, alsBreakdown, baseBreakdown, dataset) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";

    const rect = container.getBoundingClientRect();
    const width = Math.max(rect.width || 480, 360);
    const height = Math.max(rect.height || 320, 240);

    const svg = createSvgElement("svg", {
      width: "100%",
      height: "100%",
      viewBox: `0 0 ${width} ${height}`,
      style: `font-family: ${CHART_THEME.fontFamily}; display: block;`
    });

    const padding = { top: 32, bottom: 32, left: 40, right: 16 };
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;
    const maxRmse = 4.0; // Thang đo tối đa 4.0

    // Đường lưới Y
    [0, 1.0, 2.0, 3.0, 4.0].forEach((v) => {
      const y = padding.top + chartH - (v / maxRmse) * chartH;
      const g = createSvgElement("line", {
        x1: padding.left,
        y1: y,
        x2: padding.left + chartW,
        y2: y,
        stroke: CHART_THEME.gridColor,
        "stroke-width": 1
      });
      svg.appendChild(g);

      const yLbl = createSvgElement("text", {
        x: padding.left - 6,
        y: y + 4,
        fill: CHART_THEME.secondaryText,
        "font-size": 11.5,
        "text-anchor": "end"
      });
      yLbl.textContent = v.toFixed(1).replace(".", ",");
      svg.appendChild(yLbl);
    });

    // Trục hoành X
    const xAxis = createSvgElement("line", {
      x1: padding.left,
      y1: padding.top + chartH,
      x2: padding.left + chartW,
      y2: padding.top + chartH,
      stroke: CHART_THEME.axisColor,
      "stroke-width": 1
    });
    svg.appendChild(xAxis);

    // Lọc theo dataset
    const subAls = alsBreakdown.filter((r) => r.dataset === dataset);
    const subBase = baseBreakdown.filter((r) => r.dataset === dataset && r.model === "Global Mean");

    // Ghép theo rating_level
    const levels = dataset === "food_vietnam" ? [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0] : [1.0, 2.0, 3.0, 4.0, 5.0];
    const slotW = chartW / levels.length;
    const barW = Math.max(slotW * 0.35, 6);

    levels.forEach((lvl, i) => {
      const slotX = padding.left + i * slotW;
      const alsRow = subAls.find((r) => Number(r.rating_level) === lvl);
      const baseRow = subBase.find((r) => Number(r.rating_level) === lvl);

      const alsRmse = alsRow ? Number(alsRow.rmse) : 0;
      const baseRmse = baseRow ? Number(baseRow.rmse) : 0;

      // Cột 1: Baseline (Global Mean) - Màu xám xanh
      const bH = Math.max((baseRmse / maxRmse) * chartH, 2);
      const bX = slotX + slotW / 2 - barW - 2;
      const bY = padding.top + chartH - bH;
      const barBase = createSvgElement("rect", {
        x: bX,
        y: bY,
        width: barW,
        height: bH,
        fill: CHART_THEME.colorFc,
        rx: 1
      });
      svg.appendChild(barBase);

      // Cột 2: ALS - Màu cam nhấn
      const aH = Math.max((alsRmse / maxRmse) * chartH, 2);
      const aX = slotX + slotW / 2 + 2;
      const aY = padding.top + chartH - aH;
      const barAls = createSvgElement("rect", {
        x: aX,
        y: aY,
        width: barW,
        height: aH,
        fill: CHART_THEME.colorDrop,
        rx: 1
      });
      svg.appendChild(barAls);

      // Nhãn trục X mức sao
      const xLbl = createSvgElement("text", {
        x: slotX + slotW / 2,
        y: padding.top + chartH + 16,
        fill: CHART_THEME.textColor,
        "font-size": dataset === "food_vietnam" ? 11 : 12.5,
        "font-weight": "600",
        "text-anchor": "middle"
      });
      xLbl.textContent = `${lvl.toFixed(dataset === "food_vietnam" ? 1 : 0).replace(".0", dataset === "food_vietnam" ? ".0" : "")} sao`;
      svg.appendChild(xLbl);
    });

    // Chú thích legend
    const legY = 16;
    // Baseline
    const leg1 = createSvgElement("rect", { x: padding.left, y: legY - 10, width: 14, height: 10, fill: CHART_THEME.colorFc });
    svg.appendChild(leg1);
    const leg1Txt = createSvgElement("text", { x: padding.left + 20, y: legY - 1, fill: CHART_THEME.textColor, "font-size": 12, "font-weight": "600" });
    leg1Txt.textContent = "Baseline (Global Mean)";
    svg.appendChild(leg1Txt);

    // ALS
    const leg2 = createSvgElement("rect", { x: padding.left + 170, y: legY - 10, width: 14, height: 10, fill: CHART_THEME.colorDrop });
    svg.appendChild(leg2);
    const leg2Txt = createSvgElement("text", { x: padding.left + 190, y: legY - 1, fill: CHART_THEME.textColor, "font-size": 12, "font-weight": "600" });
    leg2Txt.textContent = "ALS Matrix Factorization";
    svg.appendChild(leg2Txt);

    container.appendChild(svg);
  }

  // Xuất ra phạm vi toàn cục
  window.DashboardCharts = {
    renderCleaningFunnel,
    renderRatingDistComparison,
    renderArchitectureDiagram,
    renderScalabilityChart,
    renderClusterDeviationChart,
    renderRmseBreakdownChart,
    theme: CHART_THEME
  };

})(window);

