"""
Module thuật toán gợi ý món ăn (Recommendation Engine) cho Streamlit Dashboard.
Hỗ trợ 2 chế độ:
1. Gợi ý cá nhân hóa cho người dùng có sẵn (Personalized ALS Matrix Factorization).
2. Gợi ý cho người dùng mới (Cold-Start Recommender) dựa trên Cosine Item Latent Factor Neighbors.
"""

from typing import List, Dict, Any, Optional
import pandas as pd
from app.utils.data_loader import (
    load_foods_catalog,
    load_recommendations,
    load_item_neighbors,
    load_user_clusters,
)


def get_personalized_recommendations(
    user_id: int,
    dataset: str = "vifoodrec",
    top_n: int = 10,
    dish_type: Optional[str] = None,
    max_time: Optional[int] = None,
    max_calories: Optional[float] = None,
) -> pd.DataFrame:
    """
    Trích xuất danh sách Top-N món ăn gợi ý cho người dùng có sẵn từ mô hình ALS.
    Hỗ trợ bộ lọc loại món, thời gian nấu và lượng calo tối đa.
    """
    recs_df = load_recommendations(dataset)
    if recs_df.empty:
        return pd.DataFrame()

    user_recs = recs_df[recs_df["user_id"] == user_id].copy()
    if user_recs.empty:
        return pd.DataFrame()

    catalog_df = load_foods_catalog(dataset)

    if dataset in ["vifoodrec", "food_vietnam"]:
        # Làm giàu thông tin với danh mục món Việt
        if not catalog_df.empty:
            cols_to_merge = [
                c for c in ["food_id", "cooking_time_min", "ingredients", "dish_tags", "cooking_method", "description"]
                if c in catalog_df.columns
            ]
            user_recs = user_recs.merge(catalog_df[cols_to_merge], on="food_id", how="left")

        # Áp dụng bộ lọc
        if dish_type and dish_type != "Tất cả":
            user_recs = user_recs[user_recs["dish_type"] == dish_type]

        if max_time is not None and "cooking_time_min" in user_recs.columns:
            user_recs = user_recs[
                (user_recs["cooking_time_min"].isna()) | (user_recs["cooking_time_min"] <= max_time)
            ]

        if max_calories is not None and "calories" in user_recs.columns:
            user_recs = user_recs[
                (user_recs["calories"].isna()) | (user_recs["calories"] <= max_calories)
            ]

    else:
        # Food.com
        if not catalog_df.empty:
            cols_to_merge = [
                c for c in ["recipe_id", "n_steps", "n_ingredients", "ingredients", "tags"]
                if c in catalog_df.columns
            ]
            user_recs = user_recs.merge(catalog_df[cols_to_merge], on="recipe_id", how="left")

        if max_time is not None and "minutes_clean" in user_recs.columns:
            user_recs = user_recs[
                (user_recs["minutes_clean"].isna()) | (user_recs["minutes_clean"] <= max_time)
            ]

        if max_calories is not None and "calories" in user_recs.columns:
            user_recs = user_recs[
                (user_recs["calories"].isna()) | (user_recs["calories"] <= max_calories)
            ]

    # Sắp xếp theo rank tăng dần và giới hạn top_n
    user_recs = user_recs.sort_values(by="rank", ascending=True).head(top_n)
    return user_recs


def get_cold_start_recommendations(
    selected_ids: List[int],
    dataset: str = "vifoodrec",
    top_n: int = 10,
    dish_type: Optional[str] = None,
    max_time: Optional[int] = None,
    max_calories: Optional[float] = None,
) -> pd.DataFrame:
    """
    Thuật toán Cold-Start cho người dùng mới:
    Dựa trên 3 đến 5 món yêu thích được chọn, tra cứu ma trận Cosine Item Neighbors
    trích xuất từ ALS Item Latent Factors và tổng hợp các món có độ tương đồng cao nhất.
    """
    if not selected_ids:
        return pd.DataFrame()

    neighbors_df = load_item_neighbors(dataset)
    catalog_df = load_foods_catalog(dataset)

    if neighbors_df.empty or catalog_df.empty:
        return pd.DataFrame()

    id_col = "food_id" if dataset in ["vifoodrec", "food_vietnam"] else "recipe_id"
    name_col = "dish_name" if dataset in ["vifoodrec", "food_vietnam"] else "name"

    # Tạo map tra cứu tên món
    id_to_name = dict(zip(catalog_df[id_col], catalog_df[name_col]))

    # Gom các hàng xóm tương đồng
    candidates: Dict[int, Dict[str, Any]] = {}

    selected_set = set(selected_ids)
    sub_neighbors = neighbors_df[neighbors_df[id_col].isin(selected_set)]

    for _, row in sub_neighbors.iterrows():
        source_id = int(row[id_col])
        source_name = id_to_name.get(source_id, f"Món #{source_id}")
        neighbor_ids = list(row["neighbor_ids"])
        sim_scores = list(row["similarity_scores"])

        for nid, score in zip(neighbor_ids, sim_scores):
            nid = int(nid)
            score = float(score)
            if nid in selected_set:
                continue  # Bỏ qua các món người dùng đã chọn

            if nid not in candidates:
                candidates[nid] = {
                    "total_score": score,
                    "max_score": score,
                    "matches": [(source_name, score)],
                }
            else:
                candidates[nid]["total_score"] += score
                if score > candidates[nid]["max_score"]:
                    candidates[nid]["max_score"] = score
                candidates[nid]["matches"].append((source_name, score))

    if not candidates:
        return pd.DataFrame()

    # Xây dựng DataFrame kết quả ứng viên
    candidate_records = []
    for nid, data in candidates.items():
        # Sắp xếp matches theo độ tương đồng giảm dần
        sorted_matches = sorted(data["matches"], key=lambda x: x[1], reverse=True)
        top_match_name, top_sim = sorted_matches[0]
        
        # Tạo câu lý do giải thích trực quan
        if len(sorted_matches) == 1:
            reason = f"Tương đồng {top_sim*100:.1f}% với món bạn chọn '{top_match_name}'"
        else:
            reason = f"Tương đồng {top_sim*100:.1f}% với '{top_match_name}' và {len(sorted_matches)-1} món khác bạn chọn"

        candidate_records.append({
            id_col: nid,
            "similarity_score": round(data["max_score"], 4),
            "combined_score": round(data["total_score"], 4),
            "recommendation_reason": reason,
        })

    cand_df = pd.DataFrame(candidate_records)

    # Nối với bảng danh mục món để lấy đầy đủ thuộc tính
    merged = cand_df.merge(catalog_df, on=id_col, how="inner")

    # Áp dụng bộ lọc
    if dataset in ["vifoodrec", "food_vietnam"]:
        if dish_type and dish_type != "Tất cả":
            merged = merged[merged["dish_type"] == dish_type]

        if max_time is not None and "cooking_time_min" in merged.columns:
            merged = merged[
                (merged["cooking_time_min"].isna()) | (merged["cooking_time_min"] <= max_time)
            ]

        if max_calories is not None and "calories" in merged.columns:
            merged = merged[
                (merged["calories"].isna()) | (merged["calories"] <= max_calories)
            ]
    else:
        if max_time is not None and "minutes_clean" in merged.columns:
            merged = merged[
                (merged["minutes_clean"].isna()) | (merged["minutes_clean"] <= max_time)
            ]

        if max_calories is not None and "calories" in merged.columns:
            merged = merged[
                (merged["calories"].isna()) | (merged["calories"] <= max_calories)
            ]

    # Sắp xếp theo combined_score hoặc max similarity_score giảm dần
    # Tăng cường độ ưu tiên nếu ứng viên cùng loại món với đa số món được chọn (ví dụ món chay)
    if dataset in ["vifoodrec", "food_vietnam"] and "dish_type" in catalog_df.columns:
        sel_types = catalog_df[catalog_df[id_col].isin(selected_set)]["dish_type"].tolist()
        chay_count = sum(1 for t in sel_types if t == "Món chay")
        if chay_count > len(sel_types) / 2:
            # Người dùng có xu hướng ăn chay rõ rệt: ưu tiên món chay
            merged["type_affinity"] = merged["dish_type"].apply(lambda t: 1.0 if t == "Món chay" else 0.0)
            merged = merged.sort_values(
                by=["type_affinity", "combined_score", "similarity_score"],
                ascending=[False, False, False]
            )
        else:
            merged = merged.sort_values(
                by=["combined_score", "similarity_score"],
                ascending=[False, False]
            )
    else:
        merged = merged.sort_values(
            by=["combined_score", "similarity_score"],
            ascending=[False, False]
        )
    merged = merged.head(top_n).reset_index(drop=True)
    merged["rank"] = range(1, len(merged) + 1)

    return merged
