"""
plot_bdt.py
-----------
bkg sample별 BDT response를 PNG로 저장하는 함수.
"""

import numpy as np
import matplotlib.pyplot as plt
import mplhep as hep
from pathlib import Path

plt.style.use(hep.style.CMS)


def th1_to_numpy(h):
    """ROOT TH1F → (edges, values, errors)"""
    n      = h.GetNbinsX()
    edges  = np.array([h.GetBinLowEdge(b) for b in range(1, n + 2)])
    values = np.array([h.GetBinContent(b)  for b in range(1, n + 1)])
    errors = np.array([h.GetBinError(b)    for b in range(1, n + 1)])
    return edges, values, errors


def plot_bdt_each_bkg(bkg_hists: dict,
                      out_dir  : str   = "./plots",
                      lumi     : float = 300.0):
    """
    bkg_hists의 각 sample을 개별 PNG로 저장한다.

    Parameters
    ----------
    bkg_hists : dict  {label -> ROOT.TH1F}
    out_dir   : 저장 디렉터리
    lumi      : luminosity (fb^-1)
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    for label, h in bkg_hists.items():
        edges, values, errors = th1_to_numpy(h)

        total_yield = values.sum()

        fig, ax = plt.subplots(figsize=(12, 10))

        hep.histplot(values, edges, yerr=errors,
                     histtype="fill", alpha=0.5,
                     label=f"{label}  ({total_yield:.2f})", ax=ax)

        ax.set_xlabel("BDT response")
        ax.set_ylabel("Events / bin")
        ax.set_xlim(-0.5, +0.5)
        # ax.set_yscale("log")
        ax.legend()
        hep.cms.label(data=False,
                      lumi=f"{lumi}", ax=ax)

        out_path = f"{out_dir}/{label}_bdt.png"
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  [저장] {out_path}")

