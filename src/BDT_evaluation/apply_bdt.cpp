// apply_bdt.cpp
//
// Usage:
//   ./apply_bdt <xml_path> <input_path> <output_dir> <mode>
//
// mode:
//   signal  -> sel_Signal_* 만 처리
//   bkg     -> sel_Signal_* 제외하고 처리
//   all     -> 전부 처리
//
// Example:
//   ./apply_bdt \
//     /path/to/TMVAClassification_BDT.weights.xml \
//     /users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/postprocessing/root/v2/data \
//     /users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/postprocessing/root/v2/data_eval \
//     all

#include <iostream>
#include <string>
#include <vector>
#include <filesystem>
#include <memory>

#include "TFile.h"
#include "TTree.h"
#include "TString.h"
#include "TSystem.h"

#include "TMVA/Reader.h"

namespace fs = std::filesystem;

// ------------------------------------------------------------
// helper
// ------------------------------------------------------------
bool IsRootFile(const fs::path& p) {
    return fs::is_regular_file(p) && p.extension() == ".root";
}

bool IsSignalFile(const std::string& fname) {
    return fname.rfind("sel_Signal_", 0) == 0;
}

std::string ExtractSignalMx1(const std::string& fname) {
    // expected: sel_Signal_<mx1>_<lam1>_<lam2>_<version>.root
    // example : sel_Signal_1-0_0-03_0-04_v2.root

    const std::string prefix = "sel_Signal_";
    if (fname.rfind(prefix, 0) != 0) return "";

    std::string rest = fname.substr(prefix.size()); // "1-0_0-03_0-04_v2.root"
    auto pos = rest.find('_');
    if (pos == std::string::npos) return "";

    return rest.substr(0, pos); // "1-0"
}


bool PassMode(const std::string& fname,
              const std::string& mode,
              const std::string& target_mx1) {
    const bool isSig = IsSignalFile(fname);

    if (mode == "signal") {
        if (!isSig) return false;
        if (target_mx1.empty()) return true;
        return ExtractSignalMx1(fname) == target_mx1;
    }

    if (mode == "bkg") {
        return !isSig;
    }

    if (mode == "all") {
        if (!isSig) return true;  // bkg는 전부 허용
        if (target_mx1.empty()) return true;
        return ExtractSignalMx1(fname) == target_mx1;
    }

    return false;
}
std::vector<std::string> CollectInputFiles(const std::string& input_path,
                                           const std::string& mode,
                                           const std::string& target_mx1) { 
    std::vector<std::string> files;
    fs::path p(input_path);

    if (!fs::exists(p)) {
        std::cerr << "[ERROR] input_path does not exist: " << input_path << "\n";
        return files;
    }

    if (fs::is_regular_file(p)) {
        if (p.extension() == ".root" && PassMode(p.filename().string(), mode, target_mx1)) {
            files.push_back(p.string());
        }
        return files;
    }

    if (fs::is_directory(p)) {
        for (const auto& entry : fs::directory_iterator(p)) {
            if (!IsRootFile(entry.path())) continue;
            const std::string fname = entry.path().filename().string();
            if (!PassMode(fname, mode, target_mx1)) continue;
            files.push_back(entry.path().string());
        }
    }

    std::sort(files.begin(), files.end());
    return files;
}

struct BDTVars {
    float u1PT = 0.f;
    float b1PT = 0.f;
    float METPt = 0.f;
    float u1Eta = 0.f;
    float b1Eta = 0.f;
    float ubDeltaR = 0.f;
    float ubDeltaPhi = 0.f;
    float bMETDeltaPhi = 0.f;
    float METuDeltaPhi = 0.f;
    float METuDeltaMt = 0.f;
};

std::unique_ptr<TMVA::Reader> MakeReader(const std::string& xml_path, BDTVars& v) {
    auto reader = std::make_unique<TMVA::Reader>("!Color:!Silent");

    reader->AddVariable("u1PT",         &v.u1PT);
    reader->AddVariable("b1PT",         &v.b1PT);
    reader->AddVariable("METPt",        &v.METPt);
    reader->AddVariable("u1Eta",        &v.u1Eta);
    reader->AddVariable("b1Eta",        &v.b1Eta);
    reader->AddVariable("ubDeltaR",     &v.ubDeltaR);
    reader->AddVariable("ubDeltaPhi",   &v.ubDeltaPhi);
    reader->AddVariable("bMETDeltaPhi", &v.bMETDeltaPhi);
    reader->AddVariable("METuDeltaPhi", &v.METuDeltaPhi);
    reader->AddVariable("METuDeltaMt",  &v.METuDeltaMt);

    reader->BookMVA("BDT", xml_path.c_str());
    return reader;
}

// ------------------------------------------------------------
// process one file
// ------------------------------------------------------------
bool ProcessOneFile(TMVA::Reader& reader,
                    BDTVars& v,
                    const std::string& in_file,
                    const std::string& out_dir) {
    std::cout << "\n[INFO] Processing: " << in_file << "\n";

    TFile* fin = TFile::Open(in_file.c_str(), "READ");
    if (!fin || fin->IsZombie()) {
        std::cerr << "[ERROR] Cannot open input file: " << in_file << "\n";
        return false;
    }

    TTree* inTree = dynamic_cast<TTree*>(fin->Get("events"));
    if (!inTree) {
        std::cerr << "[ERROR] Cannot find tree 'events' in: " << in_file << "\n";
        fin->Close();
        return false;
    }
    
    inTree->SetBranchAddress("u1PT",         &v.u1PT);
    inTree->SetBranchAddress("b1PT",         &v.b1PT);
    inTree->SetBranchAddress("METPt",        &v.METPt);
    inTree->SetBranchAddress("u1Eta",        &v.u1Eta);
    inTree->SetBranchAddress("b1Eta",        &v.b1Eta);
    inTree->SetBranchAddress("ubDeltaR",     &v.ubDeltaR);
    inTree->SetBranchAddress("ubDeltaPhi",   &v.ubDeltaPhi);
    inTree->SetBranchAddress("bMETDeltaPhi", &v.bMETDeltaPhi);
    inTree->SetBranchAddress("METuDeltaPhi", &v.METuDeltaPhi);
    inTree->SetBranchAddress("METuDeltaMt",  &v.METuDeltaMt);

    fs::create_directories(out_dir);
    fs::path out_path = fs::path(out_dir) / fs::path(in_file).filename();

    TFile* fout = TFile::Open(out_path.string().c_str(), "RECREATE");
    if (!fout || fout->IsZombie()) {
        std::cerr << "[ERROR] Cannot create output file: " << out_path << "\n";
        fin->Close();
        return false;
    }

    // clone tree structure + existing branches
    TTree* outTree = inTree->CloneTree(0);

    float bdt_response = -999.f;
    outTree->Branch("bdt_response", &bdt_response, "bdt_response/F");

    const Long64_t nEntries = inTree->GetEntries();
    std::cout << "[INFO] Entries = " << nEntries << "\n";

    for (Long64_t i = 0; i < nEntries; ++i) {
        inTree->GetEntry(i);
        bdt_response = reader.EvaluateMVA("BDT");
        outTree->Fill();
    }

    fout->cd();
    outTree->Write();
    fout->Close();
    fin->Close();

    std::cout << "[INFO] Saved: " << out_path << "\n";
    return true;
}

// ------------------------------------------------------------
// main
// ------------------------------------------------------------
int main(int argc, char** argv) {
    std::string target_mx1 = "";
    if (argc >= 6) target_mx1 = argv[5];
    if (argc < 5) {
        std::cerr << "Usage: " << argv[0]
                  << " <xml_path> <input_path> <output_dir> <mode> [target_mx1]\n"
                  << "  mode = signal | bkg | all\n";
        return 1;
    }

    std::string xml_path   = argv[1];
    std::string input_path = argv[2];
    std::string output_dir = argv[3];
    std::string mode       = argv[4];

    if (mode != "signal" && mode != "bkg" && mode != "all") {
        std::cerr << "[ERROR] Invalid mode: " << mode << "\n";
    }

    if (gSystem->AccessPathName(xml_path.c_str(), kFileExists)) {
        std::cerr << "[ERROR] XML file not found: " << xml_path << "\n";
        return 1;
    }

    auto files = CollectInputFiles(input_path, mode, target_mx1);
    if (files.empty()) {
        std::cerr << "[ERROR] No matching ROOT files found.\n";
        return 1;
    }
    
    BDTVars vars;
    auto reader = MakeReader(xml_path, vars);
      
    std::cout << "[INFO] XML      : " << xml_path << "\n";
    std::cout << "[INFO] Input    : " << input_path << "\n";
    std::cout << "[INFO] Output   : " << output_dir << "\n";
    std::cout << "[INFO] Mode     : " << mode << "\n";
    std::cout << "[INFO] N files   : " << files.size() << "\n";

    int nOK = 0;
    for (const auto& f : files) {
        if (ProcessOneFile(*reader, vars, f, output_dir)) ++nOK;
    }

    std::cout << "\n[INFO] Done. success = " << nOK
              << " / " << files.size() << "\n";

    return 0;
}
