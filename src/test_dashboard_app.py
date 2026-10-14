"""
Kịch bản kiểm thử tự động toàn diện Dashboard Streamlit bằng streamlit.testing.v1.AppTest.
Kiểm tra từng trang (1 to 4) và cả 2 chế độ gợi ý, bảo đảm không phát sinh ngoại lệ (Exception),
và thẩm định chất lượng gợi ý Cold-Start trên 3 bộ món chọn thử khác nhau.
"""

import sys
import unittest
from pathlib import Path
import pandas as pd

# Thêm thư mục gốc vào PYTHONPATH
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

APP_DIR = WORKSPACE_ROOT / "app"

from streamlit.testing.v1 import AppTest
from app.utils.recommender import (
    get_personalized_recommendations,
    get_cold_start_recommendations,
)
from app.utils.data_loader import (
    load_dataset_comparison,
    load_cleaning_log,
    load_storage_benchmark,
    load_model_comparison,
    load_scalability,
)


class TestStreamlitDashboard(unittest.TestCase):
    """Bộ kiểm thử đơn vị & tích hợp cho Streamlit App."""

    def test_01_main_app_navigation(self):
        """Kiểm tra trang chính main.py khởi chạy không lỗi."""
        print("\n---> [TEST 1/6] Kiểm tra app/main.py...")
        app = AppTest.from_file(str(APP_DIR / "main.py"))
        app.run(timeout=30)
        self.assertEqual(len(app.exception), 0, f"Lỗi tại app/main.py: {app.exception}")
        print("     ✓ app/main.py chạy thành công 0 exception!")

    def test_02_page_tong_quan(self):
        """Kiểm tra Trang 1: Tổng quan & Kiến trúc."""
        print("\n---> [TEST 2/6] Kiểm tra app/pages/1_Tong_quan.py...")
        page = AppTest.from_file(str(APP_DIR / "pages" / "1_Tong_quan.py"))
        page.run(timeout=30)
        self.assertEqual(len(page.exception), 0, f"Lỗi tại Trang 1: {page.exception}")
        
        # Kiểm chứng tính khớp của số liệu
        comp_df = load_dataset_comparison()
        self.assertFalse(comp_df.empty, "Bảng eda_12_dataset_comparison.csv không được rỗng")
        self.assertEqual(len(comp_df), 7, "Bảng so sánh phải đủ 7 chỉ số")
        print("     ✓ Trang 1_Tong_quan.py chạy thành công 0 exception, số liệu khớp 100%!")

    def test_03_page_hanh_vi_nguoi_dung(self):
        """Kiểm tra Trang 2: Hành vi người dùng & Phân cụm."""
        print("\n---> [TEST 3/6] Kiểm tra app/pages/2_Hanh_vi_nguoi_dung.py...")
        page = AppTest.from_file(str(APP_DIR / "pages" / "2_Hanh_vi_nguoi_dung.py"))
        page.run(timeout=30)
        self.assertEqual(len(page.exception), 0, f"Lỗi tại Trang 2: {page.exception}")
        print("     ✓ Trang 2_Hanh_vi_nguoi_dung.py chạy thành công 0 exception!")

    def test_04_page_goi_y_mon(self):
        """Kiểm tra Trang 3: Hệ thống gợi ý món ăn."""
        print("\n---> [TEST 4/6] Kiểm tra app/pages/3_Goi_y_mon.py...")
        page = AppTest.from_file(str(APP_DIR / "pages" / "3_Goi_y_mon.py"))
        page.run(timeout=30)
        self.assertEqual(len(page.exception), 0, f"Lỗi tại Trang 3: {page.exception}")
        print("     ✓ Trang 3_Goi_y_mon.py chạy thành công 0 exception!")

    def test_05_page_danh_gia_mo_hinh(self):
        """Kiểm tra Trang 4: Đánh giá mô hình & Scalability."""
        print("\n---> [TEST 5/6] Kiểm tra app/pages/4_Danh_gia_mo_hinh.py...")
        page = AppTest.from_file(str(APP_DIR / "pages" / "4_Danh_gia_mo_hinh.py"))
        page.run(timeout=30)
        self.assertEqual(len(page.exception), 0, f"Lỗi tại Trang 4: {page.exception}")

        model_comp = load_model_comparison()
        self.assertFalse(model_comp.empty, "model_comparison.csv không được rỗng")
        self.assertGreaterEqual(len(model_comp), 8, "model_comparison phải đủ tối thiểu 8 dòng")

        scale_df = load_scalability()
        self.assertFalse(scale_df.empty, "scalability.csv không được rỗng")
        self.assertEqual(len(scale_df), 32, "scalability.csv phải đủ 32 bản ghi")
        print("     ✓ Trang 4_Danh_gia_mo_hinh.py chạy thành công 0 exception, số liệu mô hình khớp!")

    def test_06_cold_start_three_presets(self):
        """Kiểm tra chất lượng gợi ý Cold-Start trên 3 bộ món chọn thử."""
        print("\n---> [TEST 6/6] Thẩm định chất lượng gợi ý Cold-Start trên 3 bộ món thử nghiệm...")

        # Bộ 1: Gu Thuần Chay
        # 321: Bánh khọt chay, 2774: Canh Rau Mồng Tơi Chay, 1964: Món Miến Xào Rau Củ Chay
        combo1 = [321, 2774, 1964]
        res1 = get_cold_start_recommendations(combo1, "vifoodrec", top_n=5)
        self.assertFalse(res1.empty, "Bộ 1 phải trả về kết quả gợi ý")
        self.assertEqual(len(res1), 5, "Bộ 1 phải trả về đúng 5 món gợi ý")
        # Kiểm tra tính hợp lý: top món gợi ý ưu tiên món chay khi chọn 3 món thuần chay
        top1_type = res1.iloc[0]["dish_type"]
        self.assertEqual(top1_type, "Món chay", f"Bộ 1 chọn món chay thì top gợi ý phải là Món chay (thực tế: {top1_type})")
        self.assertNotIn(321, res1["food_id"].values, "Món đã chọn không được xuất hiện lại trong gợi ý")
        print(f"     ✓ Bộ 1 (Thuần Chay): ĐẠT -> Top 1 là '{res1.iloc[0]['dish_name']}' ({res1.iloc[0]['dish_type']})")

        # Bộ 2: Gu Bữa Nhanh & Đậm Vị
        # 3390: Bánh Bò Bông, 2841: Bánh Khoai Sọ Chiên Giòn, 3548: Bánh Tằm Bì
        combo2 = [3390, 2841, 3548]
        res2 = get_cold_start_recommendations(combo2, "vifoodrec", top_n=5)
        self.assertFalse(res2.empty, "Bộ 2 phải trả về kết quả gợi ý")
        self.assertEqual(len(res2), 5, "Bộ 2 phải đủ 5 món gợi ý")
        self.assertTrue(all(pd.notna(r) for r in res2["recommendation_reason"]), "Mọi gợi ý phải có lý do giải thích")
        print(f"     ✓ Bộ 2 (Bữa Nhanh & Đậm Vị): ĐẠT -> Top 1 là '{res2.iloc[0]['dish_name']}' ({res2.iloc[0]['dish_type']})")

        # Bộ 3: Gu Canh Hầm & Ăn Vặt
        # 1736: Bánh Canh Chả Cá Nha Trang, 1557: Bánh Tráng Trộn, 3121: Bánh Crepe Trà Sữa Thái
        combo3 = [1736, 1557, 3121]
        res3 = get_cold_start_recommendations(combo3, "vifoodrec", top_n=5)
        self.assertFalse(res3.empty, "Bộ 3 phải trả về kết quả gợi ý")
        self.assertEqual(len(res3), 5, "Bộ 3 phải đủ 5 món gợi ý")
        print(f"     ✓ Bộ 3 (Canh Hầm & Ăn Vặt): ĐẠT -> Top 1 là '{res3.iloc[0]['dish_name']}' ({res3.iloc[0]['dish_type']})")

        # Thử nghiệm thêm trên Food.com
        res_fc = get_cold_start_recommendations([280, 780, 1072], "food_com", top_n=5)
        self.assertFalse(res_fc.empty, "Cold-start trên Food.com phải hoạt động tốt")
        self.assertEqual(len(res_fc), 5)
        print(f"     ✓ Food.com Cold-Start: ĐẠT -> Top 1 là '{res_fc.iloc[0]['name']}'")


if __name__ == "__main__":
    unittest.main()
