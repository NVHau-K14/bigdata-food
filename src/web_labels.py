"""
src/web_labels.py
-----------------
Bảng nhãn hiển thị DUY NHẤT cho dashboard web (S4). Dùng chung cho export_for_web.py (sinh web/data/labels.js)
và verify_web.py (đối chiếu), để hai bên không lệch nhau.

Dữ liệu gốc không bị đổi: chỉ chữ hiển thị trên web được ánh xạ.
- dish_type: cột nguồn chỉ có "Món mặn" (3.805) và "Món chay" (195); chè bí đỏ, bánh bò cũng là "Món mặn",
  nên "mặn" thực chất là "không gắn nhãn chay", web hiển thị "Không chay".
- Tên mô hình: bỏ tiếng Anh, giữ tên kỹ thuật ALS.
"""

DISH_TYPE_LABELS = {
    "Món mặn": "Không chay",
    "Món chay": "Chay",
}

# Trong tên cụm món (do S3 đặt), "Món mặn" thay bằng "Món không chay" cho đúng nghĩa của dữ liệu
CLUSTER_NAME_REPLACEMENTS = [("Món mặn", "Món không chay")]

MODEL_LABELS = {
    "Global Mean": "Trung bình toàn cục",
    "Smoothed Item Mean": "Trung bình món làm trơn",
    "Top-N Popular": "Top món phổ biến",
    "ALS Matrix Factorization": "ALS dự đoán điểm",
    "ALS ngầm định (điểm >= 4)": "ALS ngầm định",
}

# Dòng trùng hệt ALS cũ của Food.com (S3b), không hiển thị
HIDDEN_MODELS = {"ALS Matrix Factorization (lưới mở rộng)"}

DATASET_LABELS = {
    "food_com": "Food.com",
    "food_vietnam": "ViFoodRec",
}

# Nhãn chỉ số trong bảng đối chiếu hai bộ (bỏ phần tiếng Anh trong ngoặc của file nguồn)
COMPARISON_LABELS = {
    "Số User (Users)": "Số người dùng",
    "Số Món (Items)": "Số món",
    "Số Tương tác (Ratings)": "Số đánh giá",
    "Độ thưa ma trận (Sparsity %)": "Độ thưa của ma trận",
    "Điểm TB (Mean Rating)": "Điểm trung bình",
    "Trung vị tương tác/User": "Trung vị đánh giá mỗi người",
    "Trung vị tương tác/Item": "Trung vị đánh giá mỗi món",
}


def display_dish_type(value):
    return DISH_TYPE_LABELS.get(value, value)


def display_cluster_name(name):
    out = name
    for old, new in CLUSTER_NAME_REPLACEMENTS:
        out = out.replace(old, new)
    return out


def display_model(name):
    return MODEL_LABELS.get(name, name)
