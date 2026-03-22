#include <TH2.h>
#include <TStyle.h>
#include <TCanvas.h>
#include <iostream>
#include <cstdlib>
#include <TParticle.h>
#include <TLorentzVector.h>
#include <TChain.h>
#include <vector>
#include "TClonesArray.h"
#include <filesystem>

#include <TFile.h>   // 추가
#include <TTree.h>   // 추가

// Delphes 헤더 (경로는 본인 설치 위치에 맞게)
#include "/users/ujeon/2025-monojet/condor/3.DelphesStep/analyzer/delphes/classes/DelphesClasses.h"
#include "/users/ujeon/2025-monojet/condor/3.DelphesStep/analyzer/delphes/external/ExRootAnalysis/ExRootTreeReader.h"
// ExRootResult 안 쓰면 생략 가능
// #include "/users/ujeon/2025-monojet/condor/3.DelphesStep/analyzer/delphes/external/ExRootAnalysis/ExRootResult.h"


using namespace std;

vector<GenParticle*> x1Selection(TClonesArray* branchParticle){
    Int_t nParticle = branchParticle->GetEntries();
    vector<GenParticle*> x1s;
    for (Int_t i=0; i<nParticle; ++i){
        auto x1 = dynamic_cast<GenParticle*>(branchParticle->At(i));
        if (!x1) continue;
        if (abs(x1->PID) != 6000001) continue;
        if (x1->Status != 62) continue;
        x1s.push_back(x1);
    }
    return x1s;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <root_file_path>" << std::endl;
        return 1;
    }

    std::string inputPath = argv[1];
    std::string outputPath = "output.root";

    TChain chain("Delphes");
    chain.Add(inputPath.c_str());

    ExRootTreeReader *treeReader = new ExRootTreeReader(&chain);
    Long64_t nEntries = treeReader->GetEntries();

    TClonesArray *branchParticle = treeReader->UseBranch("Particle");

    // Output file and tree
    TFile *file = new TFile(outputPath.c_str(), "RECREATE");
    TTree *tree = new TTree("events", "Tree with x1 mass info");

    float x1_mass = -999.;
    tree->Branch("mx1mass", &x1_mass, "mx1mass/F");

    // Event loop
    for (Long64_t entry = 0; entry < nEntries; ++entry){
        treeReader->ReadEntry(entry);

        auto x1_vec = x1Selection(branchParticle);
        if (x1_vec.size() > 0) {
            x1_mass = x1_vec[0]->Mass;
            tree->Fill();
        }
    }

    file->cd();
    tree->Write();
    file->Close();

    std::cout << "[Done] File saved as " << outputPath << std::endl;
    return 0;
}
