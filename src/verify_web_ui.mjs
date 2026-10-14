// src/verify_web_ui.mjs
// Kiểm thử giao diện web (S4, mục E2, E3 phần văn bản hiển thị, E5, E6) bằng Chrome headless điều khiển qua CDP.
// Không cần cài gói ngoài: dùng WebSocket có sẵn của Node 24 và Chrome/Edge có sẵn trên máy.
//
// Việc làm:
//  1. Với 1920x1080 và 1366x768, duyệt 5 trang và mọi trạng thái chính (hai bộ dữ liệu, hai chế độ gợi ý, các tab):
//     không cuộn trang, tiêu đề một dòng, chân trang nằm trong khung nhìn.
//  2. Quét văn bản hiển thị: không có số thập phân dấu chấm, không có ngoặc tiếng Anh, không có ký tự biểu tượng.
//  3. Luồng demo: người dùng ViFoodRec xem 10 món; người dùng mới với 3 bộ món khác nhau; từng bộ lọc; tìm không dấu.
//  4. Chụp ảnh từng trạng thái vào reports/figures/screenshots/web_v2/.
// Thoát mã khác 0 nếu có mục không đạt. Kết quả chi tiết ghi vào reports/evidence/logs/S4_ui_results.json.

import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import os from "node:os";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const INDEX_URL = pathToFileURL(path.join(ROOT, "web", "index.html")).href;
const SHOT_DIR = path.join(ROOT, "reports", "figures", "screenshots", "web_v2");
const RESULT_JSON = path.join(ROOT, "reports", "evidence", "logs", "S4_ui_results.json");
const PORT = 9333;
const SIZES = [[1920, 1080], [1366, 768]];

const CHROME_PATHS = [
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe"
];

// Từ tiếng Anh không được xuất hiện trong ngoặc (B1). Tên kỹ thuật trong Chú giải (ALS, RMSE, MAE, K-core, Parquet,
// HDFS, Spark, Worker, WSL2) được phép nên không nằm trong danh sách này.
const EN_WORDS = /\b(?:the|and|of|for|with|data|mean|rating|ratings|users?|items?|cleaning|funnel|critical|reviewers?|cold|start|matrix|factorization|zero|dependency|test|train|validation|baseline|overall|popular|quick|easy|power|general|enthusiasts|diners?|selective|convenient|active|gourmet|snacks|sweets|savory|stews|vegetarian|specialties|rich|dishes|low|calorie|sugar|cores?|workers)\b/i;
const SYMBOL_BLACKLIST = /[\u2022\u2713\u2714\u2192\u2190\u2191\u2193\u2264\u2265\u00D7\u2014\u2013\u00B1\u2605\u2606\u2B50\u25CF\u25A0\u25B2\u25BC]|[\u{1F300}-\u{1FAFF}]|[\u2600-\u27BF]/u;

const results = [];
const texts = {}; // văn bản hiển thị của từng trạng thái, dùng cho src/verify_web.py
const TEXTS_JSON = path.join(ROOT, "reports", "evidence", "logs", "S4_ui_texts.json");
function record(name, ok, detail = "") {
  results.push({ name, ok, detail });
  console.log(`${ok ? "[DAT]" : "[KHONG DAT]"} ${name}${detail ? " : " + detail : ""}`);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function findChrome() {
  for (const p of CHROME_PATHS) if (fs.existsSync(p)) return p;
  throw new Error("Không tìm thấy Chrome hoặc Edge");
}

async function launch() {
  const userDir = fs.mkdtempSync(path.join(os.tmpdir(), "s4chrome-"));
  const proc = spawn(findChrome(), [
    "--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${userDir}`,
    "--disable-gpu", "--force-device-scale-factor=1", "--allow-file-access-from-files",
    "--no-first-run", "--hide-scrollbars", "about:blank"
  ], { stdio: "ignore" });
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json`);
      const pages = (await r.json()).filter((p) => p.type === "page");
      if (pages.length) return { proc, wsUrl: pages[0].webSocketDebuggerUrl };
    } catch (e) { /* chờ Chrome sẵn sàng */ }
    await sleep(250);
  }
  throw new Error("Chrome không khởi động được");
}

class Cdp {
  constructor(wsUrl) { this.ws = new WebSocket(wsUrl); this.id = 0; this.pending = new Map(); }
  async open() {
    await new Promise((res, rej) => { this.ws.onopen = res; this.ws.onerror = rej; });
    this.ws.onmessage = (m) => {
      const msg = JSON.parse(m.data);
      if (msg.id && this.pending.has(msg.id)) { this.pending.get(msg.id)(msg); this.pending.delete(msg.id); }
    };
  }
  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((res) => { this.pending.set(id, res); this.ws.send(JSON.stringify({ id, method, params })); });
  }
  async ev(expression) {
    const r = await this.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (r.result.exceptionDetails) throw new Error("JS lỗi: " + JSON.stringify(r.result.exceptionDetails.exception?.description || r.result.exceptionDetails));
    return r.result.result.value;
  }
  async shot(file) {
    const r = await this.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(file, Buffer.from(r.result.data, "base64"));
  }
  async resize(w, h) {
    await this.send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: false });
  }
  close() { this.ws.close(); }
}

// ---------------------------------------------------------------------------
// Các hàm đo chạy trong trang
// ---------------------------------------------------------------------------
const MEASURE = `(() => {
  const view = document.querySelector('.page-view.active');
  const title = view.querySelector('.page-finding-title');
  const footer = view.querySelector('.page-footer-bar');
  const main = document.querySelector('.main-viewport');
  const de = document.documentElement;
  const r = footer.getBoundingClientRect();
  // Phần trống cuối mỗi panel (không tính panel có cuộn trong)
  const panels = [...view.querySelectorAll('.panel-block')].map((p) => {
    const body = [...p.querySelectorAll('.panel-body')].find((b) => !b.hidden) || p.querySelector('.panel-body');
    const kids = body ? [...body.children] : [];
    const pr = p.getBoundingClientRect();
    const bottoms = kids.filter((k) => !k.hidden && k.offsetParent !== null).map((k) => k.getBoundingClientRect().bottom);
    const used = bottoms.length ? Math.max(...bottoms) - pr.top : 0;
    return { title: (p.querySelector('.panel-title') || {}).textContent || '', height: Math.round(pr.height),
      emptyFraction: +(Math.max(0, (pr.height - used) / pr.height)).toFixed(3),
      scrolls: body ? body.scrollHeight > body.clientHeight + 1 : false };
  });
  // Thống kê cỡ chữ (số ký tự theo cỡ chữ px) để đánh giá khả năng đọc khi thu nhỏ ảnh chia sẻ
  const fonts = {};
  const walker = document.createTreeWalker(view, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    const t = node.nodeValue.trim();
    const el2 = node.parentElement;
    if (!t || !el2 || el2.closest('[hidden]')) continue;
    const px = Math.round(parseFloat(getComputedStyle(el2).fontSize) * 10) / 10;
    fonts[px] = (fonts[px] || 0) + t.length;
  }
  return {
    fonts,
    scrollHeight: de.scrollHeight, bodyScrollHeight: document.body.scrollHeight, innerHeight: window.innerHeight,
    mainOverflow: main.scrollHeight - main.clientHeight,
    titleOneLine: title.scrollWidth <= title.clientWidth + 1, titleText: title.textContent, titleLen: title.textContent.length,
    footerInView: r.bottom <= window.innerHeight + 0.5, footerBottom: Math.round(r.bottom),
    panels,
    text: view.innerText
  };
})()`;

function scanText(label, text) {
  const problems = [];
  // Số thập phân dùng dấu chấm: loại trừ phiên bản a.b.c và nhóm nghìn đúng 3 chữ số
  const cleaned = text.replace(/\b\d+\.\d+\.\d+\b/g, "").replace(/\b\d{1,3}(?:\.\d{3})+\b/g, "");
  const dec = cleaned.match(/\d\.\d/g);
  if (dec) problems.push(`số thập phân dấu chấm (${dec.length}): ${[...new Set(dec)].slice(0, 5).join(" ")}`);
  const parens = text.match(/\([^()\n]*\)/g) || [];
  parens.filter((p) => EN_WORDS.test(p)).forEach((p) => problems.push(`ngoặc có từ tiếng Anh: ${p}`));
  const sym = text.match(SYMBOL_BLACKLIST);
  if (sym) problems.push(`ký tự biểu tượng: ${sym[0]}`);
  return problems;
}

// ---------------------------------------------------------------------------
// Trạng thái cần kiểm tra
// ---------------------------------------------------------------------------
const CLICK = (sel) => `document.querySelector(${JSON.stringify(sel)}).click()`;
const SET = (sel, v, evt = "input") => `(() => { const e = document.querySelector(${JSON.stringify(sel)}); e.value = ${JSON.stringify(v)}; e.dispatchEvent(new Event(${JSON.stringify(evt)}, { bubbles: true })); })()`;

const STATES = [
  { id: "du-lieu", hash: "#/du-lieu", steps: [] },
  { id: "he-thong-luu-tru", hash: "#/he-thong", steps: [CLICK("#tab-btn-storage")] },
  { id: "he-thong-mo-rong", hash: "#/he-thong", steps: [CLICK("#tab-btn-scalability")] },
  { id: "hanh-vi-food-com", hash: "#/hanh-vi", steps: [CLICK('[data-bds="food_com"]')] },
  { id: "hanh-vi-vifoodrec-nguoi-dung", hash: "#/hanh-vi", steps: [CLICK('[data-bds="vifoodrec_users"]')] },
  { id: "hanh-vi-vifoodrec-mon", hash: "#/hanh-vi", steps: [CLICK('[data-bds="vifoodrec_foods"]')] },
  { id: "goi-y-vifoodrec-co-san", hash: "#/goi-y", steps: [CLICK('[data-rds="vifoodrec"]'), CLICK('[data-mode="existing"]')] },
  { id: "goi-y-vifoodrec-moi", hash: "#/goi-y", steps: [CLICK('[data-rds="vifoodrec"]'), CLICK('[data-mode="new"]')] },
  { id: "goi-y-food-com-co-san", hash: "#/goi-y", steps: [CLICK('[data-rds="food_com"]'), CLICK('[data-mode="existing"]')], wait: 1200 },
  { id: "goi-y-food-com-moi", hash: "#/goi-y", steps: [CLICK('[data-rds="food_com"]'), CLICK('[data-mode="new"]')], wait: 600 },
  { id: "mo-hinh-vifoodrec", hash: "#/mo-hinh", steps: [CLICK('[data-mds="food_vietnam"]')] },
  { id: "mo-hinh-food-com", hash: "#/mo-hinh", steps: [CLICK('[data-mds="food_com"]')] },
  { id: "glossary", hash: "#/du-lieu", steps: [CLICK("#btn-open-glossary")], noScan: false },
  { id: "tuning-modal", hash: "#/hanh-vi", steps: [CLICK('[data-bds="food_com"]'), CLICK("#btn-open-tuning-modal")] }
];

async function gotoState(cdp, st) {
  await cdp.ev(`window.location.hash = ${JSON.stringify(st.hash)}`);
  await sleep(200);
  for (const step of st.steps) { await cdp.ev(step); await sleep(st.wait ? st.wait / st.steps.length : 250); }
  await sleep(350);
}

async function runLayoutChecks(cdp) {
  const perState = [];
  for (const [w, h] of SIZES) {
    await cdp.resize(w, h);
    await cdp.send("Page.navigate", { url: INDEX_URL });
    await sleep(900);
    for (const st of STATES) {
      await gotoState(cdp, st);
      const m = await cdp.ev(MEASURE);
      const tag = `${w}x${h} ${st.id}`;
      record(`Không cuộn trang: ${tag}`, m.scrollHeight <= m.innerHeight && m.bodyScrollHeight <= m.innerHeight && m.mainOverflow <= 1,
        `scrollHeight ${m.scrollHeight} / innerHeight ${m.innerHeight}, mainOverflow ${m.mainOverflow}`);
      if (!["glossary", "tuning-modal"].includes(st.id)) {
        record(`Tiêu đề một dòng và không quá 90 ký tự: ${tag}`, m.titleOneLine && m.titleLen <= 90, `${m.titleLen} ký tự: ${m.titleText}`);
        record(`Chân trang nằm trong khung nhìn: ${tag}`, m.footerInView, `đáy ${m.footerBottom}`);
      }
      if (st.id.startsWith("he-thong")) {
        // D2: không quá 25% diện tích mỗi panel của trang Hệ thống bị bỏ trống
        const worst = Math.max(...m.panels.map((q) => q.emptyFraction));
        record(`Trang Hệ thống: mỗi panel trống không quá 25%: ${tag}`, worst <= 0.25, `lớn nhất ${(worst * 100).toFixed(1)}%`);
      }
      if (st.id.startsWith("goi-y") && w === 1920) {
        // D4: danh sách món vừa khung ở 1920x1080, không cuộn trong
        const resultPanel = m.panels[m.panels.length - 1];
        record(`Trang Gợi ý: danh sách 10 món không cuộn trong ở 1920x1080: ${tag}`, !resultPanel.scrolls, `panel cao ${resultPanel.height}px`);
      }
      if (st.id.startsWith("hanh-vi") && w === 1920) {
        const itemsPanel = m.panels[m.panels.length - 1];
        record(`Trang Hành vi: danh sách món của cụm không cuộn trong ở 1920x1080: ${tag}`, !itemsPanel.scrolls, `panel cao ${itemsPanel.height}px`);
      }
      const problems = scanText(tag, m.text);
      record(`Văn bản hiển thị sạch: ${tag}`, problems.length === 0, problems.join("; "));
      perState.push({ tag, panels: m.panels, fonts: m.fonts });
      texts[tag] = m.text;
      fs.mkdirSync(SHOT_DIR, { recursive: true });
      await cdp.shot(path.join(SHOT_DIR, `${w}x${h}_${st.id}.png`));
    }
  }
  return perState;
}

// ---------------------------------------------------------------------------
// Luồng demo (E6) ở 1920x1080
// ---------------------------------------------------------------------------
const LIST_ITEMS = `[...document.querySelectorAll('#recs-menu-list .menu-item')].map((e) => ({
  name: e.querySelector('.menu-item-name').textContent,
  type: (e.querySelector('.menu-item-type') || {}).textContent || '',
  specs: [...e.querySelectorAll('.menu-item-specs span')].map((s) => s.textContent),
  reason: (e.querySelector('.menu-item-reason') || {}).textContent || ''
}))`;

async function pickFood(cdp, query) {
  await cdp.ev(SET("#search-food-input", query));
  await sleep(250);
  const first = await cdp.ev(`(() => { const d = document.querySelector('#search-results-dropdown'); const it = d.querySelector('.search-item'); return it ? it.textContent : null; })()`);
  if (first) { await cdp.ev(`document.querySelector('#search-results-dropdown .search-item').click()`); await sleep(250); }
  return first;
}

async function runDemoFlows(cdp) {
  await cdp.resize(1920, 1080);
  await cdp.send("Page.navigate", { url: INDEX_URL });
  await sleep(900);
  await cdp.ev(`window.location.hash = '#/goi-y'`);
  await sleep(500);

  // a) Người dùng ViFoodRec xem 10 món
  await cdp.ev(CLICK('[data-rds="vifoodrec"]'));
  await cdp.ev(CLICK('[data-mode="existing"]'));
  await cdp.ev(SET("#select-user-id", "70", "change"));
  await sleep(300);
  let items = await cdp.ev(LIST_ITEMS);
  record("Demo: người dùng ViFoodRec 70 xem 10 món", items.length === 10 && new Set(items.map((i) => i.name)).size === 10,
    items.map((i) => i.name).join(" | "));
  const badge = await cdp.ev(`document.querySelector('#user-cluster-badge').textContent`);
  record("Demo: huy hiệu cụm dùng nhãn Cụm n (A2)", /^Cụm hành vi: Cụm [123]$/.test(badge), badge);

  // b) Người dùng mới với 3 bộ món khác nhau
  await cdp.ev(CLICK('[data-mode="new"]'));
  await sleep(200);
  const sets = [["bun bo", "canh chua", "pho"], ["banh xeo", "che", "goi cuon"], ["com tam", "lau", "bo kho"]];
  const tops = [];
  for (const s of sets) {
    await cdp.ev(`document.querySelectorAll('.food-chip-remove').forEach((b) => b.click())`);
    await sleep(150);
    const picked = [];
    for (const q of s) picked.push(await pickFood(cdp, q));
    const lst = await cdp.ev(LIST_ITEMS);
    tops.push(lst.slice(0, 5).map((i) => i.name).join("|"));
    record(`Demo: người dùng mới chọn ${s.join(", ")} cho ra danh sách`, lst.length > 0 && picked.every(Boolean) && lst.every((i) => i.reason.startsWith("Giống")),
      `đã chọn: ${picked.join(" / ")}; ${lst.length} món; đầu danh sách: ${lst.slice(0, 3).map((i) => i.name).join(" | ")}`);
  }
  record("Demo: 3 bộ món cho 3 danh sách khác nhau", new Set(tops).size === 3, `${new Set(tops).size} danh sách khác nhau`);

  // c) Tìm không dấu
  await cdp.ev(SET("#search-food-input", "bun bo"));
  await sleep(300);
  const dd = await cdp.ev(`[...document.querySelectorAll('#search-results-dropdown .search-item')].map((e) => e.textContent)`);
  record('Demo: tìm không dấu "bun bo" ra "Bún bò"', dd.some((t) => /^bún bò/i.test(t)), dd.slice(0, 4).join(" | "));
  await cdp.ev(SET("#search-food-input", ""));

  // d) Từng bộ lọc (chế độ người dùng có sẵn, 10 món của người dùng 70, rồi chế độ mới để đủ món)
  await cdp.ev(CLICK('[data-mode="new"]'));
  await cdp.ev(`document.querySelectorAll('.food-chip-remove').forEach((b) => b.click())`);
  for (const q of ["bun bo", "canh chua", "pho"]) await pickFood(cdp, q);
  items = await cdp.ev(LIST_ITEMS);
  const base = items.length;

  await cdp.ev(CLICK('[data-dtype="Món chay"]'));
  await sleep(250);
  items = await cdp.ev(LIST_ITEMS);
  record('Bộ lọc loại món "Chay": mọi món là Chay', items.length > 0 && items.every((i) => i.type === "Chay"), `${items.length} món`);
  await cdp.ev(CLICK('[data-dtype="Món mặn"]'));
  await sleep(250);
  items = await cdp.ev(LIST_ITEMS);
  record('Bộ lọc loại món "Không chay": mọi món là Không chay', items.length > 0 && items.every((i) => i.type === "Không chay"), `${items.length} món`);
  await cdp.ev(CLICK('[data-dtype="all"]'));

  await cdp.ev(SET("#filter-max-time", "30"));
  await sleep(250);
  items = await cdp.ev(LIST_ITEMS);
  const times = items.map((i) => Number((i.specs.find((s) => /phút/.test(s)) || "").replace(/\D/g, "")));
  record("Bộ lọc thời gian nấu tối đa 30 phút", items.length > 0 && times.every((t) => t <= 30), `${items.length} món, thời gian lớn nhất ${Math.max(...times)}`);
  await cdp.ev(SET("#filter-max-time", "120"));

  await cdp.ev(SET("#filter-max-calo", "400"));
  await sleep(250);
  items = await cdp.ev(LIST_ITEMS);
  const calos = items.map((i) => Number((i.specs.find((s) => /kcal/.test(s)) || "").replace(/\D/g, "")));
  record("Bộ lọc calo tối đa 400", items.length > 0 && calos.every((c) => c <= 400), `${items.length} món, calo lớn nhất ${Math.max(...calos)}`);
  await cdp.ev(SET("#filter-max-calo", "1000"));

  await cdp.ev(SET("#filter-top-n", "5", "change"));
  await sleep(250);
  items = await cdp.ev(LIST_ITEMS);
  record("Bộ lọc số món hiển thị: 5 món", items.length === 5, `${items.length} món (trước lọc: ${base})`);
  await cdp.ev(CLICK("#btn-reset-filters"));
  await sleep(250);
  items = await cdp.ev(LIST_ITEMS);
  record('Nút "Xóa bộ lọc" khôi phục số món', items.length === base || items.length > 5, `${items.length} món`);

  // e) Trang Hành vi Food.com: tên món phải là món Âu Mỹ (không có chữ Việt có dấu)
  await cdp.ev(`window.location.hash = '#/hanh-vi'`);
  await sleep(300);
  await cdp.ev(CLICK('[data-bds="food_com"]'));
  const fcNames = [];
  for (let i = 0; i < 4; i++) {
    await cdp.ev(`document.querySelectorAll('#cluster-profiles-list .cluster-row')[${i}].click()`);
    await sleep(250);
    fcNames.push(...(await cdp.ev(`[...document.querySelectorAll('#rep-items-container .rep-name')].map((e) => e.textContent)`)));
  }
  const VI = /[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/i;
  record("Hành vi Food.com: không có tên món tiếng Việt có dấu (A1)", fcNames.length > 0 && !fcNames.some((n) => VI.test(n)), `${fcNames.length} món, ví dụ: ${fcNames.slice(0, 3).join(" | ")}`);
}

// ---------------------------------------------------------------------------
async function main() {
  const { proc, wsUrl } = await launch();
  const cdp = new Cdp(wsUrl);
  await cdp.open();
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  let panels = [];
  try {
    panels = await runLayoutChecks(cdp);
    await runDemoFlows(cdp);
  } finally {
    cdp.close();
    proc.kill();
  }
  fs.writeFileSync(RESULT_JSON, JSON.stringify({ results, panels }, null, 2), "utf-8");
  fs.writeFileSync(TEXTS_JSON, JSON.stringify(texts, null, 1), "utf-8");
  const failed = results.filter((r) => !r.ok);
  console.log(`\nTổng: ${results.length - failed.length}/${results.length} đạt; ${failed.length} không đạt`);
  failed.forEach((f) => console.log(" - " + f.name + (f.detail ? ": " + f.detail : "")));
  process.exit(failed.length ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(2); });
