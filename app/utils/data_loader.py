"""
Module quản lý nạp và cache dữ liệu cho Streamlit Dashboard.
Tuyệt đối không gọi PySpark, thuần túy dùng Pandas và PyArrow.
Tất cả hàm đều sử dụng @st.cache_data để tối ưu hiệu năng.
"""

from pathlib import Path
import pandas as pd
import streamlit as st

# Đường dẫn thư mục dữ liệu
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EDA_DIR = DATA_DIR / "eda"


@st.cache_data(show_spinner=False)
def load_dataset_comparison() -> pd.DataFrame:
    """Nạp bảng so sánh tổng quan 2 bộ dữ liệu."""
    path = DATA_DIR / "eda_12_dataset_comparison.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_cleaning_log() -> pd.DataFrame:
    """Nạp nhật ký tiền xử lý và làm sạch dữ liệu."""
    path = DATA_DIR / "cleaning_log.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_storage_benchmark() -> pd.DataFrame:
    """Nạp kết quả benchmark lưu trữ CSV vs Parquet."""
    path = DATA_DIR / "storage_benchmark.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_foods_catalog(dataset: str = "vifoodrec") -> pd.DataFrame:
    """Nạp danh mục món ăn (ViFoodRec 4,000 món hoặc Food.com mẫu)."""
    if dataset in ["vifoodrec", "food_vietnam"]:
        path = DATA_DIR / "foods_vietnam.parquet"
    else:
        path = DATA_DIR / "recipes_foodcom_sample.parquet"
    
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_recommendations(dataset: str = "vifoodrec") -> pd.DataFrame:
    """Nạp kết quả gợi ý Top-10 từ mô hình ALS."""
    if dataset in ["vifoodrec", "food_vietnam"]:
        path = DATA_DIR / "recommendations_vietnam.parquet"
    else:
        path = DATA_DIR / "recommendations_foodcom_sample.parquet"
    
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_item_neighbors(dataset: str = "vifoodrec") -> pd.DataFrame:
    """Nạp ma trận món tương đồng Cosine phục vụ Cold-Start."""
    if dataset in ["vifoodrec", "food_vietnam"]:
        path = DATA_DIR / "item_neighbors_vietnam.parquet"
    else:
        path = DATA_DIR / "item_neighbors_foodcom.parquet"
    
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_user_clusters(dataset: str = "vifoodrec") -> pd.DataFrame:
    """Nạp nhãn phân cụm người dùng."""
    if dataset in ["vifoodrec", "food_vietnam"]:
        path = DATA_DIR / "user_clusters_vietnam.parquet"
    else:
        path = DATA_DIR / "user_clusters_foodcom.parquet"
    
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_cluster_profiles(dataset: str = "vifoodrec") -> pd.DataFrame:
    """Nạp bảng hồ sơ định lượng cụm người dùng."""
    if dataset in ["vifoodrec", "food_vietnam"]:
        path = DATA_DIR / "cluster_profiles_food_vietnam.csv"
    else:
        path = DATA_DIR / "cluster_profiles_food_com.csv"
    
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_food_clusters() -> pd.DataFrame:
    """Nạp nhãn phân cụm món ăn ViFoodRec."""
    path = DATA_DIR / "food_clusters_vietnam.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_food_cluster_profiles() -> pd.DataFrame:
    """Nạp hồ sơ định lượng 4 cụm món ăn ViFoodRec."""
    path = DATA_DIR / "food_cluster_profiles_vietnam.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_model_comparison() -> pd.DataFrame:
    """Nạp bảng so sánh mô hình Baseline và ALS."""
    path = DATA_DIR / "model_comparison.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_als_tuning(dataset: str = "vifoodrec") -> pd.DataFrame:
    """Nạp nhật ký tinh chỉnh siêu tham số ALS Grid Search."""
    if dataset in ["vifoodrec", "food_vietnam"]:
        path = DATA_DIR / "als_tuning_food_vietnam.csv"
    else:
        path = DATA_DIR / "als_tuning_food_com.csv"
    
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_rmse_breakdown(dataset: str = "vifoodrec") -> pd.DataFrame:
    """Nạp bảng phân rã RMSE theo từng thang điểm rating."""
    path_als = DATA_DIR / "als_rmse_breakdown.csv"
    path_base = DATA_DIR / "baseline_rmse_breakdown.csv"
    
    dfs = []
    dataset_key = "food_vietnam" if dataset in ["vifoodrec", "food_vietnam"] else "food_com"
    
    if path_als.exists():
        df_a = pd.read_csv(path_als)
        df_a = df_a[df_a["dataset"] == dataset_key]
        dfs.append(df_a)
        
    if path_base.exists():
        df_b = pd.read_csv(path_base)
        df_b = df_b[df_b["dataset"] == dataset_key]
        dfs.append(df_b)
        
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_scalability() -> pd.DataFrame:
    """Nạp kết quả thực nghiệm mở rộng quy mô."""
    path = DATA_DIR / "scalability.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_kmeans_tuning() -> pd.DataFrame:
    """Nạp kết quả dò tìm số cụm k tối ưu (Silhouette & WSSSE)."""
    path = DATA_DIR / "kmeans_tuning.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_eda_table(filename: str) -> pd.DataFrame:
    """Nạp bảng dữ liệu EDA chỉ định."""
    path = EDA_DIR / filename
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()
