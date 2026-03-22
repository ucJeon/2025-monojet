export LD_LIBRARY_PATH=/users/ujeon/2025-monojet/condor/3.DelphesStep/analyzer/delphes:$LD_LIBRARY_PATH

g++ -o main main.cc `root-config --cflags --libs` \
    -I/users/ujeon/2025-monojet/condor/3.DelphesStep/analyzer/delphes \
    -L/users/ujeon/2025-monojet/condor/3.DelphesStep/analyzer/delphes \
    -lDelphes -std=c++17
    # -lDelphes -lstdc++fs -std=c++17
