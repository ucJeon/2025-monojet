version_list=(
#  v2
  v21
)

mx1_list=(
  1-0
  1-5
  2-0
  2-5
)

ntree_list=(
#  1500
#  2000
  2500
)

md_list=(
  4
)

for version in "${version_list[@]}"; do
  for mx1 in "${mx1_list[@]}"; do
    for ntree in "${ntree_list[@]}"; do
      for md in "${md_list[@]}"; do

        python OutputCheck.py \
          --mode single \
          --mx1 "$mx1" \
          --ntree "$ntree" \
          --maxdepth "$md" \
          --output ./out \
          --no-scatter \
          --version "$version"

      done
    done
  done
done

