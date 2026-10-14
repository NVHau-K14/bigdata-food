"""
scratch/plot_p7.py
------------------
Vẽ bộ biểu đồ trực quan nghiệm thu cho Giai đoạn P7:
1. reports/figures/model_comparison_rmse_mae.png
2. reports/figures/model_comparison_ranking.png
3. reports/figures/als_rmse_breakdown.png
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
comp_path = PROJECT_ROOT / "data" / "results" / "model_comparison.csv"
base_bk_path = PROJECT_ROOT / "data" / "results" / "baseline_rmse_breakdown.csv"
als_bk_path = PROJECT_ROOT / "data" / "results" / "als_rmse_breakdown.csv"
figures_dir = PROJECT_ROOT / "reports" / "figures"
figures_dir.mkdir(parents=True, exist_ok=True)

plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#CCCCCC'
plt.rcParams['axes.linewidth'] = 0.8

df_comp = pd.read_csv(comp_path)

# =========================================================================
# 1. BIỂU ĐỒ SO SÁNH RMSE VÀ MAE (MODEL COMPARISON)
# =========================================================================
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)

# Subplot 1: Food.com
fc_df = df_comp[df_comp['dataset'] == 'food_com']
x = np.arange(len(fc_df))
width = 0.35

ax1 = axes[0]
b1 = ax1.bar(x - width/2, fc_df['RMSE'], width, label='RMSE', color='#2b5c8f', alpha=0.9)
b2 = ax1.bar(x + width/2, fc_df['MAE'], width, label='MAE', color='#e76f51', alpha=0.9)
ax1.set_title('Food.com: So sánh Sai số Dự đoán giữa Baseline & ALS (Test Set)', fontsize=11, fontweight='bold', pad=12)
ax1.set_ylabel('Sai số (Điểm đánh giá - sao)', fontsize=10)
ax1.set_xticks(x)
ax1.set_xticklabels(fc_df['model'], fontsize=9, rotation=15, ha='right')
ax1.legend(frameon=True, facecolor='#f8f9fa')
ax1.grid(axis='y', linestyle='--', alpha=0.5)
ax1.set_ylim(0, 0.85)

for bar in b1:
    h = bar.get_height()
    ax1.annotate(f'{h:.4f}', xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=8, fontweight='bold')
for bar in b2:
    h = bar.get_height()
    ax1.annotate(f'{h:.4f}', xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=8, fontweight='bold')

# Subplot 2: ViFoodRec
vf_df = df_comp[df_comp['dataset'] == 'food_vietnam']
x2 = np.arange(len(vf_df))

ax2 = axes[1]
b3 = ax2.bar(x2 - width/2, vf_df['RMSE'], width, label='RMSE', color='#2a9d8f', alpha=0.9)
b4 = ax2.bar(x2 + width/2, vf_df['MAE'], width, label='MAE', color='#f4a261', alpha=0.9)
ax2.set_title('ViFoodRec: So sánh Sai số Dự đoán giữa Baseline & ALS (Test Set)', fontsize=11, fontweight='bold', pad=12)
ax2.set_ylabel('Sai số (Điểm đánh giá - sao)', fontsize=10)
ax2.set_xticks(x2)
ax2.set_xticklabels(vf_df['model'], fontsize=9, rotation=15, ha='right')
ax2.legend(frameon=True, facecolor='#f8f9fa')
ax2.grid(axis='y', linestyle='--', alpha=0.5)
ax2.set_ylim(0, 1.6)

for bar in b3:
    h = bar.get_height()
    ax2.annotate(f'{h:.4f}', xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=8, fontweight='bold')
for bar in b4:
    h = bar.get_height()
    ax2.annotate(f'{h:.4f}', xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=8, fontweight='bold')

plt.tight_layout()
plt.savefig(figures_dir / "model_comparison_rmse_mae.png")
plt.close()
print("Saved model_comparison_rmse_mae.png")

# =========================================================================
# 2. BIỂU ĐỒ SO SÁNH CHỈ SỐ XẾP HẠNG (RANKING METRICS: P@10 & R@10)
# =========================================================================
fig, axes = plt.subplots(1, 2, figsize=(14, 5.2), dpi=300)

ax1 = axes[0]
bars_p1 = ax1.bar(x, fc_df['Precision@10'] * 100, width=0.5, color='#457b9d', alpha=0.9)
ax1.set_title('Food.com: Precision@10 (%) trên các mô hình', fontsize=11, fontweight='bold', pad=12)
ax1.set_ylabel('Precision@10 (%)', fontsize=10)
ax1.set_xticks(x)
ax1.set_xticklabels(fc_df['model'], fontsize=9, rotation=15, ha='right')
ax1.grid(axis='y', linestyle='--', alpha=0.5)
for bar in bars_p1:
    h = bar.get_height()
    ax1.annotate(f'{h:.3f}%', xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=8, fontweight='bold')

ax2 = axes[1]
bars_p2 = ax2.bar(x2, vf_df['Precision@10'] * 100, width=0.5, color='#e76f51', alpha=0.9)
ax2.set_title('ViFoodRec: Precision@10 (%) trên các mô hình', fontsize=11, fontweight='bold', pad=12)
ax2.set_ylabel('Precision@10 (%)', fontsize=10)
ax2.set_xticks(x2)
ax2.set_xticklabels(vf_df['model'], fontsize=9, rotation=15, ha='right')
ax2.grid(axis='y', linestyle='--', alpha=0.5)
for bar in bars_p2:
    h = bar.get_height()
    ax2.annotate(f'{h:.3f}%', xy=(bar.get_x() + bar.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=8, fontweight='bold')

plt.tight_layout()
plt.savefig(figures_dir / "model_comparison_ranking.png")
plt.close()
print("Saved model_comparison_ranking.png")

# =========================================================================
# 3. BIỂU ĐỒ PHÂN RÃ RMSE THEO TỪNG MỨC ĐIỂM THẬT (BREAKDOWN)
# =========================================================================
df_base_bk = pd.read_csv(base_bk_path)
df_als_bk = pd.read_csv(als_bk_path)
df_all_bk = pd.concat([df_base_bk, df_als_bk], ignore_index=True)

fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)

# Food.com
fc_all = df_all_bk[df_all_bk['dataset'] == 'food_com']
ax3 = axes[0]
palette = {
    'Global Mean': '#8d99ae',
    'Smoothed Item Mean': '#2a9d8f',
    'Top-N Popular': '#f4a261',
    'ALS Matrix Factorization': '#e63946'
}
for model, grp in fc_all.groupby('model'):
    c = palette.get(model, '#333333')
    lw = 2.5 if 'ALS' in model else 1.5
    ls = '-' if 'ALS' in model else '--'
    ax3.plot(grp['rating_level'], grp['rmse'], marker='o', linewidth=lw, linestyle=ls, label=model, color=c)

ax3.set_title('Food.com: ALS Giảm Sai số Vượt trội tại Mức 1-4 Sao', fontsize=11, fontweight='bold', pad=12)
ax3.set_xlabel('Mức điểm thật (Rating 1.0 - 5.0 sao)', fontsize=10)
ax3.set_ylabel('RMSE tại từng mức điểm (sao)', fontsize=10)
ax3.legend(frameon=True, facecolor='#f8f9fa', fontsize=9)
ax3.grid(True, linestyle='--', alpha=0.5)

# ViFoodRec
vf_all = df_all_bk[df_all_bk['dataset'] == 'food_vietnam']
ax4 = axes[1]
for model, grp in vf_all.groupby('model'):
    c = palette.get(model, '#333333')
    lw = 2.5 if 'ALS' in model else 1.5
    ls = '-' if 'ALS' in model else '--'
    ax4.plot(grp['rating_level'], grp['rmse'], marker='s', linewidth=lw, linestyle=ls, label=model, color=c)

ax4.set_title('ViFoodRec: Phân rã RMSE Chữ V Đối xứng quanh 3.0 Sao', fontsize=11, fontweight='bold', pad=12)
ax4.set_xlabel('Mức điểm thật (Rating 1.0 - 5.0 sao)', fontsize=10)
ax4.set_ylabel('RMSE tại từng mức điểm (sao)', fontsize=10)
ax4.legend(frameon=True, facecolor='#f8f9fa', fontsize=9)
ax4.grid(True, linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig(figures_dir / "als_rmse_breakdown.png")
plt.close()
print("Saved als_rmse_breakdown.png")
