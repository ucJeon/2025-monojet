// bdt_training.cpp
// Monojet analysis - TMVA BDT training
//
// Usage:
//   ./bdt_training <which_mx1> <version> <nTrees> <maxDepth> <flag> <out_dir>
//
// Example:
//   ./bdt_training 1-0 v2 2500 4 uc /path/to/output/

#include <iostream>
#include <string>
#include <vector>
#include <memory>

#include "TFile.h"
#include "TChain.h"
#include "TString.h"
#include "TSystem.h"
#include "TCut.h"
#include "TDatime.h"

#include "TMVA/Factory.h"
#include "TMVA/DataLoader.h"
#include "TMVA/Tools.h"

TString getTimeStamp() {
    TDatime now;
    return Form("%04d%02d%02d_%02d%02d%02d",
                now.GetYear(), now.GetMonth(), now.GetDay(),
                now.GetHour(), now.GetMinute(), now.GetSecond());
}

int main(int argc, char** argv) {
    if (argc < 7) {
        std::cerr << "Usage: " << argv[0]
                  << " <which_mx1> <version> <nTrees> <maxDepth> <flag> <out_dir>\n"
                  << "e.g.) ./bdt_training 1-0 v2 2500 4 uc /path/to/output/\n";
        return 1;
    }

    // -------------------------------------------------------
    // Arguments
    // -------------------------------------------------------
    TString which_mx1 = argv[1];   // e.g. "1-0"
    TString version   = argv[2];   // e.g. "v2"
    int     nTrees    = std::stoi(argv[3]);
    int     maxDepth  = std::stoi(argv[4]);
    TString flag      = argv[5];   // e.g. "uc"
    TString out_dir   = argv[6];

    if (!out_dir.EndsWith("/")) out_dir += "/";

    // target luminosity [fb^-1]
    double target_lumi = 300000.0; // 300 fb^-1 if XS in pb

    // Input directory
    TString data_dir = Form(
        "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/postprocessing/root/%s/BDTdata/",
        version.Data()
    );

    // -------------------------------------------------------
    // Prepare output directory
    // -------------------------------------------------------
    gSystem->mkdir(out_dir.Data(), true);
    TMVA::Tools::Instance();

    TString subDir = Form("%sMX1%s_nTree%d_maxDepth%d_%s_%s",
                          out_dir.Data(),
                          which_mx1.Data(),
                          nTrees,
                          maxDepth,
                          flag.Data(),
                          version.Data());

    gSystem->mkdir(subDir.Data(), true);

    TString outFileName = subDir + "/TMVA_output.root";
    auto outputFile = std::unique_ptr<TFile>(TFile::Open(outFileName, "RECREATE"));
    if (!outputFile || outputFile->IsZombie()) {
        std::cerr << "[ERROR] Failed to create output file: " << outFileName << "\n";
        return 1;
    }

    // -------------------------------------------------------
    // TMVA setup
    // -------------------------------------------------------
    TMVA::Factory factory(
        "TMVAClassification",
        outputFile.get(),
        "!V:!Silent:Color:DrawProgressBar:Transformations=I;D;P;G,D:AnalysisType=Classification"
    );

    TMVA::DataLoader dataloader("dataset");

    // -------------------------------------------------------
    // Input variables
    // -------------------------------------------------------
    dataloader.AddVariable("u1PT",         'F');
    dataloader.AddVariable("b1PT",         'F');
    dataloader.AddVariable("METPt",        'F');
    dataloader.AddVariable("u1Eta",        'F');
    dataloader.AddVariable("b1Eta",        'F');
    dataloader.AddVariable("ubDeltaR",     'F');
    dataloader.AddVariable("ubDeltaPhi",   'F');
    dataloader.AddVariable("bMETDeltaPhi", 'F');
    dataloader.AddVariable("METuDeltaPhi", 'F');
    dataloader.AddVariable("METuDeltaMt",  'F');

    // -------------------------------------------------------
    // Signal : add 3x3 grid together
    // file pattern example:
    //   sel_Signal_1-0_0-1_0-1.0_v2.root
    // -------------------------------------------------------
    TChain* sigChain = new TChain("events");

    std::vector<TString> lam1_list = {"0-1", "0-3", "0-5"};
    std::vector<TString> lam2_list = {"0-1.0", "0-3.0", "0-5.0"};

    int nSigFilesAdded = 0;

    for (const auto& lam1 : lam1_list) {
        for (const auto& lam2 : lam2_list) {
            TString sigPath = Form("%ssel_Signal_%s_%s_%s_%s.root",
                                   data_dir.Data(),
                                   which_mx1.Data(),
                                   lam1.Data(),
                                   lam2.Data(),
                                   version.Data());

            if (!gSystem->AccessPathName(sigPath, kFileExists)) {
                sigChain->Add(sigPath);
                ++nSigFilesAdded;
                std::cout << "[INFO] Add signal: " << sigPath << "\n";
            } else {
                std::cerr << "[WARN] Missing signal: " << sigPath << "\n";
            }
        }
    }

    std::cout << "[INFO] Number of signal files added: " << nSigFilesAdded << "\n";
    std::cout << "[INFO] Signal entries: " << sigChain->GetEntries() << "\n";

    if (sigChain->GetEntries() == 0) {
        std::cerr << "[ERROR] Signal chain is empty.\n";
        delete sigChain;
        return 1;
    }

    // -------------------------------------------------------
    // Backgrounds: explicit file list
    // -------------------------------------------------------
    TChain* bgChain = new TChain("events");

    std::vector<TString> bkgNames = {
        // TT
        "sel_ttbar.1", "sel_ttbar.2", "sel_ttbar.3", "sel_ttbar.4", "sel_ttbar.5",
        "sel_ttbar.6", "sel_ttbar.7", "sel_ttbar.8", "sel_ttbar.9",

        // WJets
        "sel_wjets.2", "sel_wjets.3", "sel_wjets.4", "sel_wjets.5",
        "sel_wjets.6", "sel_wjets.7", "sel_wjets.8",

        // ZJets
        "sel_zjets.1", "sel_zjets.2", "sel_zjets.3", "sel_zjets.4",
        "sel_zjets.5", "sel_zjets.6", "sel_zjets.7", "sel_zjets.8",

        // Diboson
        "sel_ww2l2v.0",
        "sel_wwlv2q.1", "sel_wwlv2q.2", "sel_wwlv2q.3", "sel_wwlv2q.4",
        "sel_wwlv2q.5", "sel_wwlv2q.6", "sel_wwlv2q.7",

        "sel_wz2l2q.1", "sel_wz2l2q.2", "sel_wz2l2q.3", "sel_wz2l2q.4",
        "sel_wz2l2q.5", "sel_wz2l2q.6", "sel_wz2l2q.7",

        "sel_wz3l1v.0",

        "sel_wzlv2q.1", "sel_wzlv2q.2", "sel_wzlv2q.3", "sel_wzlv2q.4",
        "sel_wzlv2q.5", "sel_wzlv2q.6", "sel_wzlv2q.7",

        "sel_zz4l.0"
    };

    int nBkgFilesAdded = 0;

    for (const auto& name : bkgNames) {
        TString path = Form("%s%s_%s.root",
                            data_dir.Data(),
                            name.Data(),
                            version.Data());

        if (!gSystem->AccessPathName(path, kFileExists)) {
            bgChain->Add(path);
            ++nBkgFilesAdded;
            std::cout << "[INFO] Add bkg: " << path << "\n";
        } else {
            std::cerr << "[WARN] Missing bkg: " << path << "\n";
        }
    }

    std::cout << "[INFO] Number of bkg files added: " << nBkgFilesAdded << "\n";
    std::cout << "[INFO] Background entries: " << bgChain->GetEntries() << "\n";

    if (bgChain->GetEntries() == 0) {
        std::cerr << "[ERROR] Background chain is empty.\n";
        delete sigChain;
        delete bgChain;
        return 1;
    }

    // -------------------------------------------------------
    // Weight expression
    // -------------------------------------------------------
    TString weightExpr = Form("%.1f * XS / Ngen", target_lumi);
    std::cout << "[INFO] Weight expression: " << weightExpr << "\n";

    dataloader.AddSignalTree(sigChain, 1.0);
    dataloader.AddBackgroundTree(bgChain, 1.0);

    dataloader.SetSignalWeightExpression(weightExpr);
    dataloader.SetBackgroundWeightExpression(weightExpr);

    // -------------------------------------------------------
    // Prepare training / test
    // -------------------------------------------------------
    Long64_t nSig = sigChain->GetEntries();
    Long64_t nBkg = bgChain->GetEntries();

    Long64_t nTrainSig = static_cast<Long64_t>(0.7 * nSig);
    Long64_t nTestSig  = nSig - nTrainSig;

    Long64_t nTrainBkg = static_cast<Long64_t>(0.7 * nBkg);
    Long64_t nTestBkg  = nBkg - nTrainBkg;

    TCut sigCut = "";
    TCut bkgCut = "";

    TString prepOpt = Form(
        "nTrain_Signal=%lld:"
        "nTest_Signal=%lld:"
        "nTrain_Background=%lld:"
        "nTest_Background=%lld:"
        "SplitMode=Random:"
        "NormMode=EqualNumEvents:!V",
        nTrainSig, nTestSig,
        nTrainBkg, nTestBkg
    );

    dataloader.PrepareTrainingAndTestTree(
        sigCut,
        bkgCut,
        prepOpt
    );

    // -------------------------------------------------------
    // Book BDT
    // -------------------------------------------------------
    factory.BookMethod(
        &dataloader,
        TMVA::Types::kBDT,
        "BDT",
        Form("!H:!V:NTrees=%d:"
             "MinNodeSize=2.5%%:"
             "MaxDepth=%d:"
             "BoostType=AdaBoost:"
             "AdaBoostBeta=0.5:"
             "UseBaggedBoost:"
             "BaggedSampleFraction=0.5:"
             "SeparationType=GiniIndex:"
             "nCuts=20",
             nTrees, maxDepth)
    );

    // -------------------------------------------------------
    // Train / Test / Evaluate
    // -------------------------------------------------------
    factory.TrainAllMethods();
    factory.TestAllMethods();
    factory.EvaluateAllMethods();

    outputFile->Write();
    outputFile->Close();

    std::cout << "[INFO] Done. Output: " << outFileName << "\n";
    std::cout << "[INFO] version=" << version
              << " flag=" << flag
              << " nTrees=" << nTrees
              << " maxDepth=" << maxDepth
              << " lumi=" << target_lumi << " fb-1\n";

    delete sigChain;
    delete bgChain;
    return 0;
}
