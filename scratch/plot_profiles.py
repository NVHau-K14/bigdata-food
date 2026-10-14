"""
scratch/plot_profiles.py
------------------------
Vẽ biểu đồ cột hồ sơ cụm (Cluster Profiles Bar Charts) cho P8:
1. reports/figures/kmeans_cluster_profiles_foodcom.png
2. reports/figures/kmeans_cluster_profiles_vifood.png
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
fc_path = PROJECT_ROOT / "data" / "results" / "cluster_profiles_food_com.csv"
vf_path = PROJECT_ROOT / "data" / "results" / "food_cluster_profiles_vietnam.csv"
figures_dir = PROJECT_ROOT / "reports" / "figures"

plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#CCCCCC'
plt.rcParams['axes.linewidth'] = 0.8

# 1. Food.com Cluster Profiles
df_fc = pd.read_csv(fc_path)
df_fc_clusters = df_fc[df_fc['cluster'] >= 0]

fig, axes = plt.subplots(2, 2, figsize=(14, 9), dpi=300)

# Subplot 1: Điểm TB và Lượt đánh giá
ax1 = axes[0, 0]
x = np.arange(len(df_fc_clusters))
bars1 = ax1.bar(x, df_fc_clusters['avg_rating'], color='#2b5c8f', width=0.5, alpha=0.9)
ax1.set_title('Điểm Đánh Giá Trung Bình (sao)', fontsize=11, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels([f"Cụm {r['cluster']}\n({r['user_pct']}%)" for _, r in df_fc_clusters.iterrows()], fontsize=9)
ax1.set_ylim(0, 5.5)
ax1.grid(axis='y', linestyle='--', alpha=0.5)
for b in bars1:
    h = b.get_height()
    ax1.annotate(f'{h:.2f}⭐', xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')

# Subplot 2: Lượt đánh giá TB
ax2 = axes[0, 1]
bars2 = ax2.bar(x, df_fc_clusters['n_ratings'], color='#e76f51', width=0.5, alpha=0.9)
ax2.set_title('Số Lượt Đánh Giá Trung Bình / User', fontsize=11, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels([f"Cụm {r['cluster']}\n({r['user_pct']}%)" for _, r in df_fc_clusters.iterrows()], fontsize=9)
ax2.grid(axis='y', linestyle='--', alpha=0.5)
for b in bars2:
    h = b.get_height()
    ax2.annotate(f'{h:.1f}', xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')

# Subplot 3: Thời gian nấu TB
ax3 = axes[1, 0]
bars3 = ax3.bar(x, df_fc_clusters['avg_minutes'], color='#2a9d8f', width=0.5, alpha=0.9)
ax3.set_title('Thời Gian Nấu Trung Bình của Món (phút)', fontsize=11, fontweight='bold')
ax3.set_xticks(x)
ax3.set_xticklabels([f"Cụm {r['cluster']}\n({r['user_pct']}%)" for _, r in df_fc_clusters.iterrows()], fontsize=9)
ax3.grid(axis='y', linestyle='--', alpha=0.5)
for b in bars3:
    h = b.get_height()
    ax3.annotate(f'{h:.1f}p', xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')

# Subplot 4: Lượng Calo TB
ax4 = axes[1, 1]
bars4 = ax4.bar(x, df_fc_clusters['avg_calories'], color='#f4a261', width=0.5, alpha=0.9)
ax4.set_title('Lượng Calo Trung Bình của Món (kcal)', fontsize=11, fontweight='bold')
ax4.set_xticks(x)
ax4.set_xticklabels([f"Cụm {r['cluster']}\n({r['user_pct']}%)" for _, r in df_fc_clusters.iterrows()], fontsize=9)
ax4.grid(axis='y', linestyle='--', alpha=0.5)
for b in bars4:
    h = b.get_height()
    ax4.annotate(f'{h:.0f}', xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.suptitle('Hồ sơ Định lượng 4 Cụm Người dùng Food.com (K-means k=4)', fontsize=13, fontweight='bold', y=0.98)
plt.tight_layout()
plt.savefig(figures_dir / "kmeans_cluster_profiles_foodcom.png")
plt.close()
print("Saved kmeans_cluster_profiles_foodcom.png")

# 2. ViFoodRec Food Profiles
df_vf = pd.read_csv(vf_path)
df_vf_clusters = df_vf[df_vf['cluster'] >= 0]

fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), dpi=300)
x2 = np.arange(len(df_vf_clusters))

# Calo
ax1 = axes[0]
bars_c = ax1.bar(x2, df_vf_clusters['calories'], color='#e76f51', width=0.5, alpha=0.9)
ax1.set_title('Calo Trung Bình (kcal)', fontsize=11, fontweight='bold')
ax1.set_xticks(x2)
ax1.set_xticklabels([f"Cụm {r['cluster']}\n({r['food_pct']}%)" for _, r in df_vf_clusters.iterrows()], fontsize=9)
ax1.grid(axis='y', linestyle='--', alpha=0.5)
for b in bars_c:
    h = b.get_height()
    ax1.annotate(f'{h:.1f}', xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')

# Sugar & Protein
ax2 = axes[1]
w = 0.35
bars_s = ax2.bar(x2 - w/2, df_vf_clusters['sugar'], w, label='Đường (g)', color='#e9c46a', alpha=0.9)
bars_p = ax2.bar(x2 + w/2, df_vf_clusters['protein'], w, label='Đạm (g)', color='#2a9d8f', alpha=0.9)
ax2.set_title('Hàm lượng Đường & Chất Đạm (g)', fontsize=11, fontweight='bold')
ax2.set_xticks(x2)
ax2.set_xticklabels([f"Cụm {r['cluster']}\n({r['food_pct']}%)" for _, r in df_vf_clusters.iterrows()], fontsize=9)
ax2.legend(frameon=True, facecolor="#f8f9fa")
ax2.grid(axis='y', linestyle='--', alpha=0.5)

# Tỷ lệ món mặn
ax3 = axes[2]
bars_m = ax3.bar(x2, df_vf_clusters['is_savory'] * 100, color='#264653', width=0.5, alpha=0.9)
ax3.set_title('Tỷ lệ Món Mặn (%) [Cụm 2 = 0% Chay]', fontsize=11, fontweight='bold')
ax3.set_xticks(x2)
ax3.set_xticklabels([f"Cụm {r['cluster']}\n({r['food_pct']}%)" for _, r in df_vf_clusters.iterrows()], fontsize=9)
ax3.grid(axis='y', linestyle='--', alpha=0.5)
ax3.set_ylim(0, 115)
for b in bars_m:
    h = b.get_height()
    ax3.annotate(f'{h:.1f}%', xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.suptitle('Hồ sơ Định lượng 4 Cụm Món ăn ViFoodRec (K-means k=4)', fontsize=13, fontweight='bold', y=0.98)
plt.tight_layout()
plt.savefig(figures_dir / "kmeans_cluster_profiles_vifood.png")
plt.close()
print("Saved kmeans_cluster_profiles_vifood.png")
