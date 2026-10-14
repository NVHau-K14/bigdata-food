"""
scratch/s6_compare.py
---------------------
Stage S6: so sánh kết quả của bản chạy sạch (thư mục sao) với bản chính.
Với mỗi tệp CSV trong results/ và reports/evidence/ có ở cả hai bản: báo giống hệt từng byte, giống số liệu
(sau khi đọc bằng pandas), hoặc khác (nêu cột khác và chênh lệch lớn nhất). Với Parquet trong app/data/:
so sánh số dòng, tên cột và tổng các cột số. Cột thời gian được tách riêng vì được phép khác.

Cách chạy: python -I scratch/s6_compare.py <thư mục bản chính> <thư mục bản sao>
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

TIME_COLS = {"time_run_1", "time_run_2", "avg_time", "avg_time_sec", "std_time_sec", "time_sec", "train_time_sec",
             "fit_time", "elapsed_sec", "seconds", "duration_sec", "tuning_time_sec", "time"}


def compare_csv(a: Path, b: Path):
    if a.read_bytes() == b.read_bytes():
        return "GIỐNG TỪNG BYTE", ""
    try:
        da = pd.read_csv(a, encoding="utf-8-sig")
        db = pd.read_csv(b, encoding="utf-8-sig")
    except Exception as e:
        return "KHÔNG ĐỌC ĐƯỢC", str(e)
    if list(da.columns) != list(db.columns):
        return "KHÁC CỘT", f"{list(da.columns)} so với {list(db.columns)}"
    if len(da) != len(db):
        return "KHÁC SỐ DÒNG", f"{len(da)} so với {len(db)}"
    # Thứ tự dòng có thể khác giữa hai lần chạy (ghi Parquet, gộp bảng); so sau khi sắp xếp theo cột không phải thời gian
    keys = [c for c in da.columns if c not in TIME_COLS]
    da = da.sort_values(keys, kind="mergesort").reset_index(drop=True)
    db = db.sort_values(keys, kind="mergesort").reset_index(drop=True)
    diffs, tdiffs = [], []
    for c in da.columns:
        if pd.api.types.is_numeric_dtype(da[c]) and pd.api.types.is_numeric_dtype(db[c]):
            d = np.nanmax(np.abs(da[c].to_numpy(float) - db[c].to_numpy(float))) if len(da) else 0.0
            if d > 0:
                (tdiffs if c in TIME_COLS else diffs).append(f"{c}: lệch tối đa {d:.6g}")
        else:
            if not da[c].fillna("").astype(str).equals(db[c].fillna("").astype(str)):
                (tdiffs if c in TIME_COLS else diffs).append(f"{c}: khác chuỗi")
    if not diffs and not tdiffs:
        return "GIỐNG SỐ LIỆU (khác định dạng)", ""
    if not diffs:
        return "CHỈ KHÁC CỘT THỜI GIAN", "; ".join(tdiffs)
    return "KHÁC SỐ LIỆU", "; ".join(diffs) + (" | thời gian: " + "; ".join(tdiffs) if tdiffs else "")


def compare_parquet(a: Path, b: Path):
    da, db = pd.read_parquet(a), pd.read_parquet(b)
    if list(da.columns) != list(db.columns):
        return "KHÁC CỘT", f"{list(da.columns)} so với {list(db.columns)}"
    if len(da) != len(db):
        return "KHÁC SỐ DÒNG", f"{len(da)} so với {len(db)}"
    sort_cols = [c for c in da.columns if not pd.api.types.is_numeric_dtype(da[c]) or c.endswith("_id") or c == "cluster"]
    notes = []
    for c in da.columns:
        if pd.api.types.is_numeric_dtype(da[c]) and not c.endswith("_id"):
            sa, sb = float(da[c].sum()), float(db[c].sum())
            if not np.isclose(sa, sb, rtol=1e-9, atol=1e-9):
                notes.append(f"tổng {c}: {sa:.8g} so với {sb:.8g}")
    return ("GIỐNG (số dòng, cột, tổng cột số)" if not notes else "KHÁC TỔNG CỘT SỐ"), "; ".join(notes)


def main():
    main_dir, copy_dir = Path(sys.argv[1]), Path(sys.argv[2])
    rows = []
    for sub, pattern in [("results", "**/*.csv"), ("reports/evidence", "*.csv"), ("app/data", "**/*.csv")]:
        for a in sorted((main_dir / sub).glob(pattern)):
            rel = a.relative_to(main_dir)
            b = copy_dir / rel
            if not b.exists():
                rows.append((str(rel).replace("\\", "/"), "THIẾU Ở BẢN SAO", ""))
                continue
            rows.append((str(rel).replace("\\", "/"),) + compare_csv(a, b))
    for a in sorted((main_dir / "app/data").glob("*.parquet")):
        rel = a.relative_to(main_dir)
        b = copy_dir / rel
        if not b.exists():
            rows.append((str(rel).replace("\\", "/"), "THIẾU Ở BẢN SAO", ""))
            continue
        rows.append((str(rel).replace("\\", "/"),) + compare_parquet(a, b))
    width = max(len(r[0]) for r in rows)
    for r in rows:
        print(f"{r[0]:<{width}} | {r[1]} | {r[2]}")
    counts = pd.Series([r[1] for r in rows]).value_counts()
    print("\nTổng hợp:")
    for k, v in counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
