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
#include <TFile.h>
#include <TTree.h>
#include <cmath>
#include <TROOT.h> // Required for gInterpreter

int main(int argc, char *argv[]) {
    // Check for correct command line arguments
    if (argc < 3) {
        std::cerr << "Usage: " << argv[0] << " <input.root> <output.root>" << std::endl;
        return 1;
    }

    std::string inputFilePath = argv[1];
    std::string outputFilePath = argv[2];

    // Generate dictionary for vector<TLorentzVector> to allow reading/writing
    gInterpreter->GenerateDictionary("vector<TLorentzVector>", "TLorentzVector.h;vector");

    // Input File Handling
    TFile *inputFile = TFile::Open(inputFilePath.c_str());
    if (!inputFile || inputFile->IsZombie()) {
        std::cerr << "Failed to open input file: " << inputFilePath << std::endl;
        return 1;
    }

    TTree *tree = (TTree*)inputFile->Get("events");
    if (!tree) {
        std::cerr << "Failed to find 'events' tree in input file: " << inputFilePath << std::endl;
        inputFile->Close();
        return 1;
    }

    // --- Input Branch Variables ---
    Int_t    nbjet = 0,   nqjet = 0;
    std::vector<int>* bjetflavor = nullptr;
    std::vector<int>* qjetflavor = nullptr;

    std::vector<TLorentzVector>* bjets = nullptr;
    std::vector<TLorentzVector>* qjets = nullptr;
    std::vector<TLorentzVector>* MET   = nullptr;

    // 'float' vector pointers for scalar values (assuming they hold one entry per event)
    std::vector<float>* scalarHT          = nullptr;
    std::vector<float>* crossSection      = nullptr;
    std::vector<float>* crossSectionError = nullptr;
    std::vector<float>* evtWeightBranch   = nullptr;
    
    // Scalar floats for Efrac (used for copying)
    tree->SetBranchAddress("nbjet",        &nbjet);
    tree->SetBranchAddress("nqjet",        &nqjet);
    tree->SetBranchAddress("bjetflavor",   &bjetflavor);
    tree->SetBranchAddress("qjetflavor",   &qjetflavor);
    tree->SetBranchAddress("bjets",        &bjets);
    tree->SetBranchAddress("qjets",        &qjets);
    tree->SetBranchAddress("MET",          &MET);

    // Set addresses for scalar branches (which are stored as vectors of size 1)
    tree->SetBranchAddress("ScalarHT_HT",         &scalarHT);
    tree->SetBranchAddress("Event_CrossSection",      &crossSection);
    tree->SetBranchAddress("Event_CrossSectionError", &crossSectionError);
    tree->SetBranchAddress("Weight_Weight",           &evtWeightBranch);

    // Set addresses for Efrac branches




    // --- Output File and Tree Handling ---
    TFile *outFile = new TFile(outputFilePath.c_str(), "RECREATE");
    outFile->cd();
    
    // Clone the tree structure to preserve desired branches
    TTree *outTree = tree->CloneTree(0);
    
    // Turn off all branches, then selectively turn on the ones we want to keep
    outTree->SetBranchStatus("*", 0); 

    // Turn on the vector branches we want to keep
    outTree->SetBranchStatus("nbjet",              1);
    outTree->SetBranchStatus("nqjet",              1);
    outTree->SetBranchStatus("bjetflavor",         1); // Keeping flavor for context
    outTree->SetBranchStatus("qjetflavor",         1); // Keeping flavor for context
    outTree->SetBranchStatus("bjets",              1);
    outTree->SetBranchStatus("qjets",              1);
    outTree->SetBranchStatus("MET",                1);

    // --- Output Branch Variables (Derived & Copied) ---
    // 4-vector properties
    float u1PT, b1PT, METPt;
    float u1Eta, b1Eta, METEta;
    float u1Phi, b1Phi, METPhi;
    float u1Mass, b1Mass, METMass;
    float u1Mt, b1Mt, METMt;

    // Delta quantities
    float ubDeltaR, bMETDeltaR, METuDeltaR;
    float ubDeltaPhi, bMETDeltaPhi, METuDeltaPhi;
    float ubDeltaMt, bMETDeltaMt, METuDeltaMt;
    float ubDeltaEta, bMETDeltaEta, METuDeltaEta;

    // Copied Efrac variables
  
    // Scalar event properties (copied from vectors of size 1)
    double b_scalarHT;
    double b_crossSection;
    double b_crossSectionError;
    double b_evtWeightBranch;


    // --- Create New Branches in Output Tree ---
    // Kinematic Branches
    outTree->Branch("u1PT", &u1PT, "u1PT/F");
    outTree->Branch("b1PT", &b1PT, "b1PT/F");
    outTree->Branch("METPt", &METPt, "METPt/F");

    outTree->Branch("u1Eta", &u1Eta, "u1Eta/F");
    outTree->Branch("b1Eta", &b1Eta, "b1Eta/F");
    outTree->Branch("METEta", &METEta, "METEta/F");

    outTree->Branch("u1Phi", &u1Phi, "u1Phi/F");
    outTree->Branch("b1Phi", &b1Phi, "b1Phi/F");
    outTree->Branch("METPhi", &METPhi, "METPhi/F");

    outTree->Branch("u1Mass", &u1Mass, "u1Mass/F");
    outTree->Branch("b1Mass", &b1Mass, "b1Mass/F");
    outTree->Branch("METMass", &METMass, "METMass/F");

    outTree->Branch("u1Mt", &u1Mt, "u1Mt/F");
    outTree->Branch("b1Mt", &b1Mt, "b1Mt/F");
    outTree->Branch("METMt", &METMt, "METMt/F");

    // Delta R Branches
    outTree->Branch("ubDeltaR", &ubDeltaR, "ubDeltaR/F");
    outTree->Branch("bMETDeltaR", &bMETDeltaR, "bMETDeltaR/F");
    outTree->Branch("METuDeltaR", &METuDeltaR, "METuDeltaR/F");

    // Delta Phi Branches
    outTree->Branch("ubDeltaPhi", &ubDeltaPhi, "ubDeltaPhi/F");
    outTree->Branch("bMETDeltaPhi", &bMETDeltaPhi, "bMETDeltaPhi/F");
    outTree->Branch("METuDeltaPhi", &METuDeltaPhi, "METuDeltaPhi/F");

    // Delta Mt Branches (calculated using Pt and DeltaPhi)
    outTree->Branch("ubDeltaMt", &ubDeltaMt, "ubDeltaMt/F");
    outTree->Branch("bMETDeltaMt", &bMETDeltaMt, "bMETDeltaMt/F");
    outTree->Branch("METuDeltaMt", &METuDeltaMt, "METuDeltaMt/F");

    // Delta Eta Branches
    outTree->Branch("ubDeltaEta", &ubDeltaEta, "ubDeltaEta/F");
    outTree->Branch("bMETDeltaEta", &bMETDeltaEta, "bMETDeltaEta/F");
    outTree->Branch("METuDeltaEta", &METuDeltaEta, "METuDeltaEta/F");

    // Copied Efrac Branches



    // Scalar Event Property Branches (renamed to simplify)
    outTree->Branch("ScalarHT.HT",        &b_scalarHT, "ScalarHT_HT/D");
    outTree->Branch("Event.CrossSection", &b_crossSection, "Event_CrossSection/D");
    outTree->Branch("Event.CrossSectionError", &b_crossSectionError, "Event_CrossSectionError/D");
    outTree->Branch("Weight.Weight",      &b_evtWeightBranch, "Weight_Weight/D");

    // FIX: Newly created branches must be explicitly enabled to ensure TTreeFormula can access them.
    // This resolves the "has to be enabled to be used" error.
    outTree->SetBranchStatus("u1PT", 1);
    outTree->SetBranchStatus("b1PT", 1);
    outTree->SetBranchStatus("METPt", 1);
    outTree->SetBranchStatus("u1Eta", 1);
    outTree->SetBranchStatus("b1Eta", 1);
    outTree->SetBranchStatus("METEta", 1);
    outTree->SetBranchStatus("u1Phi", 1);
    outTree->SetBranchStatus("b1Phi", 1);
    outTree->SetBranchStatus("METPhi", 1);
    outTree->SetBranchStatus("u1Mass", 1);
    outTree->SetBranchStatus("b1Mass", 1);
    outTree->SetBranchStatus("METMass", 1);
    outTree->SetBranchStatus("u1Mt", 1);
    outTree->SetBranchStatus("b1Mt", 1);
    outTree->SetBranchStatus("METMt", 1);
    outTree->SetBranchStatus("ubDeltaR", 1);
    outTree->SetBranchStatus("bMETDeltaR", 1);
    outTree->SetBranchStatus("METuDeltaR", 1);
    outTree->SetBranchStatus("ubDeltaPhi", 1);
    outTree->SetBranchStatus("bMETDeltaPhi", 1);
    outTree->SetBranchStatus("METuDeltaPhi", 1);
    outTree->SetBranchStatus("ubDeltaMt", 1);
    outTree->SetBranchStatus("bMETDeltaMt", 1);
    outTree->SetBranchStatus("METuDeltaMt", 1);
    outTree->SetBranchStatus("ubDeltaEta", 1);
    outTree->SetBranchStatus("bMETDeltaEta", 1);
    outTree->SetBranchStatus("METuDeltaEta", 1);
    outTree->SetBranchStatus("ScalarHT.HT", 1);
    outTree->SetBranchStatus("Event.CrossSection", 1);
    outTree->SetBranchStatus("Event.CrossSectionError", 1);
    outTree->SetBranchStatus("Weight.Weight", 1);
    
    // --- Event Loop ---
    Long64_t nEntries = tree->GetEntries();
    
    for (Long64_t i = 0; i < nEntries; ++i) {
        // Reset scalar values for safety at the start of loop
        b_scalarHT = 0.0;
        b_crossSection = 0.0;
        b_crossSectionError = 0.0;
        b_evtWeightBranch = 1.0;

        // Get the current entry data from the input tree
        tree->GetEntry(i);
        
        // Safely extract scalar event properties (check if vector is valid and non-empty)
        if (scalarHT && !scalarHT->empty()) {
            b_scalarHT = scalarHT->at(0);
        }
        if (crossSection && !crossSection->empty()) {
            b_crossSection = crossSection->at(0);
        }
        if (crossSectionError && !crossSectionError->empty()) {
            b_crossSectionError = crossSectionError->at(0);
        }
        if (evtWeightBranch && !evtWeightBranch->empty()) {
            b_evtWeightBranch = evtWeightBranch->at(0);
        }
        
        // Check for required jets and MET
        if (bjets->empty() || qjets->empty() || MET->empty()) {
            continue; // Skip event if minimum objects are not present
        }

        // Get the leading (pT-ordered) jets and MET
        TLorentzVector b1LV  = bjets->at(0); 
        TLorentzVector u1LV  = qjets->at(0); 
        TLorentzVector METLV = MET->at(0);   

        // 1. Basic Kinematics Calculation
        u1PT  = u1LV.Pt();  b1PT  = b1LV.Pt();  METPt  = METLV.Pt();
        u1Eta = u1LV.Eta(); b1Eta = b1LV.Eta(); METEta = METLV.Eta();
        u1Phi = u1LV.Phi(); b1Phi = b1LV.Phi(); METPhi = METLV.Phi();
        u1Mass = u1LV.M();  b1Mass = b1LV.M();  METMass = METLV.M();
        u1Mt   = u1LV.Mt(); b1Mt   = b1LV.Mt(); METMt   = METLV.Mt();

        // 2. Delta Quantities Calculation
        
        // Delta R
        ubDeltaR      = u1LV.DeltaR(b1LV);
        bMETDeltaR    = b1LV.DeltaR(METLV);
        METuDeltaR    = METLV.DeltaR(u1LV);

        // Delta Phi
        ubDeltaPhi    = u1LV.DeltaPhi(b1LV);
        bMETDeltaPhi  = b1LV.DeltaPhi(METLV);
        METuDeltaPhi  = METLV.DeltaPhi(u1LV);

        // Delta Mt (Transverse Mass)
        // Note: Delta Mt is typically calculated only for the system's mass, 
        // but here it is calculated for the pair system using pT and DeltaPhi.
        ubDeltaMt     = std::sqrt(2 * u1LV.Pt() * b1LV.Pt() * (1 - std::cos(ubDeltaPhi)));
        bMETDeltaMt   = std::sqrt(2 * b1LV.Pt() * METLV.Pt() * (1 - std::cos(bMETDeltaPhi)));
        METuDeltaMt   = std::sqrt(2 * METLV.Pt() * u1LV.Pt() * (1 - std::cos(METuDeltaPhi)));

        // Delta Eta
        ubDeltaEta    = u1Eta - b1Eta;
        bMETDeltaEta  = b1Eta - METEta;
        METuDeltaEta  = METEta - u1Eta;

 
        // Fill the output tree with the new values
        outTree->Fill(); 
    }

    // --- Write Histograms and Cutflow Information ---
    std::vector<std::string> histNames = {
        "tot_nevents", "cnt_metCut_nevents", "cnt_bjetCut_nevents",
        "cnt_qjetCut_nevents", "cnt_lVETO_nevents", "sel_nevents"
    };
    
    // Copy histograms and collect entry counts for nEvent tree
    for (const auto& name : histNames) {
        TH1D* hist = (TH1D*) inputFile->Get(name.c_str());
        if (!hist) {
            std::cerr << "Warning: Histogram " << name << " not found! Skipping copy." << std::endl;
            continue;
        }
        outFile->cd();
        hist->Write();
    }
    
    // Create CutFlow tree with float variables (copied from histogram bin content)
    TTree* cut_flow_tree = new TTree("CutFlow", "Float Event Summary");
    float f_tot_nevents, f_cnt_metCut_nevents, f_cnt_bjetCut_nevents;
    float f_cnt_qjetCut_nevents, f_cnt_lVETO_nevents, f_sel_nevents;

    // Set branch addresses
    cut_flow_tree->Branch("tot_nevents",         &f_tot_nevents, "tot_nevents/F");
    cut_flow_tree->Branch("cnt_lVETO_nevents",   &f_cnt_lVETO_nevents, "cnt_lVETO_nevents/F");
    cut_flow_tree->Branch("cnt_bjetCut_nevents", &f_cnt_bjetCut_nevents, "cnt_bjetCut_nevents/F");
    cut_flow_tree->Branch("cnt_qjetCut_nevents", &f_cnt_qjetCut_nevents, "cnt_qjetCut_nevents/F");
    cut_flow_tree->Branch("cnt_metCut_nevents",  &f_cnt_metCut_nevents, "cnt_metCut_nevents/F");
    cut_flow_tree->Branch("sel_nevents",         &f_sel_nevents, "sel_nevents/F");

    // Read histogram bin contents safely
    TH1D* h_tot         = (TH1D*)inputFile->Get("tot_nevents");
    TH1D* h_lVETO       = (TH1D*)inputFile->Get("cnt_lVETO_nevents");
    TH1D* h_bjetCut     = (TH1D*)inputFile->Get("cnt_bjetCut_nevents");
    TH1D* h_qjetCut     = (TH1D*)inputFile->Get("cnt_qjetCut_nevents");
    TH1D* h_metCut      = (TH1D*)inputFile->Get("cnt_metCut_nevents");
    TH1D* h_sel         = (TH1D*)inputFile->Get("sel_nevents");
    
    f_tot_nevents         = h_tot ? h_tot->GetBinContent(1) : 0.0f;
    f_cnt_lVETO_nevents   = h_lVETO ? h_lVETO->GetBinContent(1) : 0.0f;
    f_cnt_bjetCut_nevents = h_bjetCut ? h_bjetCut->GetBinContent(1) : 0.0f;
    f_cnt_qjetCut_nevents = h_qjetCut ? h_qjetCut->GetBinContent(1) : 0.0f;
    f_cnt_metCut_nevents  = h_metCut ? h_metCut->GetBinContent(1) : 0.0f;
    f_sel_nevents         = h_sel ? h_sel->GetBinContent(1) : 0.0f;

    // Fill and Write the cutflow tree
    cut_flow_tree->Fill();
    cut_flow_tree->Write();

    // Finalize output file
    outFile->Write();
    outFile->Close();
    inputFile->Close();

    std::cout << "[Done] Saved all derived quantities to: " << outputFilePath << std::endl;
    return 0;
}
