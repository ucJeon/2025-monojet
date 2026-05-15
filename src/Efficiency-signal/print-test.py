import pandas as pd
import numpy  as np
import os
import re

bdt_cut_1p0 = 0.1050
bdt_cut_1p5 = 0.1350
bdt_cut_2p0 = 0.1440
bdt_cut_2p5 = 0.1520

df = pd.read_csv("efficiency.csv")
df = df.set_index(["mx1", "lam1", "lam2", "bdt_cut"])

# 이제 아래처럼 접근 
eff_1p0 = df.loc[(1.0, 0.1, 0.1, bdt_cut_1p0), "eff_gb"]
eff_1p5 = df.loc[(1.5, 0.1, 0.1, bdt_cut_1p5), "eff_gb"]
eff_2p0 = df.loc[(2.0, 0.1, 0.1, bdt_cut_2p0), "eff_gb"]
eff_2p5 = df.loc[(2.5, 0.1, 0.1, bdt_cut_2p5), "eff_gb"]

print(eff_1p0, eff_1p5, eff_2p0, eff_2p5)
