/**
 * Điều khiển chính của dashboard web tĩnh.
 * - Điều hướng theo URL hash (#/du-lieu, #/he-thong, #/hanh-vi, #/goi-y, #/mo-hinh); phím 1 đến 5 chuyển trang, Esc đóng ngăn phụ.
 * - Mọi số và chữ hiển thị lấy từ web/data/*.js (do src/export_for_web.py sinh); số đi qua FormatUtils.fmt (một hàm duy nhất).
 * - Nhãn hiển thị (loại món, tên mô hình) lấy từ web/data/labels.js (nguồn: src/web_labels.py).
 */

(function () {
  "use strict";

  const F = window.FormatUtils;
  const LB = window.WEB_LABELS || {};

  const ROUTES = [
    { key: "1", hash: "#/du-lieu", pageId: "page-du-lieu" },
    { key: "2", hash: "#/he-thong", pageId: "page-he-thong" },
    { key: "3", hash: "#/hanh-vi", pageId: "page-hanh-vi" },
    { key: "4", hash: "#/goi-y", pageId: "page-goi-y" },
    { key: "5", hash: "#/mo-hinh", pageId: "page-mo-hinh" }
  ];

  const state = {
    currentRoute: "#/du-lieu",
    systemTab: "storage",
    behaviorMode: "food_com", // food_com | vifoodrec_users | vifoodrec_foods
    selectedClusterIndex: 0,
    recsDataset: "vifoodrec", // vifoodrec | food_com
    recsMode: "existing",     // existing | new
    selectedUserId: { vifoodrec: 70, food_com: null },
    selectedColdStartIds: { vifoodrec: [1248, 1082], food_com: [] },
    expandedIngredients: new Set(),
    recsFilters: { dishType: "all", maxTime: null, maxCalo: null, topN: 10 },
    modelDataset: "food_vietnam"
  };

  // ---------------------------------------------------------------------------
  // Tiện ích DOM và nhãn
  // ---------------------------------------------------------------------------
  function $(id) { return document.getElementById(id); }

  function h(tag, className, text) {
    const e = document.createElement(tag);
    if (className) e.className = className;
    if (text !== undefined && text !== null) e.textContent = text;
    return e;
  }

  function dishLabel(raw) {
    return raw && LB.dish_type && LB.dish_type[raw] ? LB.dish_type[raw] : raw;
  }

  function clusterLabel(name) {
    let out = String(name || "");
    (LB.cluster_name_replacements || []).forEach(([a, b]) => { out = out.split(a).join(b); });
    return out;
  }

  function setSource(id, source) {
    const e = $(id);
    if (e) e.textContent = source ? `Nguồn số liệu: ${source}` : "";
  }

  // ---------------------------------------------------------------------------
  // Khởi tạo và điều hướng
  // ---------------------------------------------------------------------------
  function init() {
    setupNavigation();
    setupKeyboard();
    setupGlossary();
    setupTuningModal();
    setupSystemTabs();
    setupBehaviorSwitch();
    setupRecsHandlers();
    setupModelSwitch();
    window.addEventListener("resize", debounce(() => renderPage(currentPageId()), 120));
    navigate(window.location.hash || "#/du-lieu");
  }

  function debounce(fn, ms) {
    let t;
    return () => { clearTimeout(t); t = setTimeout(fn, ms); };
  }

  function currentPageId() {
    return (ROUTES.find((r) => r.hash === state.currentRoute) || ROUTES[0]).pageId;
  }

  function setupNavigation() {
    window.addEventListener("hashchange", () => navigate(window.location.hash));
    document.querySelectorAll(".nav-link").forEach((link) => {
      link.addEventListener("click", () => navigate(link.getAttribute("href")));
    });
  }

  function navigate(hash) {
    const route = ROUTES.find((r) => r.hash === hash) || ROUTES[0];
    state.currentRoute = route.hash;
    if (window.location.hash !== route.hash) window.location.hash = route.hash;
    document.querySelectorAll(".nav-link").forEach((l) => l.classList.toggle("active", l.getAttribute("href") === route.hash));
    document.querySelectorAll(".page-view").forEach((v) => v.classList.remove("active"));
    const view = $(route.pageId);
    if (view) view.classList.add("active");
    renderPage(route.pageId);
  }

  function renderPage(pageId) {
    ({
      "page-du-lieu": renderDataPage,
      "page-he-thong": renderSystemPage,
      "page-hanh-vi": renderBehaviorPage,
      "page-goi-y": renderRecsPage,
      "page-mo-hinh": renderModelsPage
    }[pageId] || (() => {}))();
  }

  // ===========================================================================
  // Trang 1: Dữ liệu
  // ===========================================================================
  function renderDataPage() {
    const d = window.WEB_DATA_SUMMARY;
    if (!d) return;
    const f = d.facts;

    $("title-page-du-lieu").textContent =
      `ViFoodRec nhỏ nhưng dày (độ thưa ${F.fmtPct(f.vn_sparsity, 2)}), Food.com lớn nhưng độ thưa ${F.fmtPct(f.fc_sparsity, 2)}`;

    const tbody = $("dataset-comparison-tbody");
    tbody.innerHTML = "";
    d.dataset_comparison.forEach((row) => {
      const tr = h("tr");
      tr.appendChild(h("td", "", row.label));
      [row.vifoodrec, row.food_com].forEach((v) => tr.appendChild(h("td", "num-cell", formatComparison(row.key, v))));
      tbody.appendChild(tr);
    });

    const ratingMin = Math.min(...d.rating_dist_vn.map((r) => r.rating));
    const ratingMax = Math.max(...d.rating_dist_vn.map((r) => r.rating));
    window.DashboardCharts.renderCleaningFunnel("cleaning-funnel-container", d.funnel, { ratingMin, ratingMax });
    window.DashboardCharts.renderRatingDist("rating-dist-container", d.rating_dist_vn, d.rating_dist_fc);

    const limits = $("data-limits-block");
    limits.innerHTML = "";
    limits.appendChild(h("strong", "", "Giới hạn dữ liệu"));
    [
      `ViFoodRec có ${F.fmt(f.vn_users)} người dùng và ${F.fmt(f.vn_items)} món; mỗi mức trong ${F.fmt(f.vn_levels)} mức điểm chiếm từ ${F.fmtPct(f.vn_min_pct, 2)} đến ${F.fmtPct(f.vn_max_pct, 2)} số đánh giá.`,
      `Food.com có ${F.fmt(f.fc_users)} người dùng và ${F.fmt(f.fc_items)} món; ${F.fmtPct(f.fc_pct5, 1)} số đánh giá là 5 sao.`,
      `Hai bộ không có người dùng chung nên không gộp được; ${F.fmt(f.vn_fk_dropped)} dòng ViFoodRec bị loại vì mã món không có trong danh mục.`
    ].forEach((t) => limits.appendChild(h("span", "data-limits-item", t)));
    setSource("source-du-lieu", d.source);
  }

  function formatComparison(key, v) {
    if (key.includes("Độ thưa")) return F.fmtPct(v, 2);
    if (key.includes("Điểm TB")) return F.fmt(v, 2);
    return F.fmt(v, 0);
  }

  // ===========================================================================
  // Trang 2: Hệ thống
  // ===========================================================================
  function setupSystemTabs() {
    const btnS = $("tab-btn-storage");
    const btnC = $("tab-btn-scalability");
    btnS.addEventListener("click", () => { state.systemTab = "storage"; renderSystemPage(); });
    btnC.addEventListener("click", () => { state.systemTab = "scalability"; renderSystemPage(); });
  }

  function renderSystemPage() {
    const d = window.WEB_DATA_SYSTEM;
    if (!d) return;
    const info = d.cluster_info;
    const clean = d.storage_rows.filter((r) => /sạch/.test(r.label));
    const minR = Math.min(...clean.map((r) => r.ratio));
    const maxR = Math.max(...clean.map((r) => r.ratio));

    $("title-page-he-thong").textContent =
      `HDFS ${info.hdfs.version} và Spark ${info.spark.version}; Parquet nhỏ hơn CSV ${F.fmt(minR, 2)} đến ${F.fmt(maxR, 2)} lần ở dữ liệu sạch`;
    $("system-host").textContent = `${info.host.os}, ${F.fmt(info.host.ram_gb)} GB RAM, Docker ${F.fmt(info.host.docker_ram_gb)} GB`;

    // Tab
    const isStorage = state.systemTab === "storage";
    $("tab-btn-storage").classList.toggle("active", isStorage);
    $("tab-btn-scalability").classList.toggle("active", !isStorage);
    $("tab-storage-body").hidden = !isStorage;
    $("tab-scalability-body").hidden = isStorage;
    $("system-tab-sub").textContent = isStorage ? "Parquet nén Snappy so với CSV" : "Thời gian chạy cả pipeline trên Food.com";

    window.DashboardCharts.renderArchitecture("architecture-diagram-container", info);

    // Bảng thông số cụm (màn hình cao hiện thêm hai dòng để không để trống)
    const tall = window.innerHeight >= 950;
    const rows = [
      ["HDFS", "Phiên bản Hadoop", info.hdfs.version],
      ...(tall ? [["HDFS", "Số NameNode", F.fmt(info.hdfs.namenodes)]] : []),
      ["HDFS", "Số DataNode", F.fmt(info.hdfs.datanodes)],
      ["HDFS", "Replication", F.fmt(info.hdfs.replication)],
      ...info.hdfs.fsck.map((x) => ["HDFS", `Kiểm tra fsck ${x.path}`,
        `${x.status}, thiếu bản sao ${F.fmt(x.under_replicated)} (${F.fmt(x.files)} tệp)`]),
      ["Spark", "Phiên bản", info.spark.version],
      ...(tall ? [["Spark", "Số Master", F.fmt(info.spark.masters)]] : []),
      ["Spark", "Số Worker", `${F.fmt(info.spark.workers)}, mỗi Worker ${F.fmt(info.spark.worker_cores)} nhân và ${F.fmt(info.spark.worker_ram_mb / 1000, 1)} GB`],
      ["Spark", "Tổng tài nguyên Worker", `${F.fmt(info.spark.total_cores)} nhân, ${F.fmt(info.spark.total_ram_mb / 1000, 0)} GB`]
    ];
    const tb = $("cluster-facts-tbody");
    tb.innerHTML = "";
    rows.forEach((r) => {
      const tr = h("tr");
      tr.appendChild(h("td", "", r[0]));
      tr.appendChild(h("td", "", r[1]));
      tr.appendChild(h("td", "num-cell", r[2]));
      tb.appendChild(tr);
    });

    // Tab lưu trữ
    const stb = $("storage-benchmark-tbody");
    stb.innerHTML = "";
    d.storage_rows.forEach((r) => {
      const tr = h("tr");
      tr.appendChild(h("td", "", r.label));
      tr.appendChild(h("td", "num-cell", F.fmtUnit(r.csv_mb, "MB", 2)));
      tr.appendChild(h("td", "num-cell", F.fmtUnit(r.parquet_mb, "MB", 2)));
      tr.appendChild(h("td", "num-cell strong-green", `${F.fmt(r.ratio, 2)} lần`));
      stb.appendChild(tr);
    });
    const ltb = $("query-latency-tbody");
    ltb.innerHTML = "";
    d.latency_rows.forEach((r) => {
      const tr = h("tr");
      tr.appendChild(h("td", "", r.label));
      tr.appendChild(h("td", "num-cell", `${F.fmtUnit(r.csv_avg, "s", 3)} (độ lệch ${F.fmt(r.csv_std, 3)})`));
      tr.appendChild(h("td", "num-cell", `${F.fmtUnit(r.parquet_avg, "s", 3)} (độ lệch ${F.fmt(r.parquet_std, 3)})`));
      tr.appendChild(h("td", "num-cell strong-green", `${F.fmt(r.speedup, 2)} lần`));
      ltb.appendChild(tr);
    });
    if (isStorage) window.DashboardCharts.renderStorageRatios("storage-ratio-container", d.storage_rows);

    // Tab mở rộng quy mô
    if (!isStorage) {
      const pts = d.scalability;
      const two = pts.filter((p) => /2 Workers/.test(p.resource));
      const first = two[0];
      const last = two[two.length - 1];
      $("scalability-title").textContent =
        `Thời gian không tăng theo dữ liệu: 2 Worker mất ${F.fmtUnit(first.avg_time, "s", 1)} ở ${first.ratio} và ${F.fmtUnit(last.avg_time, "s", 1)} ở ${last.ratio}`;
      window.DashboardCharts.renderScalability("scalability-chart-container", pts);
    }
    setSource("source-he-thong", d.source);
  }

  // ===========================================================================
  // Trang 3: Hành vi
  // ===========================================================================
  function setupBehaviorSwitch() {
    const btns = document.querySelectorAll("#behavior-dataset-switch .dataset-btn");
    btns.forEach((btn) => btn.addEventListener("click", () => {
      btns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.behaviorMode = btn.getAttribute("data-bds");
      state.selectedClusterIndex = 0;
      renderBehaviorPage();
    }));
  }

  function dev(val, base) {
    if (!base) return 0;
    return ((Number(val) - Number(base)) / Number(base)) * 100;
  }

  function spread(rows, overall, col) {
    const v = rows.map((r) => r[col]);
    return (Math.max(...v) - Math.min(...v)) / Math.abs(overall[col]);
  }

  const VN_FOOD_FEATURES = [
    ["calories", "Lượng calo"], ["protein", "Lượng đạm"], ["fat", "Chất béo"], ["sugar", "Lượng đường"],
    ["cooking_time_min", "Thời gian nấu"], ["is_savory", "Tỷ lệ món không chay"], ["n_ingredients", "Số nguyên liệu"]
  ];
  const VN_USER_FEATURES = [
    ["avg_rating", "Điểm trung bình"], ["avg_time_high", "Thời gian nấu của món được chấm cao"],
    ["avg_calo_high", "Calo của món được chấm cao"], ["pct_man_high", "Tỷ lệ đánh giá cao cho món không chay"],
    ["pct_chay_high", "Tỷ lệ đánh giá cao cho món chay"]
  ];
  const FC_FEATURES = [
    ["avg_rating", "Điểm trung bình"], ["avg_minutes", "Thời gian nấu (phút)"], ["avg_calories", "Lượng calo"],
    ["avg_n_ingredients", "Số nguyên liệu"], ["pct_high_rating", "Tỷ lệ điểm từ 4 sao"]
  ];

  function renderBehaviorPage() {
    const d = window.WEB_DATA_BEHAVIOR;
    if (!d) return;
    const f = d.facts;
    const mode = state.behaviorMode;
    // Màn hình cao hiện 10 món, màn hình thấp hiện 5 món để vừa khung
    const maxItems = window.innerHeight >= 950 ? 10 : 5;

    let rows, overall, features, title, itemsTitle, itemsSub, note, banner = null;
    if (mode === "food_com") {
      rows = d.fc_user_clusters.filter((r) => r.cluster >= 0);
      overall = d.fc_user_clusters.find((r) => r.cluster < 0);
      features = FC_FEATURES;
      title = `Food.com: ${F.fmt(f.fc_k)} nhóm khác nhau về điểm trung bình và thời gian nấu`;
      itemsTitle = "Món được chấm từ 4 sao nhiều nhất";
      itemsSub = "Trong tập train của cụm";
      note = `Điểm trung bình các cụm từ ${F.fmt(f.fc_avg_rating[0], 2)} đến ${F.fmt(f.fc_avg_rating[1], 2)}; thời gian nấu từ ${F.fmt(f.fc_avg_minutes[0], 1)} đến ${F.fmt(f.fc_avg_minutes[1], 1)} phút; hệ số Silhouette của k = ${F.fmt(f.fc_k)} là ${F.fmt(f.fc_silhouette, 4)}.`;
    } else if (mode === "vifoodrec_users") {
      rows = d.vn_user_clusters.filter((r) => r.cluster >= 0);
      overall = d.vn_user_clusters.find((r) => r.cluster < 0);
      features = VN_USER_FEATURES;
      title = `ViFoodRec: ${F.fmt(f.vn_k)} cụm chênh nhau ít, điểm trung bình từ ${F.fmt(f.vn_avg_rating[0], 2)} đến ${F.fmt(f.vn_avg_rating[1], 2)}`;
      itemsTitle = "Món được chấm từ 4 sao nhiều nhất";
      itemsSub = "Trong tập train của cụm";
      const diffs = Object.entries(f.vn_rel_diff).sort((a, b) => b[1] - a[1]);
      const top = diffs[0];
      const lessThan10 = diffs.filter((x) => x[1] < 0.10);
      const maxBelow = Math.max(...lessThan10.map((x) => x[1]));
      const label = (VN_USER_FEATURES.find((x) => x[0] === top[0]) || [0, top[0]])[1];
      banner = [
        `Chênh lệch lớn nhất giữa các cụm: ${F.fmtPct(top[1] * 100, 1)} ở "${label.toLowerCase()}".`,
        `${F.fmt(lessThan10.length)} trong ${F.fmt(diffs.length)} đặc trưng chênh dưới ${F.fmtPct(maxBelow * 100 + 0.05, 0)}; cụm chỉ được đánh số.`
      ];
      note = `Hệ số Silhouette của k = ${F.fmt(f.vn_k)} là ${F.fmt(f.vn_silhouette, 4)}. Chênh lệch tương đối: lớn nhất trừ nhỏ nhất, chia trung bình toàn hệ thống.`;
    } else {
      rows = d.vn_food_clusters.filter((r) => r.cluster >= 0);
      overall = d.vn_food_clusters.find((r) => r.cluster < 0);
      features = VN_FOOD_FEATURES.filter((x) => x[0] !== "is_savory" && x[0] !== "n_ingredients");
      const sp = VN_FOOD_FEATURES.map(([c, l]) => [l, spread(rows, overall, c)]).sort((a, b) => b[1] - a[1]);
      title = `ViFoodRec: ${F.fmt(f.vn_food_k)} cụm món, khác nhau nhiều nhất ở ${sp[0][0].toLowerCase()} và ${sp[1][0].toLowerCase()}`;
      itemsTitle = "Ví dụ món thuộc cụm";
      itemsSub = `${F.fmt(maxItems)} món có mã nhỏ nhất`;
      note = `Phân cụm 4.000 món theo calo, đạm, chất béo, đường, thời gian nấu, loại món và số nguyên liệu; hệ số Silhouette của k = ${F.fmt(f.vn_food_k)} là ${F.fmt(f.vn_food_silhouette, 4)}.`;
    }
    $("title-page-hanh-vi").textContent = title;
    $("rep-items-title").textContent = itemsTitle;
    $("rep-items-sub").textContent = itemsSub;
    $("behavior-note").textContent = note;
    setSource("source-hanh-vi", d.source);

    const sel = rows[state.selectedClusterIndex] || rows[0];
    const selName = clusterLabel(sel.cluster_name);
    $("behavior-chart-title").textContent = `${selName}: độ lệch so với trung bình hệ thống`;

    const feats = features.map(([col, name]) => ({ name, devPct: dev(sel[col], overall[col]) }));
    window.DashboardCharts.renderClusterDeviation("cluster-deviation-container", feats, banner);

    // Danh sách cụm
    const list = $("cluster-profiles-list");
    list.innerHTML = "";
    rows.forEach((c, idx) => {
      const item = h("div", "cluster-row" + (idx === state.selectedClusterIndex ? " selected" : ""));
      const count = c.user_count !== undefined ? c.user_count : c.food_count;
      const pct = c.user_pct !== undefined ? c.user_pct : c.food_pct;
      const unit = c.user_count !== undefined ? "người" : "món";
      const top = h("div", "cluster-row-top");
      top.appendChild(h("strong", "", clusterLabel(c.cluster_name)));
      top.appendChild(h("span", "cluster-row-count", `${F.fmt(count)} ${unit} (${F.fmtPct(pct, 1)})`));
      item.appendChild(top);
      let detail;
      if (mode === "food_com") {
        detail = `Điểm trung bình ${F.fmt(c.avg_rating, 2)}; ${F.fmt(c.n_ratings, 1)} đánh giá mỗi người; nấu ${F.fmt(c.avg_minutes, 1)} phút`;
      } else if (mode === "vifoodrec_users") {
        detail = `Điểm trung bình ${F.fmt(c.avg_rating, 2)}; ${F.fmt(c.n_ratings, 0)} đánh giá mỗi người`;
      } else {
        detail = `${F.fmt(c.calories, 0)} kcal; đường ${F.fmt(c.sugar, 1)} g; ${F.fmtPct(c.is_savory * 100, 0)} món không chay`;
      }
      item.appendChild(h("div", "cluster-row-detail", detail));
      item.addEventListener("click", () => { state.selectedClusterIndex = idx; renderBehaviorPage(); });
      list.appendChild(item);
    });

    // Món của cụm đang chọn: đúng theo bộ dữ liệu, khóa theo id cụm của chính bộ đó (sửa lỗi A1)
    const rep = $("rep-items-container");
    rep.innerHTML = "";
    const items = ((d.top_items[mode] || {})[String(sel.cluster)] || []).slice(0, maxItems);
    if (!items.length) {
      rep.appendChild(h("div", "empty-note", "Không có dữ liệu món cho cụm này."));
    }
    items.forEach((it, i) => {
      const row = h("div", "rep-row");
      const top = h("div", "rep-name");
      top.appendChild(h("strong", "", `${i + 1}. `));
      top.appendChild(document.createTextNode(it.name + " "));
      if (it.dish_type) top.appendChild(h("span", "menu-item-type " + (it.dish_type === "Món chay" ? "chay" : "man"), dishLabel(it.dish_type)));
      row.appendChild(top);
      const specs = [];
      if (it.count !== null) specs.push(`${F.fmt(it.count)} lượt chấm từ 4 sao`);
      if (it.calories) specs.push(F.fmtUnit(it.calories, "kcal", 0));
      if (it.time) specs.push(F.fmtUnit(it.time, "phút", 0));
      row.appendChild(h("div", "rep-specs", specs.join("; ")));
      rep.appendChild(row);
    });
  }

  // ===========================================================================
  // Trang 4: Gợi ý
  // ===========================================================================
  const REC_KEYS = {
    vifoodrec: { id: "food_id", name: "dish_name", time: "cooking_time_min", ds: "WEB_DATA_RECS_VN", label: "ViFoodRec" },
    food_com: { id: "recipe_id", name: "name", time: "minutes_clean", ds: "WEB_DATA_RECS_FC", label: "Food.com" }
  };

  function recData() { return window[REC_KEYS[state.recsDataset].ds]; }

  function setupRecsHandlers() {
    const dsBtns = document.querySelectorAll("#recs-dataset-switch .dataset-btn");
    dsBtns.forEach((btn) => btn.addEventListener("click", () => {
      dsBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.recsDataset = btn.getAttribute("data-rds");
      if (state.recsDataset === "food_com" && !window.WEB_DATA_RECS_FC) {
        loadScript("data/recs_foodcom.js", () => { prepareRecsControls(); renderRecsPage(); });
      } else {
        prepareRecsControls();
        renderRecsPage();
      }
    }));

    const modeBtns = document.querySelectorAll("#recs-mode-switch .seg-btn");
    modeBtns.forEach((btn) => btn.addEventListener("click", () => {
      modeBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.recsMode = btn.getAttribute("data-mode");
      renderRecsPage();
    }));

    const dtBtns = document.querySelectorAll("#filter-dish-type .seg-btn");
    dtBtns.forEach((btn) => btn.addEventListener("click", () => {
      dtBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.recsFilters.dishType = btn.getAttribute("data-dtype");
      renderRecsPage();
    }));

    $("filter-max-time").addEventListener("input", (e) => {
      const v = Number(e.target.value);
      state.recsFilters.maxTime = v >= 120 ? null : v;
      renderRecsPage();
    });
    $("filter-max-calo").addEventListener("input", (e) => {
      const v = Number(e.target.value);
      state.recsFilters.maxCalo = v >= 1000 ? null : v;
      renderRecsPage();
    });
    $("filter-top-n").addEventListener("change", (e) => { state.recsFilters.topN = Number(e.target.value); renderRecsPage(); });
    $("select-user-id").addEventListener("change", (e) => {
      state.selectedUserId[state.recsDataset] = Number(e.target.value);
      renderRecsPage();
    });

    $("btn-reset-filters").addEventListener("click", () => {
      state.recsFilters = { dishType: "all", maxTime: null, maxCalo: null, topN: 10 };
      dtBtns.forEach((b) => b.classList.toggle("active", b.getAttribute("data-dtype") === "all"));
      $("filter-max-time").value = 120;
      $("filter-max-calo").value = 1000;
      $("filter-top-n").value = "10";
      renderRecsPage();
    });

    // Tìm món không dấu cho chế độ người dùng mới
    const input = $("search-food-input");
    const dropdown = $("search-results-dropdown");
    input.addEventListener("input", (e) => {
      const q = F.removeVietnameseTones(e.target.value);
      if (q.length < 2) { dropdown.hidden = true; return; }
      const data = recData();
      const k = REC_KEYS[state.recsDataset];
      if (!data || !data.catalog) return;
      const matches = data.catalog.filter((it) => F.removeVietnameseTones(it[k.name]).includes(q)).slice(0, 8);
      dropdown.innerHTML = "";
      if (!matches.length) { dropdown.hidden = true; return; }
      matches.forEach((it) => {
        const suffix = it.dish_type ? dishLabel(it.dish_type) : (it.calories ? F.fmtUnit(it.calories, "kcal", 0) : "");
        const div = h("div", "search-item", suffix ? `${it[k.name]} (${suffix})` : it[k.name]);
        div.addEventListener("click", () => {
          addColdStart(Number(it[k.id]));
          input.value = "";
          dropdown.hidden = true;
        });
        dropdown.appendChild(div);
      });
      dropdown.hidden = false;
    });
    document.addEventListener("click", (e) => {
      if (!input.contains(e.target) && !dropdown.contains(e.target)) dropdown.hidden = true;
    });

    prepareRecsControls();
  }

  function prepareRecsControls() {
    const data = recData();
    if (!data) return;
    const ds = state.recsDataset;
    $("filter-type-box").hidden = ds !== "vifoodrec";

    const users = Array.from(new Set(data.recommendations.map((r) => r.user_id))).slice(0, 300);
    const select = $("select-user-id");
    select.innerHTML = "";
    if (state.selectedUserId[ds] === null || !users.includes(state.selectedUserId[ds])) state.selectedUserId[ds] = users[0];
    users.forEach((uid) => {
      const opt = h("option", "", `Người dùng ${uid}`);
      opt.value = uid;
      if (uid === state.selectedUserId[ds]) opt.selected = true;
      select.appendChild(opt);
    });

    // Món mẫu ban đầu cho người dùng mới của từng bộ dữ liệu
    if (!state.selectedColdStartIds[ds].length) {
      const k = REC_KEYS[ds];
      const ids = Object.keys(data.item_neighbors).map(Number).filter((id) => data.catalog.some((c) => c[k.id] === id));
      state.selectedColdStartIds[ds] = ids.slice(0, 2);
    }
    renderChips();
  }

  function addColdStart(id) {
    const arr = state.selectedColdStartIds[state.recsDataset];
    if (arr.includes(id)) return;
    if (arr.length >= 5) arr.shift();
    arr.push(id);
    renderChips();
    renderRecsPage();
  }

  function removeColdStart(id) {
    const ds = state.recsDataset;
    state.selectedColdStartIds[ds] = state.selectedColdStartIds[ds].filter((x) => x !== id);
    renderChips();
    renderRecsPage();
  }

  function renderChips() {
    const container = $("selected-chips-container");
    const data = recData();
    const ds = state.recsDataset;
    const k = REC_KEYS[ds];
    container.innerHTML = "";
    $("selected-count").textContent = state.selectedColdStartIds[ds].length;
    if (!data) return;
    state.selectedColdStartIds[ds].forEach((id) => {
      const dish = data.catalog.find((c) => c[k.id] === id);
      const chip = h("span", "food-chip");
      chip.appendChild(document.createTextNode((dish ? dish[k.name] : `Món ${id}`) + " "));
      const rm = h("button", "food-chip-remove", "Bỏ");
      rm.type = "button";
      rm.addEventListener("click", () => removeColdStart(id));
      chip.appendChild(rm);
      container.appendChild(chip);
    });
  }

  function renderRecsPage() {
    const data = recData();
    if (!data) return;
    const ds = state.recsDataset;
    const k = REC_KEYS[ds];
    const flt = state.recsFilters;

    $("title-page-goi-y").textContent =
      `${k.label}: người dùng có sẵn dùng ALS dự đoán điểm, người dùng mới dùng món tương đồng`;
    $("mode-existing-box").hidden = state.recsMode !== "existing";
    $("mode-new-box").hidden = state.recsMode !== "new";
    $("label-max-time").textContent = flt.maxTime === null ? "Không giới hạn" : F.fmtUnit(flt.maxTime, "phút", 0);
    $("label-max-calo").textContent = flt.maxCalo === null ? "Không giới hạn" : F.fmtUnit(flt.maxCalo, "kcal", 0);
    setSource("source-goi-y", ds === "vifoodrec"
      ? "recommendations_vietnam.parquet, item_neighbors_vietnam.parquet, user_clusters_vietnam.parquet"
      : "recommendations_foodcom_sample.parquet, item_neighbors_foodcom.parquet, user_clusters_foodcom.parquet");

    const uid = state.selectedUserId[ds];
    const badge = $("user-cluster-badge");
    const uInfo = (data.user_clusters || {})[uid];
    badge.textContent = state.recsMode === "existing" && uInfo ? `Cụm hành vi: ${clusterLabel(uInfo.cluster_name)}` : "";

    let items = [];
    if (state.recsMode === "existing") {
      $("recs-result-title").textContent = `Món gợi ý cho người dùng ${uid}`;
      items = data.recommendations.filter((r) => r.user_id === uid).sort((a, b) => a.rank - b.rank).map((r) => {
        const cat = data.catalog.find((c) => c[k.id] === r[k.id]) || {};
        return {
          name: r[k.name] || cat[k.name],
          dish_type: r.dish_type || cat.dish_type,
          calories: r.calories !== undefined ? r.calories : cat.calories,
          time: cat[k.time] || r.cooking_time || r.minutes_clean,
          ingredients: cat.ingredients || "",
          reason: null,
          key: `u${r[k.id]}`
        };
      });
    } else {
      $("recs-result-title").textContent = "Món gợi ý theo độ tương đồng với các món đã chọn";
      const chosen = state.selectedColdStartIds[ds];
      const sel = new Set(chosen);
      const cand = {};
      chosen.forEach((src) => {
        const sd = data.catalog.find((c) => c[k.id] === src);
        const srcName = sd ? sd[k.name] : `Món ${src}`;
        (data.item_neighbors[src] || []).forEach(([nid, score]) => {
          if (sel.has(nid)) return;
          if (!cand[nid]) cand[nid] = { total: score, topMatch: srcName, topScore: score, count: 1 };
          else {
            cand[nid].total += score;
            cand[nid].count += 1;
            if (score > cand[nid].topScore) { cand[nid].topScore = score; cand[nid].topMatch = srcName; }
          }
        });
      });
      items = Object.entries(cand).sort((a, b) => b[1].total - a[1].total).map(([nidStr, info]) => {
        const nid = Number(nidStr);
        const cat = data.catalog.find((c) => c[k.id] === nid) || {};
        const pct = F.fmtPct(info.topScore * 100, 2);
        return {
          name: cat[k.name] || `Món ${nid}`,
          dish_type: cat.dish_type,
          calories: cat.calories,
          time: cat[k.time],
          ingredients: cat.ingredients || "",
          reason: info.count === 1 ? `Giống ${pct} với "${info.topMatch}"`
            : `Giống ${pct} với "${info.topMatch}" và ${F.fmt(info.count - 1)} món khác bạn chọn`,
          key: `n${nid}`
        };
      });
    }

    if (flt.dishType !== "all" && ds === "vifoodrec") items = items.filter((i) => i.dish_type === flt.dishType);
    if (flt.maxTime !== null) items = items.filter((i) => !i.time || Number(i.time) <= flt.maxTime);
    if (flt.maxCalo !== null) items = items.filter((i) => !i.calories || Number(i.calories) <= flt.maxCalo);

    const total = items.length;
    const shown = items.slice(0, flt.topN);
    const nb = data.neighbor_stats;
    const flatSims = nb && nb.min >= 0.999;
    $("recs-result-count").textContent = `Hiển thị ${F.fmt(shown.length)} món`;

    const warn = $("filter-warning-banner");
    const filtered = flt.dishType !== "all" || flt.maxTime !== null || flt.maxCalo !== null;
    if (state.recsMode === "new" && flatSims) {
      warn.hidden = false;
      warn.textContent = `Lưu ý dữ liệu: ${F.fmtPct(nb.share_ge_0_999 * 100, 0)} điểm tương đồng của ${k.label} lớn hơn hoặc bằng 0,999 (nhỏ nhất ${F.fmt(nb.min, 4)}), nên thứ tự gợi ý ở chế độ này chưa phản ánh khác biệt giữa các món.`;
    } else if (total < flt.topN) {
      warn.hidden = false;
      warn.textContent = filtered
        ? `Chỉ có ${F.fmt(total)} món phù hợp bộ lọc. Tăng thời gian nấu hoặc lượng calo tối đa để thấy thêm món.`
        : `Chỉ có ${F.fmt(total)} món để hiển thị cho lựa chọn này.`;
    } else {
      warn.hidden = true;
    }

    const list = $("recs-menu-list");
    list.innerHTML = "";
    if (!shown.length) {
      list.appendChild(h("div", "empty-note", 'Không có món nào thỏa bộ lọc hiện tại. Bấm "Xóa bộ lọc" để bắt đầu lại.'));
      return;
    }
    shown.forEach((it, idx) => {
      const row = h("div", "menu-item");
      const main = h("div", "menu-item-main");
      const left = h("div", "menu-item-left");
      left.appendChild(h("span", "menu-item-rank", `${idx + 1}`));
      left.appendChild(h("span", "menu-item-name", it.name));
      main.appendChild(left);
      const specs = h("div", "menu-item-specs");
      if (it.dish_type) specs.appendChild(h("span", "menu-item-type " + (it.dish_type === "Món chay" ? "chay" : "man"), dishLabel(it.dish_type)));
      if (it.calories) specs.appendChild(h("span", "", F.fmtUnit(it.calories, "kcal", 0)));
      if (it.time) specs.appendChild(h("span", "", F.fmtUnit(it.time, "phút", 0)));
      main.appendChild(specs);
      row.appendChild(main);
      if (it.ingredients) {
        const sub = h("div", "menu-item-sub" + (state.expandedIngredients.has(it.key) ? " expanded" : ""), `Nguyên liệu: ${it.ingredients}`);
        sub.title = "Bấm để xem đủ hoặc thu gọn";
        sub.addEventListener("click", () => {
          if (state.expandedIngredients.has(it.key)) state.expandedIngredients.delete(it.key);
          else state.expandedIngredients.add(it.key);
          sub.classList.toggle("expanded");
        });
        row.appendChild(sub);
      }
      if (it.reason) row.appendChild(h("div", "menu-item-reason", it.reason));
      list.appendChild(row);
    });
  }

  // ===========================================================================
  // Trang 5: Mô hình
  // ===========================================================================
  function setupModelSwitch() {
    const btns = document.querySelectorAll("#model-dataset-switch .dataset-btn");
    btns.forEach((btn) => btn.addEventListener("click", () => {
      btns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.modelDataset = btn.getAttribute("data-mds");
      renderModelsPage();
    }));
  }

  const METRIC_NAMES = { RMSE: "RMSE", MAE: "MAE", "Precision@10": "P@10", "Recall@10": "R@10" };

  function modelTitle(facts, dsLabel) {
    const metrics = Object.keys(METRIC_NAMES);
    const alsBest = metrics.filter((m) => facts[m].model.startsWith("ALS"));
    if (!alsBest.length) {
      return `${dsLabel}: ALS không đứng đầu ở độ đo nào; RMSE thấp nhất là ${facts.RMSE.label} (${F.fmtMetric("RMSE", facts.RMSE.value)})`;
    }
    const first = facts[alsBest[0]];
    const rest = metrics.filter((m) => !alsBest.includes(m)).map((m) => METRIC_NAMES[m]);
    const restTxt = rest.length > 1 ? rest.slice(0, -1).join(", ") + " và " + rest[rest.length - 1] : rest[0];
    return `${dsLabel}: ${first.label} đứng đầu ${alsBest.map((m) => METRIC_NAMES[m]).join(" và ")} (${F.fmtMetric(alsBest[0], first.value)}); ${restTxt} thuộc mô hình cơ sở`;
  }

  function renderModelsPage() {
    const d = window.WEB_DATA_MODELS;
    if (!d) return;
    const ds = state.modelDataset;
    const isVn = ds === "food_vietnam";
    const dsLabel = (LB.datasets || {})[ds] || ds;
    const sub = d.model_comparison.filter((r) => r.dataset === ds);

    $("title-page-mo-hinh").textContent = modelTitle(d.facts[ds], dsLabel);
    setSource("source-mo-hinh", d.source);

    // Giá trị tốt nhất mỗi cột: so khớp đúng giá trị nguồn, không dùng dung sai
    const best = {};
    Object.keys(METRIC_NAMES).forEach((m) => { best[m] = d.facts[ds][m].value; });
    const tbody = $("model-comparison-tbody");
    tbody.innerHTML = "";
    sub.forEach((r) => {
      const tr = h("tr");
      tr.appendChild(h("td", "", r.model_label));
      Object.keys(METRIC_NAMES).forEach((m) => {
        const v = r[m];
        const missing = v === null || v === undefined;
        const td = h("td", missing ? "num-cell na-cell" : "num-cell", missing ? F.EMPTY : F.fmtMetric(m, v));
        // Giá trị tốt nhất: so khớp đúng giá trị nguồn; không tô khi giá trị tốt nhất bằng 0
        if (!missing && v === best[m] && best[m] > 0) td.classList.add("best-cell");
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

    // Bảng tinh chỉnh ALS dự đoán điểm
    const tuneRows = (isVn ? d.als_tuning_vn : d.als_tuning_fc).slice();
    const ranked = tuneRows.map((t, i) => ({ t, i }))
      .sort((a, b) => a.t.val_rmse - b.t.val_rmse || a.i - b.i)
      .slice(0, window.innerHeight >= 950 ? 10 : 5);
    const minVal = ranked[0].t.val_rmse;
    const ties = tuneRows.filter((x) => x.val_rmse === minVal).length;
    $("tuning-tie-note").textContent = ties > 1
      ? `${F.fmt(ties)} cấu hình cùng có RMSE validation ${F.fmtMetric("RMSE", minVal)}; cấu hình được chọn là cấu hình đầu tiên trong lưới.`
      : "";
    const tb = $("als-tuning-tbody");
    tb.innerHTML = "";
    ranked.forEach(({ t }, idx) => {
      const rank = 1 + tuneRows.filter((x) => x.val_rmse < t.val_rmse).length;
      const tr = h("tr", idx === 0 ? "row-selected" : "");
      tr.appendChild(h("td", "", idx === 0 ? `${rank} (được chọn)` : `${rank}`));
      tr.appendChild(h("td", "num-cell", F.fmt(t.rank, 0)));
      tr.appendChild(h("td", "num-cell", F.fmt(t.regParam, 2)));
      tr.appendChild(h("td", "num-cell", F.fmt(t.maxIter, 0)));
      tr.appendChild(h("td", "num-cell", F.fmtMetric("RMSE", t.val_rmse)));
      tr.appendChild(h("td", "num-cell", F.fmtUnit(t.train_time_sec, "s", 2)));
      tb.appendChild(tr);
    });

    // Biểu đồ phân rã RMSE theo điểm thật
    const alsBd = d.als_rmse_breakdown.filter((r) => r.dataset === ds);
    const baseBd = d.baseline_rmse_breakdown.filter((r) => r.dataset === ds && r.model === "Global Mean");
    const levels = Array.from(new Set(alsBd.map((r) => Number(r.rating_level)))).sort((a, b) => a - b);
    const val = (arr, lvl) => { const r = arr.find((x) => Number(x.rating_level) === lvl); return r ? Number(r.rmse) : null; };
    const baseLabel = (LB.models || {})["Global Mean"] || "Global Mean";
    const alsLabel = (LB.models || {})["ALS Matrix Factorization"] || "ALS";
    $("rmse-breakdown-sub").textContent = `${baseLabel} và ${alsLabel}`;
    window.DashboardCharts.renderRmseBreakdown("rmse-breakdown-chart-container", [
      { name: baseLabel, values: levels.map((l) => val(baseBd, l)) },
      { name: alsLabel, values: levels.map((l) => val(alsBd, l)) }
    ], levels, { yTitle: "RMSE", xTitle: "Điểm thật (sao)", levelDecimals: isVn ? 1 : 0 });
  }

  // ===========================================================================
  // Chú giải, hộp chọn số cụm, phím tắt
  // ===========================================================================
  const GLOSSARY = [
    ["ALS", "Mô hình phân rã ma trận: học vector ẩn của người dùng và của món từ các lượt đánh giá."],
    ["ALS dự đoán điểm", "ALS học từ điểm đánh giá để dự đoán điểm người dùng sẽ chấm cho một món."],
    ["ALS ngầm định", "ALS coi điểm từ 4 trở lên là tín hiệu thích và học cách xếp hạng món; không dự đoán điểm nên không có RMSE và MAE."],
    ["RMSE", "Căn bậc hai của trung bình bình phương sai số giữa điểm dự đoán và điểm thật; càng thấp càng tốt."],
    ["MAE", "Trung bình trị tuyệt đối sai số giữa điểm dự đoán và điểm thật; càng thấp càng tốt."],
    ["P@10", "Precision@10: tỷ lệ món phù hợp (điểm từ 4 trở lên) trong 10 món gợi ý; càng cao càng tốt."],
    ["R@10", "Recall@10: tỷ lệ món phù hợp của người dùng được tìm thấy trong 10 món gợi ý; càng cao càng tốt."],
    ["Mô hình cơ sở", "Cách dự đoán đơn giản để so sánh: trung bình toàn cục, trung bình món làm trơn, top món phổ biến."],
    ["K-core", "Lọc lặp đến khi mọi người dùng và món còn lại có ít nhất K đánh giá (ở đây K = 3)."],
    ["K-means", "Thuật toán chia người dùng hoặc món thành k cụm có đặc trưng gần nhau."],
    ["Silhouette", "Độ tách giữa các cụm, từ -1 đến 1; càng cao càng tách rõ."],
    ["WSSSE", "Tổng bình phương khoảng cách từ mỗi điểm đến tâm cụm của nó; càng thấp cụm càng gọn."],
    ["Độ thưa", "Phần trăm ô (người dùng, món) chưa có đánh giá trong ma trận."],
    ["Không chay", "Món không được gắn nhãn chay trong dữ liệu gốc; gồm cả món ngọt và bánh, không có nghĩa là vị mặn."],
    ["Người dùng mới", "Người chưa có đánh giá: web gợi ý các món có vector ẩn gần với những món người đó chọn."],
    ["Parquet", "Định dạng tệp lưu theo cột, nén tốt hơn CSV và đọc nhanh hơn khi chỉ cần vài cột."],
    ["HDFS", "Hệ thống tệp phân tán; replication là số bản sao của mỗi khối dữ liệu."],
    ["Spark", "Bộ máy xử lý dữ liệu phân tán, chạy công việc trên nhiều Worker."]
  ];

  function setupGlossary() {
    const list = $("glossary-list");
    GLOSSARY.forEach(([name, desc]) => {
      const item = h("div", "glossary-term");
      item.appendChild(h("div", "glossary-term-name", name));
      item.appendChild(h("div", "glossary-term-desc", desc));
      list.appendChild(item);
    });
    $("btn-open-glossary").addEventListener("click", openGlossary);
    $("btn-close-glossary").addEventListener("click", closeGlossary);
    $("drawer-backdrop").addEventListener("click", () => { closeGlossary(); closeTuningModal(); });
  }

  function openGlossary() {
    $("drawer-backdrop").classList.add("open");
    $("glossary-drawer").classList.add("open");
  }
  function closeGlossary() {
    $("glossary-drawer").classList.remove("open");
    if (!$("tuning-modal").classList.contains("open")) $("drawer-backdrop").classList.remove("open");
  }

  function setupTuningModal() {
    $("btn-open-tuning-modal").addEventListener("click", openTuningModal);
    $("btn-close-tuning-modal").addEventListener("click", closeTuningModal);
  }
  function openTuningModal() {
    $("drawer-backdrop").classList.add("open");
    $("tuning-modal").classList.add("open");
    const tbody = $("kmeans-tuning-tbody");
    tbody.innerHTML = "";
    (window.WEB_DATA_BEHAVIOR.kmeans_tuning || []).forEach((r) => {
      const tr = h("tr");
      tr.appendChild(h("td", "", r.task));
      tr.appendChild(h("td", "num-cell", F.fmt(r.k, 0)));
      tr.appendChild(h("td", "num-cell", F.fmt(r.silhouette, 4)));
      tr.appendChild(h("td", "num-cell", F.fmt(r.wssse, 1)));
      tr.appendChild(h("td", "num-cell", F.fmtUnit(r.time_sec, "s", 2)));
      tbody.appendChild(tr);
    });
  }
  function closeTuningModal() {
    $("tuning-modal").classList.remove("open");
    if (!$("glossary-drawer").classList.contains("open")) $("drawer-backdrop").classList.remove("open");
  }

  function setupKeyboard() {
    window.addEventListener("keydown", (e) => {
      const tag = document.activeElement && document.activeElement.tagName;
      if (["INPUT", "SELECT", "TEXTAREA"].includes(tag)) {
        if (e.key === "Escape") document.activeElement.blur();
        return;
      }
      if (e.key === "Escape") { closeGlossary(); closeTuningModal(); return; }
      const route = ROUTES.find((r) => r.key === e.key);
      if (route) navigate(route.hash);
    });
  }

  function loadScript(url, cb) {
    const s = document.createElement("script");
    s.src = url;
    s.onload = cb;
    document.body.appendChild(s);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();

  window.DashboardApp = { state, navigate, renderPage, openGlossary, closeGlossary };
})();
