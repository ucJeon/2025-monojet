"""
plot/build_plane.py
-------------------
lam1 x lam2 signal yield plane 생성 및 보간.
"""

import numpy as np
import pandas as pd
from scipy.interpolate import griddata

# ============================================================
# USER CONFIG  ← 여기서 조절
# ============================================================

INTERP_FACTOR  = 100      # 보간 배율 (원래 grid 대비 몇 배 촘촘하게 할지)
                          # 예: 15개 lam1 포인트 → 15*10 = 150 포인트
INTERP_METHOD  = "linear" # "linear" | "cubic" | "nearest"

LAM1_LIST = [
    "0-03","0-05","0-07","0-08","0-1","0-15",
    "0-2","0-3","0-4","0-5","0-6","0-7","0-8","0-9","1-0",
]
LAM2_LIST = [
    "0-04","0-06","0-08","0-1","0-15",
    "0-2","0-3","0-4","0-5","0-6","0-7","0-8","0-9","1-0",
]

# ============================================================


def lam_to_float(v: str) -> float:
    return float(v.replace("-", "."))


def get_signal_value(df: pd.DataFrame, mx1: str, lam1: str, lam2: str,
                     col: str = "sg after", default: float = np.nan) -> float:
    key = f"Signal_{mx1}_{lam1}_{lam2}.0"
    s   = df.loc[df["signal"].eq(key), col]
    return float(s.iat[0]) if len(s) else default


def build_plane(df: pd.DataFrame, mx1: str,
                lam1_list=None, lam2_list=None,
                col: str = "sg after") -> pd.DataFrame:
    """
    index  = lam2 (str), columns = lam1 (str) 인 signal yield plane 반환.
    """
    if lam1_list is None:
        lam1_list = LAM1_LIST
    if lam2_list is None:
        lam2_list = LAM2_LIST

    plane = pd.DataFrame(index=lam2_list, columns=lam1_list, dtype=float)
    for lam1 in lam1_list:
        for lam2 in lam2_list:
            plane.loc[lam2, lam1] = get_signal_value(df, mx1, lam1, lam2, col=col)
    return plane


def interpolate_plane(plane: pd.DataFrame,
                      factor: int = None,
                      method: str = None) -> pd.DataFrame:
    """
    plane(index=lam2 str, columns=lam1 str) 을 factor 배 촘촘하게 보간한다.
    반환 DataFrame: index=lam2(float), columns=lam1(float)
    """
    if factor is None:
        factor = INTERP_FACTOR
    if method is None:
        method = INTERP_METHOD

    x = np.array([lam_to_float(v) for v in plane.columns], dtype=float)  # lam1
    y = np.array([lam_to_float(v) for v in plane.index],   dtype=float)  # lam2
    X, Y = np.meshgrid(x, y)
    Z    = plane.to_numpy(dtype=float)
    mask = np.isfinite(Z)

    xi = np.linspace(x.min(), x.max(), len(x) * factor)
    yi = np.linspace(y.min(), y.max(), len(y) * factor)
    XI, YI = np.meshgrid(xi, yi)

    pts  = np.column_stack([X[mask], Y[mask]])
    vals = Z[mask]

    ZI = griddata(pts, vals, (XI, YI), method=method)

    return pd.DataFrame(ZI, index=yi, columns=xi)
