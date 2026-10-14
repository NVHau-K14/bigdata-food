/**
 * Định dạng số theo quy chuẩn tiếng Việt. MỌI số hiển thị trên web đi qua hàm fmt() trong file này.
 * Quy chuẩn:
 * - Dấu chấm phân tách hàng nghìn: 149.431
 * - Dấu phẩy phân tách phần thập phân: 1,3832 hoặc 54,8%
 * - Không viết tắt "K" cho nghìn.
 * Số chữ số thập phân theo độ đo (A4): RMSE và MAE 4 chữ số; Precision@10 và Recall@10 5 chữ số.
 */
(function (window) {
  "use strict";

  const METRIC_DIGITS = { RMSE: 4, MAE: 4, "Precision@10": 5, "Recall@10": 5 };
  const EMPTY = "không áp dụng";

  /**
   * Hàm định dạng số duy nhất.
   * @param {number|string|null} val Giá trị cần định dạng.
   * @param {number|null} decimals Số chữ số thập phân cố định; null thì số nguyên giữ nguyên,
   *   số thực lấy tối đa 4 chữ số và bỏ số 0 thừa ở cuối.
   * @returns {string}
   */
  function fmt(val, decimals = null) {
    if (val === null || val === undefined || val === "" || isNaN(val)) return EMPTY;
    const num = Number(val);
    let s;
    if (decimals !== null) {
      s = num.toFixed(decimals);
    } else if (Number.isInteger(num)) {
      s = String(num);
    } else {
      s = num.toFixed(4).replace(/\.?0+$/, "");
    }
    const parts = s.split(".");
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return parts.join(",");
  }

  /** Phần trăm: fmtPct(54.79, 2) cho "54,79%". Giá trị đầu vào ở thang 0 đến 100. */
  function fmtPct(val, decimals = 1) {
    const s = fmt(val, decimals);
    return s === EMPTY ? s : s + "%";
  }

  /** Số kèm đơn vị, ví dụ fmtUnit(2.73, "s", 2) cho "2,73 s". */
  function fmtUnit(val, unit, decimals = null) {
    const s = fmt(val, decimals);
    return s === EMPTY ? s : s + " " + unit;
  }

  /** Số theo độ đo (RMSE, MAE, Precision@10, Recall@10) với số chữ số cố định. */
  function fmtMetric(metric, val) {
    return fmt(val, METRIC_DIGITS[metric] !== undefined ? METRIC_DIGITS[metric] : null);
  }

  /** Độ lệch có dấu, ví dụ +12,3% hoặc -4,5%. */
  function fmtSigned(val, decimals = 1) {
    const num = Number(val);
    return (num >= 0 ? "+" : "-") + fmt(Math.abs(num), decimals) + "%";
  }

  /** Loại bỏ dấu tiếng Việt để tìm kiếm không dấu ("bún bò" thành "bun bo"). */
  function removeVietnameseTones(str) {
    if (!str) return "";
    return String(str)
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/đ/g, "d")
      .trim();
  }

  window.FormatUtils = {
    fmt,
    fmtPct,
    fmtUnit,
    fmtMetric,
    fmtSigned,
    removeVietnameseTones,
    METRIC_DIGITS,
    EMPTY
  };
})(window);
