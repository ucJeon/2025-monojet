for sample in zz4l ww2l2v wz3l1v; do
    echo -n "${sample}.0: "
    hdfs dfs -ls /user/ujeon/monojet/HepMC/v1.1.0/${sample}.0.*.hepmc.gz 2>/dev/null \
        | awk '{print $NF}' \
        | grep -oP "(?<=${sample}\.0\.)\d+(?=\.hepmc\.gz)" \
        | sort -n | tail -1
done

for sample in wwlv2q wz2l2q wzlv2q; do
    for idx in 1 2 3 4 5 6 7; do
        echo -n "${sample}.${idx}: "
        hdfs dfs -ls /user/ujeon/monojet/HepMC/v1.1.0/${sample}.${idx}.*.hepmc.gz 2>/dev/null \
            | awk '{print $NF}' \
            | grep -oP "(?<=${sample}\.${idx}\.)\d+(?=\.hepmc\.gz)" \
            | sort -n | tail -1
    done
done
