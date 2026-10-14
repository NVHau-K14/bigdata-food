"""
src/verify_web_style.py
-----------------------
Kiểm tra kiểu dáng và khả năng đọc của dashboard web (S4, mục E3, E4, E5).

1. Quét mã (web/index.html, web/css/*.css, web/js/*.js): không emoji, không ký tự biểu tượng (kể cả dấu tích và mũi tên),
   không text-transform khác none, không gradient, không box-shadow, không animation tự chạy.
2. Tương phản WCAG: chữ chính và chữ phụ 7:1, chữ nhỏ 4,5:1, đường và cột biểu đồ 3:1.
3. Màu biểu đồ: xanh lá đậm và xám trung tính phải khác nhau rõ về độ sáng (đọc được ở thang xám).
4. Diện tích màu cam đo trên ảnh chụp từng trang (reports/figures/screenshots/web_v2/): dưới 2% mỗi ảnh.
5. Mô phỏng chia sẻ online: thu nhỏ ảnh 1920x1080 còn 960x540, nén JPEG 60%, rồi đo tỷ lệ chữ còn đủ lớn để đọc
   (cỡ chữ sau khi thu nhỏ từ 9 px trở lên), dựa trên thống kê cỡ chữ do verify_web_ui.mjs ghi.
Thoát mã khác 0 nếu có mục không đạt (mục 5 chỉ báo cáo, không làm thất bại, vì là giới hạn của việc thu nhỏ ảnh).
"""

import glob
import json
import os
import re
import sys
import unicodedata

import numpy as np
from PIL import Image

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SHOT_DIR = "reports/figures/screenshots/web_v2"
UI_RESULTS = "reports/evidence/logs/S4_ui_results.json"
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"[{'DAT' if ok else 'KHONG DAT'}] {name}" + (f" : {detail}" if detail else ""))


def lum(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def css_tokens():
    css = open("web/css/style.css", encoding="utf-8").read()
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})", css))


def main():
    print("=" * 70)
    print(" KIỂM TRA KIỂU DÁNG, TƯƠNG PHẢN VÀ KHẢ NĂNG ĐỌC (src/verify_web_style.py)")
    print("=" * 70)

    # ------------------------------------------------------------------ 1. quét mã
    print("\n--- 1. Quét mã ---")
    files = ["web/index.html", "web/config.js"] + sorted(glob.glob("web/css/style.css")) + sorted(glob.glob("web/js/*.js")) + ["web/data/labels.js"]
    symbol_cats = {"So", "Sk", "Sm"}
    allowed_sm = set("+<>=~|^`")  # dấu huyền dùng cho chuỗi mẫu của JavaScript
    bad_chars = {}
    for f in files:
        text = open(f, encoding="utf-8").read()
        for ch in set(text):
            cat = unicodedata.category(ch)
            if (cat in symbol_cats and ch not in allowed_sm) or ch in "•–—" or cat == "Cs" or ord(ch) >= 0x1F000:
                bad_chars.setdefault(f, set()).add(ch)
    check("Không emoji hay ký tự biểu tượng (kể cả dấu tích, mũi tên, so sánh, nhân, cộng trừ, gạch dài) trong mã web",
          not bad_chars, "; ".join(f"{f}: {''.join(sorted(v))}" for f, v in bad_chars.items()))

    css = open("web/css/style.css", encoding="utf-8").read()
    css_nocomment = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    check("Không có text-transform khác none", all(v == "none" for v in re.findall(r"text-transform:\s*([a-z-]+)", css_nocomment)))
    check("Không có gradient", "gradient(" not in css_nocomment)
    check("Không có box-shadow (ngoài dòng chú thích)", "box-shadow" not in css_nocomment)
    check("Không có animation hay @keyframes tự chạy", "@keyframes" not in css_nocomment and not re.search(r"animation\s*:", css_nocomment))
    js_all = "".join(open(f, encoding="utf-8").read() for f in sorted(glob.glob("web/js/*.js")))
    check("Không có setInterval hay requestAnimationFrame tự chạy trong JS", "setInterval" not in js_all and "requestAnimationFrame" not in js_all)

    # ------------------------------------------------------------------ 2. tương phản
    print("\n--- 2. Tương phản WCAG ---")
    t = css_tokens()
    pairs = [
        ("Chữ chính trên nền trắng", t["text-primary"], t["bg-main"], 7.0),
        ("Chữ phụ trên nền trắng", t["text-secondary"], t["bg-main"], 7.0),
        ("Chữ phụ trên nền phụ (tiêu đề cột)", t["text-secondary"], t["bg-subtle"], 7.0),
        ("Chữ xanh lá trên nền trắng", t["brand-green"], t["bg-main"], 7.0),
        ("Chữ xanh lá trên nền chọn (dòng cụm)", t["brand-green"], t["bg-selected"], 7.0),
        ("Chữ trắng trên nút xanh lá", "#FFFFFF", t["brand-green"], 7.0),
        ("Chữ cam nhỏ trên nền trắng (số dòng bị loại)", t["accent-orange"], t["bg-main"], 4.5),
        ("Chữ cam nhỏ trên nền phụ (dòng cảnh báo)", t["accent-orange"], t["bg-subtle"], 4.5),
        ("Cột biểu đồ xanh lá đậm trên nền trắng", t["brand-green"], t["bg-main"], 3.0),
        ("Cột biểu đồ xám trung tính trên nền trắng", t["neutral"], t["bg-main"], 3.0),
    ]
    for name, fg, bg, need in pairs:
        r = contrast(fg, bg)
        check(f"{name}: {r:.2f}:1 (cần từ {need}:1)", r >= need)

    # ------------------------------------------------------------------ 3. thang xám
    print("\n--- 3. Màu biểu đồ ở thang xám ---")
    g = lambda hx: round(0.299 * int(hx[1:3], 16) + 0.587 * int(hx[3:5], 16) + 0.114 * int(hx[5:7], 16))
    gp, gn = g(t["brand-green"]), g(t["neutral"])
    check(f"Xanh lá đậm (xám {gp}/255) và xám trung tính (xám {gn}/255) cách nhau từ 40 bậc",
          abs(gp - gn) >= 40)
    check(f"Độ chói tương đối khác nhau từ 0,1 ({lum(t['brand-green']):.3f} và {lum(t['neutral']):.3f})",
          abs(lum(t["brand-green"]) - lum(t["neutral"])) >= 0.1)

    # ------------------------------------------------------------------ 4. diện tích cam
    print("\n--- 4. Diện tích màu cam trên ảnh chụp ---")
    ar, ag, ab = (int(t["accent-orange"][i:i + 2], 16) for i in (1, 3, 5))
    shots = sorted(glob.glob(os.path.join(SHOT_DIR, "*x*_*.png")))
    check("Có ảnh chụp để đo", len(shots) > 0, f"{len(shots)} ảnh")
    worst = (0.0, "")
    for f in shots:
        a = np.asarray(Image.open(f).convert("RGB")).astype(int)
        near = (abs(a[..., 0] - ar) < 40) & (abs(a[..., 1] - ag) < 40) & (abs(a[..., 2] - ab) < 40)
        share = near.mean() * 100
        if share > worst[0]:
            worst = (share, os.path.basename(f))
    check(f"Diện tích cam lớn nhất trên một ảnh: {worst[0]:.3f}% ({worst[1]}), cần dưới 2%", worst[0] < 2.0)

    # ------------------------------------------------------------------ 5. mô phỏng chia sẻ
    print("\n--- 5. Mô phỏng chia sẻ online (960x540, JPEG 60%) ---")
    share_dir = os.path.join(SHOT_DIR, "chia_se_960x540")
    os.makedirs(share_dir, exist_ok=True)
    ui = json.load(open(UI_RESULTS, encoding="utf-8")) if os.path.exists(UI_RESULTS) else {}
    fonts_by_tag = {p["tag"]: p.get("fonts", {}) for p in ui.get("panels", [])}
    sizes = []
    for f in [x for x in shots if os.path.basename(x).startswith("1920x1080_")]:
        name = os.path.splitext(os.path.basename(f))[0]
        im = Image.open(f).convert("RGB").resize((960, 540), Image.LANCZOS)
        out = os.path.join(share_dir, name + ".jpg")
        im.save(out, "JPEG", quality=60)
        sizes.append(os.path.getsize(out) / 1024)
    check(f"Đã tạo {len(sizes)} ảnh chia sẻ", len(sizes) > 0, f"dung lượng trung bình {np.mean(sizes):.0f} KB")

    print("    Tỷ lệ ký tự có cỡ chữ từ 9 px trở lên sau khi thu nhỏ một nửa (chỉ báo cáo):")
    for tag, fonts in sorted(fonts_by_tag.items()):
        if not tag.startswith("1920x1080"):
            continue
        total = sum(fonts.values())
        readable = sum(c for px, c in fonts.items() if float(px) * 0.5 >= 9)
        print(f"    - {tag}: {readable / total * 100:5.1f}% ký tự ({readable}/{total})" if total else f"    - {tag}: không có dữ liệu")

    total = len(results)
    passed = sum(results)
    print("\n" + "=" * 70)
    print(f" KẾT QUẢ: {passed}/{total} đạt")
    print("=" * 70)
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
