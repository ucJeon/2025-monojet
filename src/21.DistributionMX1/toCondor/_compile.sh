DELPHES_DIR=/users/ujeon/2025-monojet/condor/3.DelphesStep/analyzer/delphes

g++ -std=c++17 main.cc -o monojetMX1massDitribution \
  `root-config --cflags` \
  -I${DELPHES_DIR} \
  -I${DELPHES_DIR}/external/ExRootAnalysis \
  `root-config --libs` \
  ${DELPHES_DIR}/libDelphes.so \
  -Wl,-rpath,${DELPHES_DIR}
