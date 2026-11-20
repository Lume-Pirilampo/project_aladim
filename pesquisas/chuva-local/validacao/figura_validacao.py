"""Gera a figura vetorial a partir das duas tabelas publicadas."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False,
                     "axes.spines.right": False, "axes.labelcolor": "#242a32",
                     "xtick.color": "#46505d", "ytick.color": "#46505d",
                     "svg.fonttype": "path", "svg.hashsalt": "project-aladim-rain-2026"})
LIMITS = Path("limites-fixos.csv")
DENSITY = Path("densidade-resumo.csv")
limits = pd.read_csv(LIMITS)
density = pd.read_csv(DENSITY)
colors = {"suecia": "#176c8a", "italia_2021": "#925339", "italia_2022": "#b37719"}
labels = {"suecia": "Suécia · ago. 2015", "italia_2021": "Itália · verão 2021",
          "italia_2022": "Itália · verão 2022"}
fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.45), layout="constrained")
ax, support = axes
ax.axhline(0, linewidth=.8, color="#727981", linestyle="--", zorder=0)
for name, group in limits.groupby("recorte", sort=False):
    x = np.arange(len(group))
    delta = group["eam_5"] - float(group.loc[group["limite_mm_h"] == 10, "eam_5"].iloc[0])
    ax.plot(x, delta, label=labels[name], color=colors[name],
            marker="o", markersize=4, linewidth=1.7)
ax.set_xticks([0, 2, 4, 6, 7, 8, 9, 10], ["2", "5", "10", "15", "20", "30", "50", "Sem\nfiltro"])
ax.set_xlabel("Limites fixos avaliados (mm/h)")
ax.set_ylabel("Diferença de erro médio frente a 10 mm/h (mm)")
ax.set_title("Erro nas horas com pelo menos 5 mm", fontsize=11, loc="left", fontweight="bold")
ax.legend(loc="upper right", frameon=False, fontsize=8)
ax.grid(axis="y", linewidth=.55, alpha=.28)
for network, group in density.loc[density["metodo"] == "fixo_10"].groupby("recorte"):
    group = group.sort_values("fracao")
    color = colors["suecia" if network == "SE" else "italia_2022"]
    label = "Suécia" if network == "SE" else "Itália 2022"
    support.plot(100 * group["fracao"], 100 * group["suporte_local_mediano"],
                 label=label, color=color, marker="o", markersize=4, linewidth=1.7)
support.set_xticks([10, 25, 50, 75, 100])
support.set_ylim(-3, 103)
support.set_yticks([0, 25, 50, 75, 100])
support.set_xlabel("Enlaces mantidos na rede (%)")
support.set_ylabel("Pares hora–enlace com suporte local (%)")
support.set_title("Pelo menos 8 outros enlaces válidos em 10 km", fontsize=11, loc="left", fontweight="bold")
support.legend(loc="center right", frameon=False, fontsize=8)
support.grid(axis="y", linewidth=.55, alpha=.28)
fig.savefig("limites-e-densidade.svg", metadata={
    "Date": None, "Title": "Chuva intensa, limites fixos e densidade dos enlaces",
    "Description": "À esquerda, diferença no erro médio em três recortes. À direita, o suporte local por fração de enlaces."
})
