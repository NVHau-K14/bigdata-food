/**
 * Logic điều khiển chính của Dashboard Web Tĩnh (app.js).
 * - Điều hướng theo URL hash (#/du-lieu, #/he-thong, #/hanh-vi, #/goi-y, #/mo-hinh)
 * - Phím tắt 1 đến 5 để chuyển trang cho người thuyết trình, phím Esc đóng Chú giải / Modal.
 * - Quản lý trạng thái bộ dữ liệu (ViFoodRec / Food.com) và các chế độ gợi ý.
 * - Triển khai đầy đủ logic render cho cả 5 trang dữ liệu chuẩn mực.
 */

(function () {
  "use strict";

  // Danh mục trang tương ứng với phím tắt 1 - 5
  const ROUTES = [
    { key: "1", hash: "#/du-lieu", pageId: "page-du-lieu", title: "Dữ liệu" },
    { key: "2", hash: "#/he-thong", pageId: "page-he-thong", title: "Hệ thống" },
    { key: "3", hash: "#/hanh-vi", pageId: "page-hanh-vi", title: "Hành vi" },
    { key: "4", hash: "#/goi-y", pageId: "page-goi-y", title: "Gợi ý" },
    { key: "5", hash: "#/mo-hinh", pageId: "page-mo-hinh", title: "Mô hình" }
  ];

  // Trạng thái ứng dụng
  const state = {
    currentRoute: "#/du-lieu",
    currentDataset: "vifoodrec", // "vifoodrec" | "food_com"
    isGlossaryOpen: false,
    isTuningModalOpen: false,

    // Trạng thái Trang 2: Hệ thống
    systemTab: "storage", // "storage" | "scalability"

    // Trạng thái Trang 3: Hành vi
    behaviorMode: "food_com", // "food_com" | "vifoodrec_users" | "vifoodrec_foods"
    selectedClusterIndex: 0,

    // Trạng thái Trang 4: Gợi ý
    recsDataset: "vifoodrec", // "vifoodrec" | "food_com"
    recsMode: "existing", // "existing" | "new"
    selectedUserId: 70,
    selectedColdStartIds: [1248, 1082], // 2 món mẫu ban đầu: Chè bí đỏ, Món tương đồng
    recsFilters: {
      dishType: "all",
      maxTime: null,
      maxCalo: null,
      topN: 10
    },

    // Trạng thái Trang 5: Mô hình
    modelDataset: "food_vietnam" // "food_vietnam" | "food_com"
  };

  /**
   * Khởi tạo ứng dụng khi tải trang
   */
  function init() {
    setupNavigation();
    setupKeyboardShortcuts();
    setupGlossaryDrawer();
    setupTuningModal();
    setupPage2Handlers();
    setupPage3Handlers();
    setupPage4Handlers();
    setupPage5Handlers();
    setupResizeHandler();

    // Điều hướng theo hash hiện tại hoặc mặc định #/du-lieu
    const currentHash = window.location.hash || "#/du-lieu";
    navigate(currentHash);
  }

  /**
   * Thiết lập sự kiện điều hướng hash và click link
   */
  function setupNavigation() {
    window.addEventListener("hashchange", () => {
      navigate(window.location.hash);
    });

    document.querySelectorAll(".nav-link").forEach((link) => {
      link.addEventListener("click", (e) => {
        const hash = link.getAttribute("href");
        if (hash.startsWith("#/")) {
          navigate(hash);
        }
      });
    });
  }

  /**
   * Điều hướng tới một route cụ thể
   */
  function navigate(hash) {
    const route = ROUTES.find((r) => r.hash === hash) || ROUTES[0];
    state.currentRoute = route.hash;
    window.location.hash = route.hash;

    // Cập nhật class active cho navigation header
    document.querySelectorAll(".nav-link").forEach((link) => {
      if (link.getAttribute("href") === route.hash) {
        link.classList.add("active");
      } else {
        link.classList.remove("active");
      }
    });

    // Ẩn tất cả view, chỉ hiện view tương ứng
    document.querySelectorAll(".page-view").forEach((view) => {
      view.classList.remove("active");
    });
    const targetView = document.getElementById(route.pageId);
    if (targetView) {
      targetView.classList.add("active");
    }

    // Kích hoạt render nội dung cho trang được chọn
    renderPage(route.pageId);
  }

  /**
   * Điều phối render dữ liệu cho từng trang
   */
  function renderPage(pageId) {
    switch (pageId) {
      case "page-du-lieu":
        renderPage1Data();
        break;
      case "page-he-thong":
        renderPage2System();
        break;
      case "page-hanh-vi":
        renderPage3Behavior();
        break;
      case "page-goi-y":
        renderPage4Recs();
        break;
      case "page-mo-hinh":
        renderPage5Models();
        break;
    }
  }

  // =========================================================================
  // TRANG 1: DỮ LIỆU
  // =========================================================================
  function renderPage1Data() {
    const data = window.WEB_DATA_SUMMARY;
    if (!data) return;

    // Bảng đối chiếu 2 bộ dữ liệu (7 hàng)
    const tableBody = document.getElementById("dataset-comparison-tbody");
    if (tableBody && data.dataset_comparison) {
      tableBody.innerHTML = "";
      data.dataset_comparison.forEach((row) => {
        const tr = document.createElement("tr");

        const tdMetric = document.createElement("td");
        tdMetric.textContent = row.ChiSo;
        tr.appendChild(tdMetric);

        const tdVn = document.createElement("td");
        tdVn.className = "num-cell";
        tdVn.textContent = formatMetricValue(row.ChiSo, row.ViFoodRec);
        tr.appendChild(tdVn);

        const tdFc = document.createElement("td");
        tdFc.className = "num-cell";
        tdFc.textContent = formatMetricValue(row.ChiSo, row.Food_com);
        tr.appendChild(tdFc);

        tableBody.appendChild(tr);
      });
    }

    // Phễu làm sạch dữ liệu bằng SVG
    if (window.DashboardCharts?.renderCleaningFunnel) {
      window.DashboardCharts.renderCleaningFunnel("cleaning-funnel-container", data.cleaning_log);
    }

    // Biểu đồ phân phối điểm đánh giá mini side-by-side
    if (window.DashboardCharts?.renderRatingDistComparison) {
      window.DashboardCharts.renderRatingDistComparison(
        "rating-dist-container",
        data.rating_dist_vn,
        data.rating_dist_fc
      );
    }
  }

  function formatMetricValue(metricName, rawVal) {
    if (rawVal === null || rawVal === undefined) return "—";
    const num = Number(rawVal);
    if (metricName.includes("Độ thưa")) {
      return window.FormatUtils.formatPercent(num, 2, false);
    }
    if (metricName.includes("Điểm TB")) {
      return window.FormatUtils.formatNumber(num, 2);
    }
    return window.FormatUtils.formatNumber(num, 0);
  }

  // =========================================================================
  // TRANG 2: HỆ THỐNG
  // =========================================================================
  function setupPage2Handlers() {
    const btnStorage = document.getElementById("tab-btn-storage");
    const btnScalability = document.getElementById("tab-btn-scalability");
    const subLabel = document.getElementById("system-tab-sub");

    if (btnStorage && btnScalability) {
      btnStorage.addEventListener("click", () => {
        state.systemTab = "storage";
        btnStorage.classList.add("active");
        btnScalability.classList.remove("active");
        document.getElementById("tab-storage-body").style.display = "block";
        document.getElementById("tab-scalability-body").style.display = "none";
        if (subLabel) subLabel.textContent = "So sánh Parquet Snappy vs CSV";
      });

      btnScalability.addEventListener("click", () => {
        state.systemTab = "scalability";
        btnScalability.classList.add("active");
        btnStorage.classList.remove("active");
        document.getElementById("tab-storage-body").style.display = "none";
        document.getElementById("tab-scalability-body").style.display = "flex";
        if (subLabel) subLabel.textContent = "Đường thời gian 1 vs 2 Workers";
        if (window.DashboardCharts?.renderScalabilityChart) {
          window.DashboardCharts.renderScalabilityChart("scalability-chart-container", window.WEB_DATA_SYSTEM?.scalability);
        }
      });
    }
  }

  function renderPage2System() {
    const data = window.WEB_DATA_SYSTEM;
    if (!data) return;

    // 1. Sơ đồ kiến trúc phân tán SVG
    if (window.DashboardCharts?.renderArchitectureDiagram) {
      window.DashboardCharts.renderArchitectureDiagram("architecture-diagram-container");
    }

    // 2. Bảng hiệu quả lưu trữ (Exp A & Exp B)
    const storageTbody = document.getElementById("storage-benchmark-tbody");
    if (storageTbody && data.storage_benchmark) {
      storageTbody.innerHTML = "";
      const storageRows = [
        { name: "RAW_interactions (Thô, 1,13M dòng)", csv: "333,25 MB", pq: "189,79 MB", gain: "Giảm 1,76x" },
        { name: "RAW_recipes (Thô, 231K dòng)", csv: "280,88 MB", pq: "120,25 MB", gain: "Giảm 2,34x" },
        { name: "interactions_clean (Sạch, 706K dòng)", csv: "19,11 MB", pq: "4,56 MB", gain: "Giảm 4,19x" },
        { name: "recipes_clean (Sạch, 231K dòng)", csv: "124,92 MB", pq: "17,78 MB", gain: "Giảm 7,03x" }
      ];

      storageRows.forEach((r) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${r.name}</td><td class="num-cell">${r.csv}</td><td class="num-cell">${r.pq}</td><td class="num-cell" style="color: var(--brand-green); font-weight:700;">${r.gain}</td>`;
        storageTbody.appendChild(tr);
      });
    }

    // 3. Bảng độ trễ truy vấn (Exp C)
    const latencyTbody = document.getElementById("query-latency-tbody");
    if (latencyTbody && data.storage_benchmark) {
      latencyTbody.innerHTML = "";
      const latencyRows = [
        { name: "Q1: Đếm dòng toàn bảng (Full Scan)", csv: "0,508s (±0,104)", pq: "0,296s (±0,043)", speed: "Nhanh hơn 1,71x" },
        { name: "Q2: Tính điểm TB theo món (GroupBy)", csv: "0,697s (±0,099)", pq: "0,338s (±0,005)", speed: "Nhanh hơn 2,06x" },
        { name: "Q3: Chiếu 3 cột & lọc (Column Pushdown)", csv: "0,507s (±0,102)", pq: "0,281s (±0,012)", speed: "Nhanh hơn 1,80x" }
      ];

      latencyRows.forEach((r) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `<td>${r.name}</td><td class="num-cell">${r.csv}</td><td class="num-cell">${r.pq}</td><td class="num-cell" style="color: var(--brand-green); font-weight:700;">${r.speed}</td>`;
        latencyTbody.appendChild(tr);
      });
    }

    // 4. Biểu đồ mở rộng quy mô SVG nếu tab đang mở
    if (state.systemTab === "scalability" && window.DashboardCharts?.renderScalabilityChart) {
      window.DashboardCharts.renderScalabilityChart("scalability-chart-container", data.scalability);
    }
  }

  // =========================================================================
  // TRANG 3: HÀNH VI
  // =========================================================================
  function setupPage3Handlers() {
    const dsBtns = document.querySelectorAll("#behavior-dataset-switch .dataset-btn");
    dsBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        dsBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.behaviorMode = btn.getAttribute("data-bds");
        state.selectedClusterIndex = 0;
        renderPage3Behavior();
      });
    });
  }

  function renderPage3Behavior() {
    const data = window.WEB_DATA_BEHAVIOR;
    if (!data) return;

    const titleEl = document.getElementById("title-page-hanh-vi");
    const ruleNoteEl = document.getElementById("behavior-rule-note");
    const clusterSelectBadge = document.getElementById("behavior-cluster-select-badge");
    const repItemsTitle = document.getElementById("rep-items-title");

    let clusterRows = [];
    let isVnUsers = false;
    let isVnFoods = false;

    if (state.behaviorMode === "food_com") {
      titleEl.textContent = "Người dùng Food.com chia 4 nhóm rõ rệt theo mức độ khắt khe và thời gian; ViFoodRec chưa phân hóa";
      ruleNoteEl.textContent = "4 cụm Food.com có độ lệch rõ rệt so với trung bình hệ thống: nhóm khắt khe điểm TB 3,83; nhóm chuộng món nhanh gọn 45,5 phút.";
      clusterRows = data.fc_user_clusters.filter((r) => r.cluster !== -1);
      repItemsTitle.textContent = "Món ăn ưa chuộng tiêu biểu của cụm người dùng Food.com";
    } else if (state.behaviorMode === "vifoodrec_users") {
      titleEl.textContent = "Các cụm người dùng ViFoodRec chưa phân biệt rõ (độ lệch trên mọi đặc trưng < 10%)";
      ruleNoteEl.textContent = "Quy tắc trung thực: Độ lệch mọi đặc trưng < 10% (điểm TB 3,00 / 2,96 / 3,03). Không gán nhãn chủ quan, giữ tên Cụm 1, 2, 3.";
      clusterRows = data.vn_user_clusters.filter((r) => r.cluster !== -1);
      isVnUsers = true;
      repItemsTitle.textContent = "Món ăn được chấm điểm cao trong cụm người dùng";
    } else if (state.behaviorMode === "vifoodrec_foods") {
      titleEl.textContent = "Món ăn Việt Nam phân thành 4 cụm dinh dưỡng: Chiên xào đậm vị, canh hầm ít đường, thanh tịnh, ít calo";
      ruleNoteEl.textContent = "Phân cụm món ăn ViFoodRec theo calo, đạm, béo, đường và thời gian nấu: 4 cụm thể hiện sự phân hóa ẩm thực rõ rệt.";
      clusterRows = data.vn_food_clusters.filter((r) => r.cluster !== -1);
      isVnFoods = true;
      repItemsTitle.textContent = "Món ăn tiêu biểu của cụm dinh dưỡng ẩm thực";
    }

    const curCluster = clusterRows[state.selectedClusterIndex] || clusterRows[0];
    clusterSelectBadge.textContent = `Đang chọn: ${curCluster.cluster_name || `Cụm ${curCluster.cluster + 1}`}`;

    // Tính toán độ lệch % cho biểu đồ
    const overallRow = state.behaviorMode === "food_com"
      ? data.fc_user_clusters.find((r) => r.cluster === -1)
      : (isVnUsers ? data.vn_user_clusters.find((r) => r.cluster === -1) : data.vn_food_clusters.find((r) => r.cluster === -1));

    let featuresList = [];
    if (state.behaviorMode === "food_com") {
      featuresList = [
        { name: "Điểm TB", devPct: calcDevPct(curCluster.avg_rating, overallRow.avg_rating) },
        { name: "Thời gian nấu (phút)", devPct: calcDevPct(curCluster.avg_minutes, overallRow.avg_minutes) },
        { name: "Lượng calo (kcal)", devPct: calcDevPct(curCluster.avg_calories, overallRow.avg_calories) },
        { name: "Số nguyên liệu", devPct: calcDevPct(curCluster.avg_n_ingredients, overallRow.avg_n_ingredients) },
        { name: "Tỷ lệ điểm cao (≥4 sao)", devPct: calcDevPct(curCluster.pct_high_rating, overallRow.pct_high_rating) }
      ];
    } else if (isVnUsers) {
      featuresList = [
        { name: "Điểm TB (3,00)", devPct: calcDevPct(curCluster.avg_rating, overallRow.avg_rating) },
        { name: "Thời gian nấu (32,8p)", devPct: calcDevPct(curCluster.avg_time_high, overallRow.avg_time_high) },
        { name: "Lượng calo (390 kcal)", devPct: calcDevPct(curCluster.avg_calo_high, overallRow.avg_calo_high) },
        { name: "Tỷ lệ món mặn (31%)", devPct: calcDevPct(curCluster.pct_man_high, overallRow.pct_man_high) },
        { name: "Tỷ lệ món chay (1,6%)", devPct: calcDevPct(curCluster.pct_chay_high, overallRow.pct_chay_high) }
      ];
    } else if (isVnFoods) {
      featuresList = [
        { name: "Lượng calo (kcal)", devPct: calcDevPct(curCluster.calories, overallRow.calories) },
        { name: "Độ đạm (g protein)", devPct: calcDevPct(curCluster.protein, overallRow.protein) },
        { name: "Chất béo (g fat)", devPct: calcDevPct(curCluster.fat, overallRow.fat) },
        { name: "Lượng đường (g sugar)", devPct: calcDevPct(curCluster.sugar, overallRow.sugar) },
        { name: "Thời gian nấu (phút)", devPct: calcDevPct(curCluster.cooking_time_min, overallRow.cooking_time_min) }
      ];
    }

    if (window.DashboardCharts?.renderClusterDeviationChart) {
      window.DashboardCharts.renderClusterDeviationChart(
        "cluster-deviation-container",
        { features: featuresList },
        isVnUsers
      );
    }

    // Render danh sách cụm (hàng bấm chọn được)
    const listContainer = document.getElementById("cluster-profiles-list");
    if (listContainer) {
      listContainer.innerHTML = "";
      clusterRows.forEach((c, idx) => {
        const item = document.createElement("div");
        item.style.padding = "6px 10px";
        item.style.borderBottom = "1px solid var(--border)";
        item.style.cursor = "pointer";
        item.style.borderRadius = "2px";
        item.style.transition = "background-color 140ms";

        const isSelected = idx === state.selectedClusterIndex;
        item.style.backgroundColor = isSelected ? "#EBF3EE" : "transparent";
        item.style.borderLeft = isSelected ? "3px solid var(--brand-green)" : "3px solid transparent";

        const countVal = c.user_count !== undefined ? c.user_count : c.food_count;
        const pctVal = c.user_pct !== undefined ? c.user_pct : c.food_pct;
        const unitLabel = c.user_count !== undefined ? "người" : "món";

        // Tên cụm trung thực
        let displayName = c.cluster_name;
        if (isVnUsers) {
          displayName = `Cụm ${c.cluster + 1} (Chưa phân hóa)`;
        }

        item.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: baseline;">
            <strong style="color: var(--text-primary); font-size: 0.9375rem;">${displayName}</strong>
            <span style="font-size: 0.8125rem; font-weight: 600; color: var(--brand-green);">${window.FormatUtils.formatNumber(countVal)} ${unitLabel} (${pctVal}%)</span>
          </div>
        `;

        item.addEventListener("click", () => {
          state.selectedClusterIndex = idx;
          renderPage3Behavior();
        });

        listContainer.appendChild(item);
      });
    }

    // Render danh sách món tiêu biểu của cụm đang chọn
    const repContainer = document.getElementById("rep-items-container");
    if (repContainer) {
      repContainer.innerHTML = "";
      const cId = curCluster.cluster;
      const repFoods = data.representative_foods_vn?.[cId] || [];

      if (repFoods.length > 0) {
        repFoods.forEach((f, i) => {
          const row = document.createElement("div");
          row.style.padding = "4px 8px";
          row.style.borderBottom = "1px solid var(--border)";
          row.style.display = "flex";
          row.style.justifyContent = "space-between";
          row.style.fontSize = "0.875rem";
          row.innerHTML = `
            <span><strong>#${i + 1}</strong> ${f.dish_name} <span class="menu-item-type ${f.dish_type === 'Món chay' ? 'chay' : 'man'}">${f.dish_type}</span></span>
            <span style="color: var(--text-secondary);">${f.calories ? `${f.calories} kcal` : ''} ${f.cooking_time_min ? `• ${f.cooking_time_min}p` : ''}</span>
          `;
          repContainer.appendChild(row);
        });
      } else {
        repContainer.innerHTML = `<div style="padding: 10px; color: var(--text-secondary); font-size: 0.875rem;">Đại diện cụm người dùng: Phản ánh qua sở thích chấm sao và thời gian chế biến.</div>`;
      }
    }
  }

  function calcDevPct(val, base) {
    if (!base || base === 0) return 0;
    return ((Number(val) - Number(base)) / Number(base)) * 100;
  }

  // =========================================================================
  // TRANG 4: GỢI Ý MÓN ĂN (TÂM ĐIỂM THIẾT KẾ)
  // =========================================================================
  function setupPage4Handlers() {
    // 1. Chuyển bộ dữ liệu (ViFoodRec / Food.com)
    const rdsBtns = document.querySelectorAll("#recs-dataset-switch .dataset-btn");
    rdsBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        rdsBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.recsDataset = btn.getAttribute("data-rds");

        if (state.recsDataset === "food_com" && !window.WEB_DATA_RECS_FC) {
          // Lazy load script Food.com
          loadScript("data/recs_foodcom.js", () => {
            initPage4Controls();
            renderPage4Recs();
          });
        } else {
          initPage4Controls();
          renderPage4Recs();
        }
      });
    });

    // 2. Chuyển chế độ: Người dùng có sẵn / Người dùng mới
    const modeBtns = document.querySelectorAll("#recs-mode-switch .seg-btn");
    modeBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        modeBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.recsMode = btn.getAttribute("data-mode");

        document.getElementById("mode-existing-box").style.display = state.recsMode === "existing" ? "block" : "none";
        document.getElementById("mode-new-box").style.display = state.recsMode === "new" ? "block" : "none";

        renderPage4Recs();
      });
    });

    // 3. Bộ lọc loại món
    const dtypeBtns = document.querySelectorAll("#filter-dish-type .seg-btn");
    dtypeBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        dtypeBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.recsFilters.dishType = btn.getAttribute("data-dtype");
        renderPage4Recs();
      });
    });

    // 4. Thanh trượt thời gian tối đa
    const timeSlider = document.getElementById("filter-max-time");
    const timeLabel = document.getElementById("label-max-time");
    if (timeSlider && timeLabel) {
      timeSlider.addEventListener("input", (e) => {
        const val = Number(e.target.value);
        if (val >= 120) {
          state.recsFilters.maxTime = null;
          timeLabel.textContent = "Không giới hạn";
        } else {
          state.recsFilters.maxTime = val;
          timeLabel.textContent = `≤ ${val} phút`;
        }
        renderPage4Recs();
      });
    }

    // 5. Thanh trượt calo tối đa
    const caloSlider = document.getElementById("filter-max-calo");
    const caloLabel = document.getElementById("label-max-calo");
    if (caloSlider && caloLabel) {
      caloSlider.addEventListener("input", (e) => {
        const val = Number(e.target.value);
        if (val >= 1000) {
          state.recsFilters.maxCalo = null;
          caloLabel.textContent = "Không giới hạn";
        } else {
          state.recsFilters.maxCalo = val;
          caloLabel.textContent = `≤ ${val} kcal`;
        }
        renderPage4Recs();
      });
    }

    // 6. Số lượng món Top-N
    const topNSelect = document.getElementById("filter-top-n");
    if (topNSelect) {
      topNSelect.addEventListener("change", (e) => {
        state.recsFilters.topN = Number(e.target.value);
        renderPage4Recs();
      });
    }

    // 7. Nút xóa bộ lọc
    const btnReset = document.getElementById("btn-reset-filters");
    if (btnReset) {
      btnReset.addEventListener("click", () => {
        state.recsFilters = { dishType: "all", maxTime: null, maxCalo: null, topN: 10 };
        dtypeBtns.forEach((b) => b.classList.toggle("active", b.getAttribute("data-dtype") === "all"));
        if (timeSlider) timeSlider.value = 120;
        if (timeLabel) timeLabel.textContent = "Không giới hạn";
        if (caloSlider) caloSlider.value = 1000;
        if (caloLabel) caloLabel.textContent = "Không giới hạn";
        if (topNSelect) topNSelect.value = "10";
        renderPage4Recs();
      });
    }

    // 8. Tìm kiếm món không dấu cho Cold-Start
    const searchInput = document.getElementById("search-food-input");
    const searchDropdown = document.getElementById("search-results-dropdown");
    if (searchInput && searchDropdown) {
      searchInput.addEventListener("input", (e) => {
        const query = window.FormatUtils.removeVietnameseTones(e.target.value).trim();
        if (query.length < 2) {
          searchDropdown.style.display = "none";
          return;
        }

        const data = state.recsDataset === "vifoodrec" ? window.WEB_DATA_RECS_VN : window.WEB_DATA_RECS_FC;
        if (!data?.catalog) return;

        const idKey = state.recsDataset === "vifoodrec" ? "food_id" : "recipe_id";
        const nameKey = state.recsDataset === "vifoodrec" ? "dish_name" : "name";

        const matches = data.catalog
          .filter((item) => window.FormatUtils.removeVietnameseTones(item[nameKey]).includes(query))
          .slice(0, 8);

        searchDropdown.innerHTML = "";
        if (matches.length > 0) {
          searchDropdown.style.display = "block";
          matches.forEach((item) => {
            const div = document.createElement("div");
            div.className = "search-item";
            div.textContent = `${item[nameKey]} (${item.dish_type || (item.calories ? `${item.calories} kcal` : '')})`;
            div.addEventListener("click", () => {
              addColdStartDish(Number(item[idKey]));
              searchInput.value = "";
              searchDropdown.style.display = "none";
            });
            searchDropdown.appendChild(div);
          });
        } else {
          searchDropdown.style.display = "none";
        }
      });

      document.addEventListener("click", (e) => {
        if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
          searchDropdown.style.display = "none";
        }
      });
    }

    initPage4Controls();
  }

  function initPage4Controls() {
    const data = state.recsDataset === "vifoodrec" ? window.WEB_DATA_RECS_VN : window.WEB_DATA_RECS_FC;
    if (!data) return;

    // Ẩn/hiện bộ lọc mặn/chay nếu là Food.com
    const typeBox = document.getElementById("filter-type-box");
    if (typeBox) {
      typeBox.style.display = state.recsDataset === "vifoodrec" ? "block" : "none";
    }

    // Nạp danh sách User ID
    const userSelect = document.getElementById("select-user-id");
    if (userSelect && data.recommendations) {
      userSelect.innerHTML = "";
      const uniqueUsers = Array.from(new Set(data.recommendations.map((r) => r.user_id))).slice(0, 101);
      uniqueUsers.forEach((uid) => {
        const opt = document.createElement("option");
        opt.value = uid;
        opt.textContent = `Người dùng #${uid}`;
        if (uid === state.selectedUserId) opt.selected = true;
        userSelect.appendChild(opt);
      });

      userSelect.addEventListener("change", (e) => {
        state.selectedUserId = Number(e.target.value);
        renderPage4Recs();
      });
    }

    renderColdStartChips();
  }

  function addColdStartDish(id) {
    if (!state.selectedColdStartIds.includes(id)) {
      if (state.selectedColdStartIds.length >= 5) {
        state.selectedColdStartIds.shift(); // Tối đa 5 món, bỏ món cũ nhất
      }
      state.selectedColdStartIds.push(id);
      renderColdStartChips();
      renderPage4Recs();
    }
  }

  function removeColdStartDish(id) {
    state.selectedColdStartIds = state.selectedColdStartIds.filter((x) => x !== id);
    renderColdStartChips();
    renderPage4Recs();
  }

  function renderColdStartChips() {
    const container = document.getElementById("selected-chips-container");
    const countEl = document.getElementById("selected-count");
    if (!container) return;

    container.innerHTML = "";
    if (countEl) countEl.textContent = state.selectedColdStartIds.length;

    const data = state.recsDataset === "vifoodrec" ? window.WEB_DATA_RECS_VN : window.WEB_DATA_RECS_FC;
    if (!data?.catalog) return;

    const idKey = state.recsDataset === "vifoodrec" ? "food_id" : "recipe_id";
    const nameKey = state.recsDataset === "vifoodrec" ? "dish_name" : "name";

    state.selectedColdStartIds.forEach((id) => {
      const dish = data.catalog.find((d) => d[idKey] === id);
      const name = dish ? dish[nameKey] : `Món #${id}`;

      const chip = document.createElement("span");
      chip.className = "food-chip";
      chip.innerHTML = `${name} <span class="food-chip-remove" title="Bỏ chọn">×</span>`;
      chip.querySelector(".food-chip-remove").addEventListener("click", () => removeColdStartDish(id));
      container.appendChild(chip);
    });
  }

  function renderPage4Recs() {
    const data = state.recsDataset === "vifoodrec" ? window.WEB_DATA_RECS_VN : window.WEB_DATA_RECS_FC;
    if (!data) return;

    const idKey = state.recsDataset === "vifoodrec" ? "food_id" : "recipe_id";
    const nameKey = state.recsDataset === "vifoodrec" ? "dish_name" : "name";
    const timeKey = state.recsDataset === "vifoodrec" ? "cooking_time_min" : "minutes_clean";

    // Cập nhật huy hiệu cụm người dùng
    const badgeEl = document.getElementById("user-cluster-badge");
    if (badgeEl && state.recsMode === "existing") {
      const uInfo = data.user_clusters?.[state.selectedUserId];
      if (uInfo) {
        badgeEl.textContent = `Hành vi: ${uInfo.cluster_name}`;
      } else {
        badgeEl.textContent = "";
      }
    }

    let items = [];

    if (state.recsMode === "existing") {
      // 1. Gợi ý cá nhân hóa cho người dùng có sẵn (ALS)
      const userRecs = data.recommendations.filter((r) => r.user_id === state.selectedUserId);
      items = userRecs.map((r) => {
        const cat = data.catalog.find((c) => c[idKey] === r[idKey]) || {};
        return {
          id: r[idKey],
          name: r[nameKey] || cat[nameKey],
          dish_type: r.dish_type || cat.dish_type,
          calories: r.calories !== undefined ? r.calories : cat.calories,
          time: cat[timeKey] || r.cooking_time,
          ingredients: cat.ingredients || "",
          reason: null
        };
      });
    } else {
      // 2. Gợi ý Cold-Start cho người dùng mới qua Item Neighbors
      const selSet = new Set(state.selectedColdStartIds);
      const candidates = {};

      state.selectedColdStartIds.forEach((srcId) => {
        const srcDish = data.catalog.find((c) => c[idKey] === srcId);
        const srcName = srcDish ? srcDish[nameKey] : `Món #${srcId}`;
        const nbrList = data.item_neighbors?.[srcId] || [];

        nbrList.forEach(([nid, score]) => {
          if (selSet.has(nid)) return; // Bỏ qua món đã chọn
          if (!candidates[nid]) {
            candidates[nid] = { totalScore: score, topMatch: srcName, topScore: score, count: 1 };
          } else {
            candidates[nid].totalScore += score;
            candidates[nid].count += 1;
            if (score > candidates[nid].topScore) {
              candidates[nid].topScore = score;
              candidates[nid].topMatch = srcName;
            }
          }
        });
      });

      // Sắp xếp giảm dần theo tổng điểm tương đồng
      const sortedCand = Object.entries(candidates).sort((a, b) => b[1].totalScore - a[1].totalScore);

      items = sortedCand.map(([nidStr, info]) => {
        const nid = Number(nidStr);
        const cat = data.catalog.find((c) => c[idKey] === nid) || {};
        const reason = info.count === 1
          ? `Tương đồng ${(info.topScore * 100).toFixed(1).replace(".", ",")}% với '${info.topMatch}'`
          : `Tương đồng ${(info.topScore * 100).toFixed(1).replace(".", ",")}% với '${info.topMatch}' và ${info.count - 1} món khác bạn chọn`;

        return {
          id: nid,
          name: cat[nameKey] || `Món #${nid}`,
          dish_type: cat.dish_type,
          calories: cat.calories,
          time: cat[timeKey],
          ingredients: cat.ingredients || "",
          reason: reason
        };
      });
    }

    // Áp dụng bộ lọc
    if (state.recsFilters.dishType !== "all" && state.recsDataset === "vifoodrec") {
      items = items.filter((item) => item.dish_type === state.recsFilters.dishType);
    }
    if (state.recsFilters.maxTime !== null) {
      items = items.filter((item) => !item.time || Number(item.time) <= state.recsFilters.maxTime);
    }
    if (state.recsFilters.maxCalo !== null) {
      items = items.filter((item) => !item.calories || Number(item.calories) <= state.recsFilters.maxCalo);
    }

    const totalFiltered = items.length;
    const topN = state.recsFilters.topN;
    const finalItems = items.slice(0, topN);

    // Render danh sách hàng thực đơn
    const menuList = document.getElementById("recs-menu-list");
    const countHeader = document.getElementById("recs-result-count");
    const warnBanner = document.getElementById("filter-warning-banner");

    if (countHeader) {
      countHeader.textContent = `Hiển thị ${finalItems.length}/${topN} món phù hợp`;
    }

    if (warnBanner) {
      if (totalFiltered < topN) {
        warnBanner.style.display = "block";
        warnBanner.textContent = `Chỉ còn lại ${totalFiltered} món phù hợp bộ lọc. Hãy tăng thời gian nấu hoặc lượng calo tối đa để nhận đủ ${topN} món.`;
      } else {
        warnBanner.style.display = "none";
      }
    }

    if (menuList) {
      menuList.innerHTML = "";
      if (finalItems.length === 0) {
        menuList.innerHTML = `<div style="padding: 24px; text-align: center; color: var(--text-secondary);">Không có món ăn nào thỏa mãn bộ lọc hiện tại. Vui lòng bấm "Xóa bộ lọc".</div>`;
        return;
      }

      finalItems.forEach((item, idx) => {
        const row = document.createElement("div");
        row.className = "menu-item";

        const typeBadge = item.dish_type
          ? `<span class="menu-item-type ${item.dish_type === 'Món chay' ? 'chay' : 'man'}">${item.dish_type}</span>`
          : "";
        const caloStr = item.calories ? `${window.FormatUtils.formatNumber(item.calories)} kcal` : "";
        const timeStr = item.time ? `${item.time} phút` : "";
        const ingredientsStr = item.ingredients ? `Nguyên liệu chính: ${item.ingredients}` : "";
        const reasonHtml = item.reason ? `<div class="menu-item-reason">• ${item.reason}</div>` : "";

        row.innerHTML = `
          <div class="menu-item-main">
            <div class="menu-item-left">
              <span class="menu-item-rank">#${idx + 1}</span>
              <span class="menu-item-name">${item.name}</span>
            </div>
            <div class="menu-item-specs">
              ${typeBadge}
              ${caloStr ? `<span>${caloStr}</span>` : ""}
              ${timeStr ? `<span>${timeStr}</span>` : ""}
            </div>
          </div>
          ${ingredientsStr ? `<div class="menu-item-sub">${ingredientsStr}</div>` : ""}
          ${reasonHtml}
        `;
        menuList.appendChild(row);
      });
    }
  }

  // =========================================================================
  // TRANG 5: MÔ HÌNH
  // =========================================================================
  function setupPage5Handlers() {
    const mdsBtns = document.querySelectorAll("#model-dataset-switch .dataset-btn");
    mdsBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        mdsBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.modelDataset = btn.getAttribute("data-mds");
        renderPage5Models();
      });
    });
  }

  function renderPage5Models() {
    const data = window.WEB_DATA_MODELS;
    if (!data) return;

    const isVn = state.modelDataset === "food_vietnam";
    const subModels = data.model_comparison.filter((r) => r.dataset === state.modelDataset);

    // 1. Tiêu đề phát hiện trung thực sinh từ số liệu thật
    const titleEl = document.getElementById("title-page-mo-hinh");
    if (titleEl) {
      if (isVn) {
        titleEl.textContent = "ViFoodRec: Global Mean có RMSE tốt nhất (1,2866), ALS đạt 1,3832 do dữ liệu khảo sát hạn chế";
      } else {
        titleEl.textContent = "Food.com: Smoothed Item Mean có RMSE tốt nhất (0,6177), ALS đạt 0,6747 do 78,4% đánh giá là 5 sao";
      }
    }

    // 2. Tìm giá trị tốt nhất mỗi cột để gạch chân và in đậm
    let minRmse = Infinity, minMae = Infinity, maxP10 = -1, maxR10 = -1;
    subModels.forEach((m) => {
      if (m.RMSE < minRmse) minRmse = m.RMSE;
      if (m.MAE < minMae) minMae = m.MAE;
      if (m["Precision@10"] > maxP10) maxP10 = m["Precision@10"];
      if (m["Recall@10"] > maxR10) maxR10 = m["Recall@10"];
    });

    const compTbody = document.getElementById("model-comparison-tbody");
    if (compTbody) {
      compTbody.innerHTML = "";
      subModels.forEach((m) => {
        const isBestRmse = Math.abs(m.RMSE - minRmse) < 1e-4;
        const isBestMae = Math.abs(m.MAE - minMae) < 1e-4;
        const isBestP10 = Math.abs(m["Precision@10"] - maxP10) < 1e-4 && maxP10 > 0;
        const isBestR10 = Math.abs(m["Recall@10"] - maxR10) < 1e-4 && maxR10 > 0;

        const isAls = m.model.includes("ALS");
        const rowBg = isAls ? "background-color: #FDF9F6;" : "";

        const tr = document.createElement("tr");
        if (rowBg) tr.style = rowBg;

        tr.innerHTML = `
          <td><strong>${m.model}</strong> ${isAls ? '<span style="color:var(--accent-orange); font-size:12px;">(Mô hình đề xuất)</span>' : ''}</td>
          <td class="num-cell" style="${isBestRmse ? 'font-weight:700; text-decoration:underline;' : ''}">${window.FormatUtils.formatNumber(m.RMSE, 4)}</td>
          <td class="num-cell" style="${isBestMae ? 'font-weight:700; text-decoration:underline;' : ''}">${window.FormatUtils.formatNumber(m.MAE, 4)}</td>
          <td class="num-cell" style="${isBestP10 ? 'font-weight:700; text-decoration:underline;' : ''}">${window.FormatUtils.formatNumber(m["Precision@10"], 5)}</td>
          <td class="num-cell" style="${isBestR10 ? 'font-weight:700; text-decoration:underline;' : ''}">${window.FormatUtils.formatNumber(m["Recall@10"], 5)}</td>
          <td class="num-cell">${window.FormatUtils.formatPercent(m.coverage, 0, false)}</td>
        `;
        compTbody.appendChild(tr);
      });
    }

    // 3. Bảng Tinh chỉnh ALS (Top 5 cấu hình)
    const tuneTbody = document.getElementById("als-tuning-tbody");
    if (tuneTbody) {
      tuneTbody.innerHTML = "";
      const tuneRows = isVn ? data.als_tuning_vn : data.als_tuning_fc;
      const sortedTune = [...tuneRows].sort((a, b) => a.val_rmse - b.val_rmse).slice(0, 5);

      sortedTune.forEach((t, idx) => {
        const isBest = idx === 0;
        const tr = document.createElement("tr");
        if (isBest) tr.style = "background-color: #EBF3EE; font-weight: 600;";

        tr.innerHTML = `
          <td>#${idx + 1} ${isBest ? '(Chọn)' : ''}</td>
          <td class="num-cell">${t.rank}</td>
          <td class="num-cell">${t.regParam}</td>
          <td class="num-cell">${t.maxIter}</td>
          <td class="num-cell" style="${isBest ? 'color: var(--brand-green); font-weight: 700;' : ''}">${window.FormatUtils.formatNumber(t.val_rmse, 4)}</td>
          <td class="num-cell">${t.train_time_sec ? `${t.train_time_sec}s` : '—'}</td>
        `;
        tuneTbody.appendChild(tr);
      });
    }

    // 4. Biểu đồ cột phân rã RMSE theo bậc điểm thật SVG
    if (window.DashboardCharts?.renderRmseBreakdownChart) {
      window.DashboardCharts.renderRmseBreakdownChart(
        "rmse-breakdown-chart-container",
        data.als_rmse_breakdown,
        data.baseline_rmse_breakdown,
        state.modelDataset
      );
    }
  }

  // =========================================================================
  // TIỆN ÍCH MODAL & CHÚ GIẢI
  // =========================================================================
  function setupKeyboardShortcuts() {
    window.addEventListener("keydown", (e) => {
      if (["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement?.tagName)) {
        if (e.key === "Escape") {
          document.activeElement.blur();
        }
        return;
      }

      if (e.key === "Escape") {
        closeGlossary();
        closeTuningModal();
        return;
      }

      const matchedRoute = ROUTES.find((r) => r.key === e.key);
      if (matchedRoute) {
        navigate(matchedRoute.hash);
      }
    });
  }

  function setupGlossaryDrawer() {
    const btnOpen = document.getElementById("btn-open-glossary");
    const btnClose = document.getElementById("btn-close-glossary");
    const backdrop = document.getElementById("drawer-backdrop");

    if (btnOpen) btnOpen.addEventListener("click", openGlossary);
    if (btnClose) btnClose.addEventListener("click", closeGlossary);
    if (backdrop) backdrop.addEventListener("click", () => {
      closeGlossary();
      closeTuningModal();
    });
  }

  function openGlossary() {
    state.isGlossaryOpen = true;
    document.getElementById("drawer-backdrop")?.classList.add("open");
    document.getElementById("glossary-drawer")?.classList.add("open");
  }

  function closeGlossary() {
    state.isGlossaryOpen = false;
    document.getElementById("drawer-backdrop")?.classList.remove("open");
    document.getElementById("glossary-drawer")?.classList.remove("open");
  }

  function setupTuningModal() {
    const btnOpen = document.getElementById("btn-open-tuning-modal");
    const btnClose = document.getElementById("btn-close-tuning-modal");

    if (btnOpen) btnOpen.addEventListener("click", openTuningModal);
    if (btnClose) btnClose.addEventListener("click", closeTuningModal);
  }

  function openTuningModal() {
    state.isTuningModalOpen = true;
    document.getElementById("drawer-backdrop")?.classList.add("open");
    const modal = document.getElementById("tuning-modal");
    if (modal) {
      modal.classList.add("open");
      const tbody = document.getElementById("kmeans-tuning-tbody");
      if (tbody && window.WEB_DATA_BEHAVIOR?.kmeans_tuning) {
        tbody.innerHTML = "";
        window.WEB_DATA_BEHAVIOR.kmeans_tuning.forEach((r) => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>${r.task}</td>
            <td class="num-cell">${r.k}</td>
            <td class="num-cell" style="font-weight:600;">${window.FormatUtils.formatNumber(r.silhouette, 4)}</td>
            <td class="num-cell">${window.FormatUtils.formatNumber(r.wssse, 1)}</td>
            <td class="num-cell">${r.time_sec}s</td>
          `;
          tbody.appendChild(tr);
        });
      }
    }
  }

  function closeTuningModal() {
    state.isTuningModalOpen = false;
    document.getElementById("drawer-backdrop")?.classList.remove("open");
    document.getElementById("tuning-modal")?.classList.remove("open");
  }

  function setupResizeHandler() {
    let resizeTimer;
    window.addEventListener("resize", () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        renderPage(ROUTES.find((r) => r.hash === state.currentRoute)?.pageId || "page-du-lieu");
      }, 100);
    });
  }

  function loadScript(url, callback) {
    const s = document.createElement("script");
    s.src = url;
    s.onload = callback;
    document.body.appendChild(s);
  }

  // Khởi chạy khi DOM sẵn sàng
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.DashboardApp = {
    state,
    navigate,
    openGlossary,
    closeGlossary,
    renderPage
  };

})();
