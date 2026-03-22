MX1_list=("1-0" "1-5" "2-0" "2-5")
OUT_DIR="./plots"
  
for MX1 in "${MX1_list[@]}"; do
  BKG_INDICES=(1 2)   # ttbar ~ zz4l
  for idx in "${BKG_INDICES[@]}"; do
   
      echo "=== index=${idx}, mode=whole ==="
      printf "%s\n%s\n%s\n" "$idx" "$MX1" "1" | python3 main.py
   
      echo "=== index=${idx}, mode=subsample ==="
      printf "%s\n%s\n%s\n" "$idx" "$MX1" "2" | python3 main.py
   
  done
  mv ./plots ./plots_${MX1}
done
