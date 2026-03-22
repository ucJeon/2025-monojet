// #pragma once
// postprocess.cpp
// sel_*.root 파일들을 sample 단위로 merge하고 파생 변수를 계산하여 저장
//
// Usage:
//   ./postprocess <version> <in_dir> <out_dir>
//   예시: ./postprocess v2 .../outputs/root/v2 .../outputs/postproc/v2
//
// Input tree : events
// Input branches : Ngen, Nsel, XS, dXS, u1_4mom, b1_4mom, MET_4mom
//
// Output tree : events
// Output branches:
//   Ngen, Nsel, XS, dXS (scalar, 이벤트마다 동일)
//   u1PT, b1PT, METPt
//   u1Eta, b1Eta
//   ubDeltaR, ubDeltaPhi
//   bMETDeltaPhi, METuDeltaPhi
//   METuDeltaMt

#include <TFile.h>
#include <TTree.h>
#include <TLorentzVector.h>

#include <filesystem>
#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <regex>
#include <cmath>
#include <numeric>
#include <algorithm>

#include <optional>

namespace fs = std::filesystem;

// ============================================================
// 1. 파일명 파싱
//    sel_{sample_key}.{parallel}_{version}.root
//    → sample_key, parallel index
// ============================================================
struct ParsedFile {
    std::string sample_key;   // e.g. "zz4l.0" or "Signal_2-5_0-4_0-6.0"
    std::string parallel;     // e.g. "33" or "25"
    std::string filepath;
};

std::optional<ParsedFile> ParseFilename(const std::string& filepath,
                                         const std::string& version) {
    std::string fname = fs::path(filepath).filename().string();
    // pattern: sel_{body}.{parallel}_{version}.root
    std::string suffix = "_" + version + ".root";
    if (fname.rfind(suffix) == std::string::npos) return std::nullopt;
    if (fname.substr(0, 4) != "sel_") return std::nullopt;

    // suffix 제거
    std::string body = fname.substr(4, fname.size() - 4 - suffix.size());
    // body = "{sample_key}.{parallel}"
    // 마지막 '.' 뒤가 parallel (숫자)
    size_t dot_pos = body.rfind('.');
    if (dot_pos == std::string::npos) return std::nullopt;

    std::string parallel = body.substr(dot_pos + 1);
    // parallel이 숫자인지 확인
    if (parallel.empty() || !std::all_of(parallel.begin(), parallel.end(), ::isdigit))
        return std::nullopt;

    std::string sample_key = body.substr(0, dot_pos);

    return ParsedFile{sample_key, parallel, filepath};
}

// ============================================================
// 2. in_dir 내 파일을 sample_key 기준으로 그룹핑
// ============================================================
std::map<std::string, std::vector<ParsedFile>>
GroupFiles(const std::string& in_dir, const std::string& version) {
    std::map<std::string, std::vector<ParsedFile>> groups;

    for (auto const& entry : fs::directory_iterator(in_dir)) {
        if (!entry.is_regular_file()) continue;
        auto result = ParseFilename(entry.path().string(), version);
        if (!result) {
            std::cerr << "[WARN] 파싱 실패, 스킵: " << entry.path().filename() << "\n";
            continue;
        }
        groups[result->sample_key].push_back(*result);
    }

    for (auto& [key, files] : groups) {
        std::sort(files.begin(), files.end(),
                  [](const ParsedFile& a, const ParsedFile& b) {
                      return std::stoi(a.parallel) < std::stoi(b.parallel);
                  });
    }

    return groups;
}

static std::vector<std::string> Split(const std::string& s, char delim){
    std::vector<std::string> out;
    std::stringstream ss(s);
    std::string tok;
    while (std::getline(ss, tok, delim)) out.push_back(tok);
    return out;
}

static std::string StripDot0(std::string s){
    auto pos = s.find(".0");
    if (pos != std::string::npos) s = s.substr(0, pos);
    return s;
}

static bool IsInSet(const std::string& x, const std::vector<std::string>& allowed){
    return std::find(allowed.begin(), allowed.end(), x) != allowed.end();
}

// 여기만 수정해서 signal grid 바꾸면 됨
static const std::vector<std::string> SIG_GRID = {"0-1", "0-3", "0-5"};

static bool IsSignalSample(const std::string& sample_key){
    return sample_key.rfind("Signal_", 0) == 0;
}

static bool ComputeIsSigTargetFromSampleKey(const std::string& sample_key){
    if (!IsSignalSample(sample_key)) return false;

    auto usParts = Split(sample_key, '_');
    // expected: Signal_mass_lam1_lam2
    if (usParts.size() < 4) return false;

    std::string lam1 = StripDot0(usParts[2]);
    std::string lam2 = StripDot0(usParts[3]);

    return IsInSet(lam1, SIG_GRID) && IsInSet(lam2, SIG_GRID);
}

Long64_t ReadEntriesOnly(const std::string& filepath) {
    TFile* f = TFile::Open(filepath.c_str(), "READ");
    if (!f || f->IsZombie()) return 0;

    TTree* tree = dynamic_cast<TTree*>(f->Get("events"));
    if (!tree) {
        f->Close();
        return 0;
    }

    Long64_t n = tree->GetEntries();
    f->Close();
    return n;
}

struct SplitPlan {
    std::vector<std::string> bdt_files;
    std::vector<std::string> data_files;
    Long64_t total_entries = 0;
    Long64_t target_entries = 0;
    bool isSig = false;
    bool isSigTarget = false;
};

static const Long64_t TARGET_SIG_PER_SAMPLE = 80000;
// static const double   BKG_BDT_FRAC = 0.8;
static const double   BKG_BDT_FRAC = 0.7;

SplitPlan MakeSplitPlan(const std::string& sample_key,
                        const std::vector<ParsedFile>& files) {
    SplitPlan plan;
    plan.isSig = IsSignalSample(sample_key);
    plan.isSigTarget = plan.isSig ? ComputeIsSigTargetFromSampleKey(sample_key) : false;

    struct FileInfo {
        std::string path;
        Long64_t entries;
    };
    std::vector<FileInfo> valid;

    for (const auto& pf : files) {
        Long64_t n = ReadEntriesOnly(pf.filepath);
        if (n <= 0) continue;
        valid.push_back({pf.filepath, n});
        plan.total_entries += n;
    }

    if (plan.isSig) {
        if (!plan.isSigTarget) {
            for (auto& x : valid) plan.data_files.push_back(x.path);
            plan.target_entries = 0;
            return plan;
        }
        plan.target_entries = TARGET_SIG_PER_SAMPLE;
    } else {
        plan.target_entries = (Long64_t)std::floor(BKG_BDT_FRAC * (double)plan.total_entries);
    }

    Long64_t acc = 0;
    for (auto& x : valid) {
        if (acc < plan.target_entries) {
            plan.bdt_files.push_back(x.path);
            acc += x.entries;
        } else {
            plan.data_files.push_back(x.path);
        }
    }

    return plan;
}

// ============================================================
// 3. 단일 파일에서 scalar 메타데이터 읽기 (Ngen, Nsel, XS, dXS)
// ============================================================
struct FileMeta {
    Long64_t Ngen = 0;
    Long64_t Nsel = 0;
    double   XS   = -1.;
    double   dXS  = -1.;
    bool     valid = false;
};

FileMeta ReadMeta(const std::string& filepath) {
    FileMeta meta;
    TFile* f = TFile::Open(filepath.c_str(), "READ");
    if (!f || f->IsZombie()) {
        std::cerr << "[WARN] 파일 열기 실패: " << filepath << "\n";
        return meta;
    }
    TTree* tree = dynamic_cast<TTree*>(f->Get("events"));
    if (!tree || tree->GetEntries() == 0) {
        // Nsel==0인 빈 트리는 정상 — scalar 0으로 처리
        // Ngen/XS는 첫 엔트리에서 읽어야 하므로, 엔트리가 없으면 별도 처리 필요
        // → 빈 트리는 Ngen=0, Nsel=0, XS는 아직 모름 → 스킵하지 않고 meta.valid=false 반환
        f->Close();
        return meta;
    }

    Long64_t Ngen; Long64_t Nsel;
    double   XS;   double   dXS;
    tree->SetBranchAddress("Ngen", &Ngen);
    tree->SetBranchAddress("Nsel", &Nsel);
    tree->SetBranchAddress("XS",   &XS);
    tree->SetBranchAddress("dXS",  &dXS);
    tree->GetEntry(0);  // scalar이므로 첫 엔트리만 읽으면 됨

    meta.Ngen  = Ngen;
    meta.Nsel  = Nsel;
    meta.XS    = XS;
    meta.dXS   = dXS;
    meta.valid = true;

    f->Close();
    return meta;
}

// ============================================================
// 4. 파생 변수 계산 (TLorentzVector 기반)
// ============================================================
struct DerivedVars {
    float u1PT;
    float b1PT;
    float METPt;
    float u1Eta;
    float b1Eta;
    float ubDeltaR;
    float ubDeltaPhi;
    float bMETDeltaPhi;
    float METuDeltaPhi;
    float METuDeltaMt;
};

DerivedVars ComputeDerived(const TLorentzVector& u1,
                            const TLorentzVector& b1,
                            const TLorentzVector& MET) {
    DerivedVars d;
    d.u1PT  = u1.Pt();
    d.b1PT  = b1.Pt();
    d.METPt = MET.Pt();

    d.u1Eta = u1.Eta();
    d.b1Eta = b1.Eta();

    d.ubDeltaR   = u1.DeltaR(b1);
    d.ubDeltaPhi = u1.DeltaPhi(b1);

    d.bMETDeltaPhi = b1.DeltaPhi(MET);
    d.METuDeltaPhi = MET.DeltaPhi(u1);

    // m_T(MET, u1) = sqrt(2 * pT_MET * pT_u1 * (1 - cos(dphi)))
    d.METuDeltaMt = std::sqrt(
        std::max(0., 2. * MET.Pt() * u1.Pt()
                     * (1. - std::cos(MET.DeltaPhi(u1)))));

    return d;
}

// ============================================================
// 5. 샘플 단위 처리: merge + 파생 변수 계산 + 저장
// ============================================================
void ProcessSample(const std::string&              sample_key,
                   const std::vector<std::string>& filepaths,
                   const std::string&              out_dir,
                   const std::string&              version) {

    if (filepaths.empty()) {
        std::cout << "[SKIP] empty subset: " << sample_key << "\n";
        return;
    }

    std::string out_fname = out_dir + "/sel_" + sample_key + "_" + version + ".root";

    // 4) 이미 처리된 샘플 skip
    if (fs::exists(out_fname)) {
        std::cout << "[SKIP] 이미 존재: " << out_fname << "\n";
        return;
    }

    std::cout << "[INFO] Processing: " << sample_key
              << "  (" << filepaths.size() << " files)\n";

    // ── pass 1: meta 수집 (Ngen 합산, XS 일관성 확인) ──
    Long64_t Ngen_total = 0;
    Long64_t Nsel_total = 0;
    double   XS_ref     = -1.;
    double   dXS_ref    = -1.;
    std::vector<std::string> valid_files;

    for (auto& fpath : filepaths) {
        auto meta = ReadMeta(fpath);
        if (!meta.valid) {
            // 빈 트리 파일 (Nsel==0) — Ngen/XS를 읽을 수 없으므로 스킵
            std::cout << "  [SKIP empty] " << fs::path(fpath).filename() << "\n";
            continue;
        }
        // 3) XS 일관성 확인
        if (XS_ref < 0.) {
            XS_ref  = meta.XS;
            dXS_ref = meta.dXS;
        } else {
            double rel_diff = std::abs(meta.XS - XS_ref) / (std::abs(XS_ref) + 1e-30);
            if (rel_diff > 1e-4) {
                std::cerr << "  [WARN] XS 불일치 → skip: "
                          << fs::path(fpath).filename()
                          << "  (expected " << XS_ref
                          << ", got "       << meta.XS << ")\n";
                continue;
            }
        }
        // 2) Ngen, Nsel summation
        Ngen_total += meta.Ngen;
        Nsel_total += meta.Nsel;
        valid_files.push_back(fpath);
    }

    if (XS_ref < 0.) {
        std::cerr << "[ERROR] 유효한 파일 없음: " << sample_key << "\n";
        return;
    }

    std::cout << "  Ngen=" << Ngen_total
              << ", Nsel=" << Nsel_total
              << ", XS="   << XS_ref << "\n";

    // ── pass 2: output tree 생성 ──
    TFile* fout = TFile::Open(out_fname.c_str(), "RECREATE");
    if (!fout || fout->IsZombie()) {
        std::cerr << "[ERROR] 출력 파일 생성 실패: " << out_fname << "\n";
        return;
    }
    TTree* out_tree = new TTree("events", "postprocessed events");

    // scalar branches
    Long64_t b_Ngen = Ngen_total;
    Long64_t b_Nsel = Nsel_total;
    double   b_XS   = XS_ref;
    double   b_dXS  = dXS_ref;
    out_tree->Branch("Ngen", &b_Ngen, "Ngen/L");
    out_tree->Branch("Nsel", &b_Nsel, "Nsel/L");
    out_tree->Branch("XS",   &b_XS,   "XS/D");
    out_tree->Branch("dXS",  &b_dXS,  "dXS/D");

    // derived variable branches
    float b_u1PT, b_b1PT, b_METPt;
    float b_u1Eta, b_b1Eta;
    float b_ubDeltaR, b_ubDeltaPhi;
    float b_bMETDeltaPhi, b_METuDeltaPhi;
    float b_METuDeltaMt;

    out_tree->Branch("u1PT",        &b_u1PT,        "u1PT/F");
    out_tree->Branch("b1PT",        &b_b1PT,        "b1PT/F");
    out_tree->Branch("METPt",       &b_METPt,       "METPt/F");
    out_tree->Branch("u1Eta",       &b_u1Eta,       "u1Eta/F");
    out_tree->Branch("b1Eta",       &b_b1Eta,       "b1Eta/F");
    out_tree->Branch("ubDeltaR",    &b_ubDeltaR,    "ubDeltaR/F");
    out_tree->Branch("ubDeltaPhi",  &b_ubDeltaPhi,  "ubDeltaPhi/F");
    out_tree->Branch("bMETDeltaPhi",&b_bMETDeltaPhi,"bMETDeltaPhi/F");
    out_tree->Branch("METuDeltaPhi",&b_METuDeltaPhi,"METuDeltaPhi/F");
    out_tree->Branch("METuDeltaMt", &b_METuDeltaMt, "METuDeltaMt/F");

    // ── pass 3: 이벤트 루프 (파일별 순회) ──
    for (auto& fpath : valid_files) {
        TFile* fin = TFile::Open(fpath.c_str(), "READ");
        if (!fin || fin->IsZombie()) continue;

        TTree* in_tree = dynamic_cast<TTree*>(fin->Get("events"));
        if (!in_tree) { fin->Close(); continue; }

        TLorentzVector* u1_4mom  = nullptr;
        TLorentzVector* b1_4mom  = nullptr;
        TLorentzVector* MET_4mom = nullptr;

        in_tree->SetBranchAddress("u1_4mom",  &u1_4mom);
        in_tree->SetBranchAddress("b1_4mom",  &b1_4mom);
        in_tree->SetBranchAddress("MET_4mom", &MET_4mom);

        Long64_t n_entries = in_tree->GetEntries();
        for (Long64_t ievt = 0; ievt < n_entries; ++ievt) {
            in_tree->GetEntry(ievt);

            auto d = ComputeDerived(*u1_4mom, *b1_4mom, *MET_4mom);

            b_u1PT        = d.u1PT;
            b_b1PT        = d.b1PT;
            b_METPt       = d.METPt;
            b_u1Eta       = d.u1Eta;
            b_b1Eta       = d.b1Eta;
            b_ubDeltaR    = d.ubDeltaR;
            b_ubDeltaPhi  = d.ubDeltaPhi;
            b_bMETDeltaPhi= d.bMETDeltaPhi;
            b_METuDeltaPhi= d.METuDeltaPhi;
            b_METuDeltaMt = d.METuDeltaMt;

            out_tree->Fill();
        }

        fin->Close();
    }

    fout->Write();
    fout->Close();
    std::cout << "  → saved: " << out_fname << "\n";
}

// ============================================================
// 6. main
// ============================================================
int main(int argc, char** argv) {
    bool do_split = false;
    std::vector<std::string> pos;

    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--split") do_split = true;
        else pos.push_back(a);
    }

    if (pos.size() < 3) {
        std::cerr << "Usage: " << argv[0]
                  << " [--split] <version> <in_dir> <out_dir>\n";
        return 1;
    }

    std::string version = pos[0];
    std::string in_dir  = pos[1];
    std::string out_dir = pos[2];

    if (!fs::exists(in_dir)) {
        std::cerr << "[ERROR] in_dir 없음: " << in_dir << "\n";
        return 1;
    }

    fs::create_directories(out_dir);

    auto groups = GroupFiles(in_dir, version);
    std::cout << "[INFO] " << groups.size() << " samples found in " << in_dir << "\n\n";

    if (!do_split) {
        for (auto& [sample_key, parsed_files] : groups) {
            std::vector<std::string> files;
            for (auto& pf : parsed_files) files.push_back(pf.filepath);
            ProcessSample(sample_key, files, out_dir, version);
        }
    } else {
        fs::path bdt_dir  = fs::path(out_dir) / "BDTdata";
        fs::path data_dir = fs::path(out_dir) / "data";
        fs::create_directories(bdt_dir);
        fs::create_directories(data_dir);

        for (auto& [sample_key, parsed_files] : groups) {
            auto plan = MakeSplitPlan(sample_key, parsed_files);

            std::cout << "[SPLIT] " << sample_key
                      << " total=" << plan.total_entries
                      << " target=" << plan.target_entries
                      << " isSig=" << plan.isSig
                      << " isSigTarget=" << plan.isSigTarget
                      << " | BDT=" << plan.bdt_files.size()
                      << " files, DATA=" << plan.data_files.size()
                      << " files\n";

            if (!plan.bdt_files.empty())
                ProcessSample(sample_key, plan.bdt_files, bdt_dir.string(), version);

            if (!plan.data_files.empty())
                ProcessSample(sample_key, plan.data_files, data_dir.string(), version);
        }
    }

    std::cout << "\n[DONE]\n";
    return 0;
}
