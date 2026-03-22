#pragma once
// main.hpp
// CutFlow 결과 → CSV / stdout / ROOT 출력 유틸리티
// XS/efficiency 계산 포함
// ============================================================

#include <vector>
#include <string>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <cmath>
#include <TFile.h>
#include <TTree.h>
#include <TLorentzVector.h>
#include "xs_map.hpp"
#include "event_selection.hpp"

// ============================================================
// per-cut 출력 행
// ============================================================
struct CutFlowRow {
    std::string cut_name;
    Long64_t    n_raw;
    double      n_weighted;  // n_raw * xsec / N_generated
    double      eff_abs;     // n_raw / N_generated
    double      eff_rel;     // n_raw / n_raw_prev
};

// ============================================================
// CutFlowRow 벡터 생성
// ============================================================
inline std::vector<CutFlowRow> BuildCutFlow(
        const std::vector<std::string>& cut_names,
        const std::vector<Long64_t>&    counts,
        double                          weight) {

    std::vector<CutFlowRow> cf;
    Long64_t n_gen = (counts.empty()) ? 1 : counts[0];

    for (size_t i = 0; i < cut_names.size(); ++i) {
        CutFlowRow row;
        row.cut_name   = cut_names[i];
        row.n_raw      = counts[i];
        row.n_weighted = counts[i] * weight;
        row.eff_abs    = (n_gen > 0) ? (double)counts[i] / n_gen : 0.;
        row.eff_rel    = (i == 0 || counts[i-1] == 0)
                         ? 1.0
                         : (double)counts[i] / counts[i-1];
        cf.push_back(row);
    }
    return cf;
}

// ============================================================
// stdout 출력
// ============================================================
inline void PrintCutFlow(const std::vector<CutFlowRow>& cf,
                         const std::string& sample_name,
                         const SampleInfo&  xs_info,
                         const std::string& version) {
    std::cout << "\n";
    std::cout << "========================================\n";
    std::cout << " Sample  : " << sample_name << "\n";
    std::cout << " Version : " << version     << "\n";
    std::cout << " XS [pb] : " << std::scientific << std::setprecision(4)
              << xs_info.xsec << " ± " << xs_info.xsec_unc << "\n";
    std::cout << "========================================\n";
    std::cout << std::left  << std::setw(14) << "cut"
              << std::right << std::setw(12) << "n_raw"
              << std::right << std::setw(16) << "n_weighted"
              << std::right << std::setw(10) << "eff_abs"
              << std::right << std::setw(10) << "eff_rel"
              << "\n";
    std::cout << std::string(62, '-') << "\n";
    for (auto& r : cf) {
        std::cout << std::left  << std::setw(14) << r.cut_name
                  << std::right << std::setw(12) << r.n_raw
                  << std::right << std::setw(16) << std::fixed
                                << std::setprecision(2) << r.n_weighted
                  << std::right << std::setw(10) << std::fixed
                                << std::setprecision(4) << r.eff_abs
                  << std::right << std::setw(10) << std::fixed
                                << std::setprecision(4) << r.eff_rel
                  << "\n";
    }
    std::cout << "\n";
}

// ============================================================
// CSV 저장
// 출력 파일명: cutflow_<sample>_<version>.csv
// ============================================================
inline void WriteCSV(const std::vector<CutFlowRow>& cf,
                     const std::string& sample_name,
                     const SampleInfo&  xs_info,
                     Long64_t           n_generated,
                     double             weight,
                     const std::string& version) {

    std::string out_path = "cutflow_" + sample_name + "_" + version + ".csv";
    std::ofstream ofs(out_path);
    if (!ofs.is_open()) {
        std::cerr << "[ERROR] Cannot open: " << out_path << "\n";
        return;
    }

    // meta block
    ofs << "# sample_name,"       << sample_name   << "\n";
    ofs << "# sel_version,"       << version        << "\n";
    ofs << "# xsec_pb,"           << std::scientific << std::setprecision(8)
                                   << xs_info.xsec   << "\n";
    ofs << "# xsec_unc_pb,"       << xs_info.xsec_unc << "\n";
    ofs << "# n_generated,"       << n_generated    << "\n";
    ofs << "# weight_per_event,"  << weight         << "\n";
    ofs << "#\n";

    // column header
    ofs << "cut,n_raw,n_weighted,eff_abs,eff_rel\n";

    // data
    for (auto& r : cf) {
        ofs << r.cut_name << ","
            << r.n_raw    << ","
            << std::fixed << std::setprecision(4) << r.n_weighted << ","
            << std::fixed << std::setprecision(6) << r.eff_abs    << ","
            << std::fixed << std::setprecision(6) << r.eff_rel    << "\n";
    }

    ofs.close();
    std::cout << "[INFO] CSV saved: " << out_path << "\n";
}

// ============================================================
// ROOT 저장
// 출력 파일명: sel_<sample>_<version>.root
// tree: events
// branches: u1_4mom, b1_4mom, MET_4mom, Ngen, Nsel, XS, dXS
//
// Nsel == 0 이면 빈 tree로 저장 (파일은 생성됨)
// ============================================================
inline void WriteROOT(const EventSelResult& result,
                      const std::string&    sample_name,
                      const SampleInfo&     xs_info,
                      const std::string&    version) {

    std::string out_path = "sel_" + sample_name + "_" + version + ".root";
    TFile* fout = TFile::Open(out_path.c_str(), "RECREATE");
    if (!fout || fout->IsZombie()) {
        std::cerr << "[ERROR] Cannot open ROOT file: " << out_path << "\n";
        return;
    }

    TTree* tree = new TTree("events", "Selected events");

    // ── scalar branches (이벤트마다 동일한 값) ──
    Long64_t Ngen = result.n_generated;
    Long64_t Nsel = result.n_sel;
    double   XS   = xs_info.xsec;
    double   dXS  = xs_info.xsec_unc;

    // ── 4-momentum branches (이벤트마다 다른 값) ──
    TLorentzVector u1_4mom, b1_4mom, MET_4mom;

    tree->Branch("Ngen",     &Ngen,     "Ngen/L");
    tree->Branch("Nsel",     &Nsel,     "Nsel/L");
    tree->Branch("XS",       &XS,       "XS/D");
    tree->Branch("dXS",      &dXS,      "dXS/D");
    tree->Branch("u1_4mom",  &u1_4mom);
    tree->Branch("b1_4mom",  &b1_4mom);
    tree->Branch("MET_4mom", &MET_4mom);

    // ── 이벤트 루프 ──
    for (Long64_t i = 0; i < result.n_sel; ++i) {
        u1_4mom  = result.u1_4moms[i];
        b1_4mom  = result.b1_4moms[i];
        MET_4mom = result.met_4moms[i];
        tree->Fill();
    }

    fout->Write();
    fout->Close();

    std::cout << "[INFO] ROOT saved: " << out_path
              << "  (Ngen=" << Ngen << ", Nsel=" << Nsel << ")\n";
}
