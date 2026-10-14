/**
 * Module định dạng số chuẩn hóa theo quy chuẩn tiếng Việt và tiện ích xử lý chuỗi.
 * Quy chuẩn:
 * - Dấu chấm (.) phân tách hàng nghìn: 149.431
 * - Dấu phẩy (,) phân tách phần thập phân: 1,3832 hoặc 63,0%
 * - Tuyệt đối không viết tắt "K" (149K -> 149.431)
 */

/**
 * Định dạng số nguyên hoặc số thực theo chuẩn Việt Nam.
 * @param {number|string} val - Giá trị số cần định dạng
 * @param {number|null} decimals - Số chữ số phần thập phân cố định (nếu null thì tự động giữ theo số ban đầu, tối đa 4)
 * @returns {string} Chuỗi số đã định dạng
 */
function formatNumber(val, decimals = null) {
  if (val === null || val === undefined || isNaN(val)) {
    return "—";
  }
  const num = Number(val);
  
  let formatted;
  if (decimals !== null) {
    formatted = num.toFixed(decimals);
  } else {
    // Nếu là số nguyên thì không thập phân, nếu là số thực thì tối đa 4 chữ số
    if (Number.isInteger(num)) {
      formatted = num.toString();
    } else {
      formatted = num.toFixed(4).replace(/\.?0+$/, "");
    }
  }

  const parts = formatted.split(".");
  // Thêm dấu chấm phân tách hàng nghìn
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  // Ghép lại bằng dấu phẩy thập phân
  return parts.length > 1 ? parts.join(",") : parts[0];
}

/**
 * Định dạng phần trăm theo chuẩn tiếng Việt (ví dụ: 63,0%).
 * @param {number|string} val - Giá trị phần trăm (0 - 100 hoặc 0 - 1)
 * @param {number} decimals - Số chữ số thập phân (mặc định 1)
 * @param {boolean} isFraction - true nếu giá trị ở khoảng [0, 1] cần nhân 100
 * @returns {string}
 */
function formatPercent(val, decimals = 1, isFraction = false) {
  if (val === null || val === undefined || isNaN(val)) {
    return "—";
  }
  let num = Number(val);
  if (isFraction) {
    num = num * 100;
  }
  return formatNumber(num, decimals) + "%";
}

/**
 * Loại bỏ dấu tiếng Việt để phục vụ tìm kiếm không dấu ("bún bò" -> "bun bo").
 * @param {string} str - Chuỗi nguồn
 * @returns {string} Chuỗi không dấu, chữ thường
 */
function removeVietnameseTones(str) {
  if (!str) return "";
  str = String(str).toLowerCase().trim();
  str = str.replace(/à|á|ạ|ả|ã|â|ầ|ấ|ậ|ẩ|ẫ|ă|ằ|ắ|ặ|ẳ|ẵ/g, "a");
  str = str.replace(/è|é|ẹ|ẻ|ẽ|ê|ề|ế|ệ|ể|ễ/g, "e");
  str = str.replace(/ì|í|ị|ỉ|ĩ/g, "i");
  str = str.replace(/ò|ó|ọ|ỏ|õ|ô|ồ|ố|ộ|ổ|ỗ|ơ|ờ|ớ|ợ|ở|ỡ/g, "o");
  str = str.replace(/ù|ú|ụ|ủ|ũ|ư|ừ|ứ|ự|ử|ữ/g, "u");
  str = str.replace(/ỳ|ý|ỵ|ỷ|ỹ/g, "y");
  str = str.replace(/đ/g, "d");
  // Loại bỏ các ký tự dấu tổ hợp Unicode
  str = str.replace(/\u0300|\u0301|\u0303|\u0309|\u0323/g, "");
  str = str.replace(/\u02C6|\u0306|\u031B/g, "");
  return str;
}

window.FormatUtils = {
  formatNumber,
  formatPercent,
  removeVietnameseTones
};
