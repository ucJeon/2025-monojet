import pandas as pd

OPTIMAL_CUTS = {1.0: 0.105, 1.5: 0.135, 2.0: 0.144, 2.5: 0.152}
MODEL = "v2_2500_4"

df = pd.read_csv("efficiency.csv")

print(f"{'MX1':>5}  {'cut':>6}  {'mean':>8}  {'std':>8}  {'min':>8}  {'max':>8}  {'(max-min)/mean':>15}")
print("-" * 70)
for mx1, cut in OPTIMAL_CUTS.items():
    sub = df[(df.model == MODEL) & (df.mx1 == mx1) & (df.bdt_cut == cut)]["eff_gb"]
    mean = sub.mean()
    print(f"{mx1:>5.1f}  {cut:>6.3f}  {mean:>8.4f}  {sub.std():>8.4f}  {sub.min():>8.4f}  {sub.max():>8.4f}  {(sub.max()-sub.min())/mean*100:>13.1f}%")
