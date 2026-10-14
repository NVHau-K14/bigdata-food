"""
src/cluster_naming.py
---------------------
Đặt tên cụm dựa trên số liệu hồ sơ cụm, dùng chung cho kmeans_behavior.py và
relabel_food_com_clusters.py. Mỗi tên chỉ được gán khi điều kiện nêu trong tên đúng với
số liệu (cực đại hoặc cực tiểu giữa các cụm); nếu không đúng thì báo lỗi thay vì đặt tên sai.

Quy tắc trình bày (CONTEXT mục 7.8): tiếng Việt viết hoa kiểu câu, không kèm tiếng Anh.
Quy tắc cụm ViFoodRec (CONTEXT mục 7.4): nếu chênh lệch tương đối giữa các cụm ở mọi đặc trưng
nhỏ hơn 10% thì gọi "Cụm 1, 2, 3", không đặt tên diễn giải.
"""

# Ngưỡng chênh lệch tương đối giữa các cụm (CONTEXT mục 7.4)
REL_DIFF_THRESHOLD = 0.10


def relative_differences(cluster_rows, overall_row, feature_cols):
    """
    Chênh lệch tương đối giữa các cụm theo từng đặc trưng:
    (giá trị lớn nhất giữa các cụm - nhỏ nhất) / giá trị trung bình toàn hệ thống của đặc trưng đó.
    Chia cho trung bình toàn hệ thống để cùng một thước đo cho mọi đặc trưng, kể cả tỷ lệ rất nhỏ.
    """
    diffs = {}
    for c in feature_cols:
        vals = [r[c] for r in cluster_rows]
        base = abs(overall_row[c])
        diffs[c] = (max(vals) - min(vals)) / base if base > 0 else float("inf")
    return diffs


def name_vifoodrec_user_clusters(cluster_rows, overall_row, feature_cols):
    """
    Trả về (names, diffs, is_generic). Nếu mọi chênh lệch dưới ngưỡng thì gọi "Cụm 1, 2, ...".
    Nếu có đặc trưng vượt ngưỡng, hàm vẫn trả tên "Cụm n" (chưa đặt tên diễn giải) và is_generic=False
    để người gọi báo lại cho người dùng quyết định.
    """
    diffs = relative_differences(cluster_rows, overall_row, feature_cols)
    is_generic = max(diffs.values()) < REL_DIFF_THRESHOLD
    names = {r["cluster"]: f"Cụm {int(r['cluster']) + 1}" for r in cluster_rows}
    return names, diffs, is_generic


def _check(cond, msg):
    if not cond:
        raise ValueError(f"Tên cụm không khớp số liệu: {msg}")


def name_food_com_user_clusters(cluster_rows):
    """
    Đặt tên 4 cụm người dùng Food.com theo cực trị giữa các cụm.
    cluster_rows: danh sách dict (không gồm dòng Overall) có cluster, avg_rating, n_ratings,
    activity_span_days, avg_minutes, avg_calories.
    """
    _check(len(cluster_rows) == 4, "Food.com cần đúng 4 cụm")
    rest = {r["cluster"]: r for r in cluster_rows}
    names = {}

    strict = min(rest.values(), key=lambda r: r["avg_rating"])
    names[strict["cluster"]] = "Người dùng khắt khe"
    del rest[strict["cluster"]]

    veteran = max(rest.values(), key=lambda r: r["n_ratings"])
    _check(all(veteran["activity_span_days"] >= r["activity_span_days"] for r in cluster_rows),
           "cụm lâu năm phải có thời gian hoạt động dài nhất")
    names[veteran["cluster"]] = "Thành viên lâu năm, đánh giá nhiều"
    del rest[veteran["cluster"]]

    slow = max(rest.values(), key=lambda r: r["avg_minutes"])
    _check(all(slow["avg_calories"] >= r["avg_calories"] for r in cluster_rows),
           "cụm món nấu lâu phải có calo trung bình cao nhất")
    names[slow["cluster"]] = "Người chuộng món nấu lâu, nhiều calo"
    del rest[slow["cluster"]]

    (fast,) = rest.values()
    _check(all(fast["avg_minutes"] <= r["avg_minutes"] for r in cluster_rows),
           "cụm món nấu nhanh phải có thời gian nấu thấp nhất")
    _check(all(fast["avg_calories"] <= r["avg_calories"] for r in cluster_rows),
           "cụm món ít calo phải có calo trung bình thấp nhất")
    names[fast["cluster"]] = "Người chuộng món nấu nhanh, ít calo"
    return names


def name_vifoodrec_food_clusters(cluster_rows):
    """
    Đặt tên 4 cụm món ăn ViFoodRec theo cực trị. cluster_rows có cluster, is_savory, calories, sugar.
    """
    _check(len(cluster_rows) == 4, "món ViFoodRec cần đúng 4 cụm")
    names = {}
    rest = {r["cluster"]: r for r in cluster_rows}

    veg = [r for r in rest.values() if r["is_savory"] < 0.5]
    _check(len(veg) == 1, "cần đúng một cụm món chay")
    names[veg[0]["cluster"]] = "Món chay"
    del rest[veg[0]["cluster"]]

    low_cal = min(rest.values(), key=lambda r: r["calories"])
    names[low_cal["cluster"]] = "Món mặn ít calo"
    del rest[low_cal["cluster"]]

    low_sugar = min(rest.values(), key=lambda r: r["sugar"])
    names[low_sugar["cluster"]] = "Món mặn ít đường"
    del rest[low_sugar["cluster"]]

    (rich,) = rest.values()
    savory = [r for r in cluster_rows if r["is_savory"] >= 0.5]
    _check(all(rich["calories"] >= r["calories"] for r in savory),
           "cụm món mặn nhiều calo và đường phải có calo cao nhất trong các cụm món mặn")
    _check(all(rich["sugar"] >= r["sugar"] for r in savory),
           "cụm món mặn nhiều calo và đường phải có đường cao nhất trong các cụm món mặn")
    names[rich["cluster"]] = "Món mặn nhiều calo và đường"
    return names
