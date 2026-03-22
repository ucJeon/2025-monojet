import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

shade = {
    "1.0 TeV": {"x1": 0.05,  "y1": 0.07,  "c": "cornflowerblue"},
    "1.5 TeV": {"x1": 0.04,  "y1": 0.057, "c": "y"},
    "2.0 TeV": {"x1": 0.035, "y1": 0.05,  "c": "coral"},
    "2.5 TeV": {"x1": 0.031, "y1": 0.044, "c": "#8B0000"},
}

fig, ax = plt.subplots()

ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(0.03, 1.0); ax.set_ylim(0.05, 1.0)
ax.set_xlabel(r"$\lambda_{1}$"); ax.set_ylabel(r"$\lambda_{2}$")
ax.set_xticks([0.1, 0.3, 0.5, 0.7, 1.0])
ax.set_yticks([0.1, 0.3, 0.5, 0.7, 1.0])
ax.minorticks_off()

xmin, xmax = ax.get_xlim()
ymin, ymax = ax.get_ylim()

# 겹침(=교집합) 없이 union 영역을 칠하기:
#  - (x<x1) 전체를 먼저 칠하고
#  - (y<y1) 은 x>=x1 구간만 칠해서 overlap 제거
for label, v in shade.items():
    x1, y1, c = v["x1"], v["y1"], v["c"]
    ax.fill_between([xmin, x1], ymin, ymax, color=c, alpha=0.18, zorder=0)   # x < x1
    ax.fill_between([x1,  xmax], ymin, y1,  color=c, alpha=0.18, zorder=0)   # y < y1 AND x >= x1 (overlap 제거)

# legend에 (lam1, lam2) threshold 값 표시
proxy = []
labels = []
for label, v in shade.items():
    proxy.append(Line2D([0],[0], color=v["c"], lw=6))
    labels.append(f"{label}\n" + rf"$\lambda_1<{v['x1']}$, $\lambda_2<{v['y1']}$")

ax.legend(proxy, labels, frameon=False, loc="best", handlelength=1.6)

plt.tight_layout()
plt.savefig("temp.png")


"""
import matplotlib.pyplot as plt

# mass point별 (x1, y1) and color
shade = {
    "1.0 TeV": {"x1": 0.05,  "y1": 0.07,  "c": "cornflowerblue"},
    "1.5 TeV": {"x1": 0.04,  "y1": 0.057, "c": "y"},
    "2.0 TeV": {"x1": 0.035, "y1": 0.05,  "c": "coral"},
    "2.5 TeV": {"x1": 0.031, "y1": 0.044, "c": "#8B0000"},
}

fig, ax = plt.subplots()

# axes style (원하는 스타일 최소만)
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(0.03, 1.0); ax.set_ylim(0.05, 1.0)
ax.set_xlabel(r"$\lambda_{1}$"); ax.set_ylabel(r"$\lambda_{2}$")
ax.set_xticks([0.1, 0.3, 0.5, 0.7, 1.0])
ax.set_yticks([0.1, 0.3, 0.5, 0.7, 1.0])
ax.minorticks_off()

xmin, xmax = ax.get_xlim()
ymin, ymax = ax.get_ylim()

# (x <= x1) OR (y < y1) 영역을 각 mass point 색으로 칠하기
for label, v in shade.items():
    x1, y1, c = v["x1"], v["y1"], v["c"]
    ax.fill_between([xmin, x1], ymin, ymax, color=c, alpha=0.18, zorder=0)  # x<x1
    ax.fill_between([xmin, xmax], ymin, y1,  color=c, alpha=0.18, zorder=0)  # y<y1

# legend용 proxy
from matplotlib.lines import Line2D
proxy = [Line2D([0],[0], color=v["c"], lw=6) for v in shade.values()]
ax.legend(proxy, list(shade.keys()), frameon=False, loc="best")

plt.tight_layout()
plt.savefig("temp.png")

"""
