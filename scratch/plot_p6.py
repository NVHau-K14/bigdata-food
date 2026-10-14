"""
scratch/plot_p6.py
------------------
Vẽ biểu đồ kết quả mô hình Baseline (P6):
1. reports/figures/baseline_performance.png (So sánh RMSE, MAE giữa 3 mô hình Baseline)
2. reports/figures/baseline_rmse_breakdown.png (Phân rã RMSE theo từng mức điểm thật 1-5 sao)
"""

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
metrics_path = PROJECT_ROOT / "data" / "results" / "baseline_metrics.csv"
breakdown_path = PROJECT_ROOT / "data" / "results" / "baseline_rmse_breakdown.csv"
figures_dir = PROJECT_ROOT / "reports" / "figures"
figures_dir.mkdir(parents=True, exist_ok=True)

plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['axes.edgecolor'] = '#CCCCCC'
plt.rcParams['axes.linewidth'] = 0.8

# 1. Biểu đồ so sánh Baseline Metrics
df_metrics = pd.read_csv(metrics_path)

fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)

colors = ['#4A90E2', '#50E3C2', '#F5A623']

# Subplot 1: Food.com
fc_df = df_metrics[df_metrics['dataset'] == 'food_com']
x = np.arange(len(fc_df))
width = 0.35

ax1 = axes[0]
bars1 = ax1.bar(x - width/2, fc_df['RMSE'], width, label='RMSE', color='#2b5c8f', alpha=0.9)
bars2 = ax1.bar(x + width/2, fc_df['MAE'], width, label='MAE', color='#e76f51', alpha=0.9)
ax1.set_title('Food.com: Sai số Dự đoán của 3 Mô hình Baseline (Test set)', fontsize=12, fontweight='bold', pad=12)
ax1.set_ylabel('Sai số (Điểm đánh giá - sao)', fontsize=11)
ax1.set_xticks(x)
ax1.set_xticklabels(fc_df['model'], fontsize=10)
ax1.legend(frameon=True, facecolor='#f8f9fa')
ax1.grid(axis='y', linestyle='--', alpha=0.5)
ax1.set_ylim(0, 0.85)

for b in bars1:
    h = b.get_height()
    ax1.annotate(f'{h:.4f}', xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')
for b in bars2:
    h = b.get_height()
    ax1.annotate(f'{h:.4f}', xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')

# Subplot 2: ViFoodRec
vf_df = df_metrics[df_metrics['dataset'] == 'food_vietnam']
x2 = np.arange(len(vf_df))

ax2 = axes[1]
bars3 = ax2.bar(x2 - width/2, vf_df['RMSE'], width, label='RMSE', color='#2a9d8f', alpha=0.9)
bars4 = ax2.bar(x2 + width/2, vf_df['MAE'], width, label='MAE', color='#f4a261', alpha=0.9)
ax2.set_title('ViFoodRec: Sai số Dự đoán của 3 Mô hình Baseline (Test set)', fontsize=12, fontweight='bold', pad=12)
ax2.set_ylabel('Sai số (Điểm đánh giá - sao)', fontsize=11)
ax2.set_xticks(x2)
ax2.set_xticklabels(vf_df['model'], fontsize=10)
ax2.legend(frameon=True, facecolor='#f8f9fa')
ax2.grid(axis='y', linestyle='--', alpha=0.5)
ax2.set_ylim(0, 1.6)

for b in bars3:
    h = b.get_height()
    ax2.annotate(f'{h:.4f}', xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')
for b in bars4:
    h = b.get_height()
    ax2.annotate(f'{h:.4f}', xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3),
                 textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(figures_dir / "baseline_performance.png")
plt.close()
print("Saved baseline_performance.png")

# 2. Biểu đồ RMSE Breakdown theo từng mức điểm thật
df_breakdown = pd.read_csv(breakdown_path)

fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)

# Food.com breakdown
fc_b = df_breakdown[df_breakdown['dataset'] == 'food_com']
ax3 = axes[0]
for model, grp in fc_b.groupby('model'):
    ax3.plot(grp['rating_level'], grp['rmse'], marker='o', linewidth=2, label=model)
ax3.set_title('Food.com: Phân rã RMSE theo Mức Điểm Thực tế', fontsize=12, fontweight='bold', pad=12)
ax3.set_xlabel('Mức điểm thật (Rating 1.0 - 5.0 sao)', fontsize=11)
ax3.set_ylabel('RMSE tại từng mức điểm (sao)', fontsize=11)
ax3.legend(frameon=True, facecolor='#f8f9fa')
ax3.grid(True, linestyle='--', alpha=0.5)

# ViFoodRec breakdown
vf_b = df_breakdown[df_breakdown['dataset'] == 'food_vietnam']
ax4 = axes[1]
for model, grp in vf_b.groupby('model'):
    ax4.plot(grp['rating_level'], grp['rmse'], marker='s', linewidth=2, label=model)
ax4.set_title('ViFoodRec: Phân rã RMSE theo Mức Điểm Thực tế (Chữ V đối xứng)', fontsize=12, fontweight='bold', pad=12)
ax4.set_xlabel('Mức điểm thật (Rating 1.0 - 5.0 sao)', fontsize=11)
ax4.set_ylabel('RMSE tại từng mức điểm (sao)', fontsize=11)
ax4.legend(frameon=True, facecolor='#f8f9fa')
ax4.grid(True, linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig(figures_dir / "baseline_rmse_breakdown.png")
plt.close()
print("Saved baseline_rmse_breakdown.png")
