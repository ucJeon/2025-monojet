import argparse
import subprocess
import sys
import os
from condoop import copyFileToHDFS

for i in [2,3,4]:
    output_name=f"/user/ujeon/monojet/mc/v1.0.0/Signal_2-5_0-3_2-0.0.{i}.root"
    copyFileToHDFS(f"prom{i}.root", output_name)
    print(output_name)
