#!/bin/sh
target_event=$1
delphe_card=$2
pythia8MC=$3
output=$4
procID=$5
Delphes_path=$6

# export Delphes_HepMC3="${Delphes_path}/DelphesHepMC"
# Vertex error, It has different from dataformat
# export Delphes_HepMC3="${Delphes_path}/DelphesHepMC3"
export Delphes_HepMC3="${Delphes_path}/DelphesHepMC2"

${Delphes_HepMC3} ${delphe_card} output.root ${pythia8MC}
