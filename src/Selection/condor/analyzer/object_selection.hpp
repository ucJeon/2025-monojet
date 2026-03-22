#pragma once
// object_selection.hpp
// Object-level selection 모듈
//
// [버전 구조]
//   namespace ObjSel::v1  ←  기존 방식 (원본 코드 그대로)
//   namespace ObjSel::v2  ←  CMS 스타일 (object sel / event sel 명확히 분리)
//
// [새 버전 추가 방법]
//   1. namespace ObjSel::v3 { ... } 블록 추가
//   2. main에서 using namespace ObjSel::v3; 으로 스위치
// ============================================================

#include <vector>
#include <cmath>
#include "classes/DelphesClasses.h"
#include "TClonesArray.h"

// ============================================================
// 공통 결과 구조체
// ============================================================
struct SelJets {
    std::vector<Jet*> bjets;   // b-tagged jets (pT 내림차순 정렬)
    std::vector<Jet*> qjets;   // light jets     (pT 내림차순 정렬)
};

struct SelLeptons {
    int nElec   = 0;
    int nMuon   = 0;
    int nTau_h  = 0;
    int nTotal() const { return nElec + nMuon + nTau_h; }
};

struct SelMET {
    double pt  = 0.;
    double phi = 0.;
};

// ============================================================
// namespace ObjSel::v1
// 기존 방식: bjet/qjet을 한 루프에서 동시에 결정
// isQ = (!isB) 로 정의 → bjet이 먼저 결정되어야 qjet 판별 가능
// ============================================================
namespace ObjSel {
namespace v1 {

    // [v1] Jet selection
    // bjet: BTag==1 && pT>20 && |η|<2.4
    // qjet: !bjet  && pT>150 && |η|<2.4
    // → 두 조건이 한 루프에서 coupled되어 있음
    inline SelJets SelectJets(TClonesArray* branchJet) {
        SelJets res;
        if (!branchJet) return res;

        int nJ = branchJet->GetEntriesFast();
        for (int j = 0; j < nJ; ++j) {
            Jet* jet = (Jet*) branchJet->At(j);
            if (!jet) continue;

            bool isB = (jet->BTag == 1)
                    && (jet->PT   > 20.f)
                    && (std::abs(jet->Eta) < 2.4f);
            bool isQ = (!isB)
                    && (jet->PT   > 150.f)
                    && (std::abs(jet->Eta) < 2.4f);

            if (isB) res.bjets.push_back(jet);
            if (isQ) res.qjets.push_back(jet);
        }
        // pT 내림차순 정렬
        auto byPt = [](Jet* a, Jet* b){ return a->PT > b->PT; };
        std::sort(res.bjets.begin(), res.bjets.end(), byPt);
        std::sort(res.qjets.begin(), res.qjets.end(), byPt);
        return res;
    }

    // [v1] Lepton veto object counting
    // e/μ: pT>10 && |η|<2.4
    // τ_h: TauTag==1 && pT>10 && |η|<2.4
    inline SelLeptons CountVetoLeptons(TClonesArray* branchElec,
                                       TClonesArray* branchMuon,
                                       TClonesArray* branchJet) {
        SelLeptons res;
        if (branchElec) {
            int n = branchElec->GetEntriesFast();
            for (int i = 0; i < n; ++i) {
                auto* el = (Electron*) branchElec->At(i);
                if (!el) continue;
                if (el->PT > 10.f && std::abs(el->Eta) < 2.4f) ++res.nElec;
            }
        }
        if (branchMuon) {
            int n = branchMuon->GetEntriesFast();
            for (int i = 0; i < n; ++i) {
                auto* mu = (Muon*) branchMuon->At(i);
                if (!mu) continue;
                if (mu->PT > 10.f && std::abs(mu->Eta) < 2.4f) ++res.nMuon;
            }
        }
        if (branchJet) {
            int n = branchJet->GetEntriesFast();
            for (int j = 0; j < n; ++j) {
                auto* jet = (Jet*) branchJet->At(j);
                if (!jet) continue;
                if (jet->TauTag == 1
                    && jet->PT > 10.f
                    && std::abs(jet->Eta) < 2.4f) ++res.nTau_h;
            }
        }
        return res;
    }

    // [v1] MET object
    inline SelMET GetMET(TClonesArray* branchMissingET) {
        SelMET res;
        if (!branchMissingET || branchMissingET->GetEntriesFast() == 0) return res;
        auto* met = (MissingET*) branchMissingET->At(0);
        if (met) { res.pt = met->MET; res.phi = met->Phi; }
        return res;
    }

} // namespace v1

// ============================================================
// namespace ObjSel::v2
// CMS 스타일: Object Selection / Event Selection 명확히 분리
//
// 변경점 vs v1:
//   - bjet / qjet 선택을 독립된 함수로 분리
//   - qjet 정의에서 "!isB" coupling 제거
//     → qjet은 자체 기준(pT, η, JetID)만으로 판별
//     → b-jet과 overlap은 Event Selection 단계에서 처리
//   - 향후 Jet ID WP, isolation 추가 시 이 함수만 수정
// ============================================================
namespace v2 {

    // [v2] b-jet object selection
    // CMS DeepJet Medium WP 기준 (Delphes: BTag==1로 근사)
    // pT > 20 GeV, |η| < 2.4
    inline std::vector<Jet*> SelectBJets(TClonesArray* branchJet) {
        std::vector<Jet*> res;
        if (!branchJet) return res;

        int nJ = branchJet->GetEntriesFast();
        for (int j = 0; j < nJ; ++j) {
            Jet* jet = (Jet*) branchJet->At(j);
            if (!jet) continue;
            if (jet->BTag == 1
                && jet->PT  > 20.f
                && std::abs(jet->Eta) < 2.4f)
                res.push_back(jet);
        }
        std::sort(res.begin(), res.end(),
                  [](Jet* a, Jet* b){ return a->PT > b->PT; });
        return res;
    }

    // [v2] light jet (ujet / qjet) object selection
    // bjet과 독립적으로 판별 (coupling 제거)
    // pT > 150 GeV, |η| < 2.4
    // → b-jet overlap 제거는 아래 RemoveBJetOverlap() 에서 수행
    inline std::vector<Jet*> SelectQJets(TClonesArray* branchJet) {
        std::vector<Jet*> res;
        if (!branchJet) return res;

        int nJ = branchJet->GetEntriesFast();
        for (int j = 0; j < nJ; ++j) {
            Jet* jet = (Jet*) branchJet->At(j);
            if (!jet) continue;
            if (jet->PT  > 150.f
                && std::abs(jet->Eta) < 2.4f)
                res.push_back(jet);
        }
        std::sort(res.begin(), res.end(),
                  [](Jet* a, Jet* b){ return a->PT > b->PT; });
        return res;
    }

    // [v2] qjet에서 bjet overlap 제거
    // 같은 Jet 포인터면 제거 (ΔR 기반 매칭으로 교체 가능)
    inline std::vector<Jet*> RemoveBJetOverlap(
            const std::vector<Jet*>& qjets,
            const std::vector<Jet*>& bjets) {
        std::vector<Jet*> res;
        for (auto* qj : qjets) {
            bool overlap = false;
            for (auto* bj : bjets) {
                if (qj == bj) { overlap = true; break; }
            }
            if (!overlap) res.push_back(qj);
        }
        return res;
    }

    // [v2] Lepton veto object counting (v1과 동일 기준, 함수 독립)
    inline SelLeptons CountVetoLeptons(TClonesArray* branchElec,
                                       TClonesArray* branchMuon,
                                       TClonesArray* branchJet) {
        // 기준 동일 → v1 구현 재사용
        return v1::CountVetoLeptons(branchElec, branchMuon, branchJet);
    }

    // [v2] MET object (v1과 동일)
    inline SelMET GetMET(TClonesArray* branchMissingET) {
        return v1::GetMET(branchMissingET);
    }

} // namespace v21

namespace v21 {

    // [v2] b-jet object selection
    // CMS DeepJet Medium WP 기준 (Delphes: BTag==1로 근사)
    // pT > 20 GeV, |η| < 2.4
    inline std::vector<Jet*> SelectBJets(TClonesArray* branchJet) {
        std::vector<Jet*> res;
        if (!branchJet) return res;

        int nJ = branchJet->GetEntriesFast();
        for (int j = 0; j < nJ; ++j) {
            Jet* jet = (Jet*) branchJet->At(j);
            if (!jet) continue;
            if (jet->BTag == 1
                && jet->PT  > 20.f
                && std::abs(jet->Eta) < 2.4f)
                res.push_back(jet);
        }
        std::sort(res.begin(), res.end(),
                  [](Jet* a, Jet* b){ return a->PT > b->PT; });
        return res;
    }

    // [v2] light jet (ujet / qjet) object selection
    // bjet과 독립적으로 판별 (coupling 제거)
    // pT > 150 GeV, |η| < 2.4
    // → b-jet overlap 제거는 아래 RemoveBJetOverlap() 에서 수행
    inline std::vector<Jet*> SelectQJets(TClonesArray* branchJet) {
        std::vector<Jet*> res;
        if (!branchJet) return res;

        int nJ = branchJet->GetEntriesFast();
        for (int j = 0; j < nJ; ++j) {
            Jet* jet = (Jet*) branchJet->At(j);
            if (!jet) continue;
            if (jet->PT  > 150.f
                && std::abs(jet->Eta) < 2.4f)
                res.push_back(jet);
        }
        std::sort(res.begin(), res.end(),
                  [](Jet* a, Jet* b){ return a->PT > b->PT; });
        return res;
    }

    // [v2] qjet에서 bjet overlap 제거
    // 같은 Jet 포인터면 제거 (ΔR 기반 매칭으로 교체 가능)
    inline std::vector<Jet*> RemoveBJetOverlap(
            const std::vector<Jet*>& qjets,
            const std::vector<Jet*>& bjets) {
        std::vector<Jet*> res;
        for (auto* qj : qjets) {
            bool overlap = false;
            for (auto* bj : bjets) {
                if (qj == bj) { overlap = true; break; }
            }
            if (!overlap) res.push_back(qj);
        }
        return res;
    }

    // [v2] Lepton veto object counting (v1과 동일 기준, 함수 독립)
    inline SelLeptons CountVetoLeptons(TClonesArray* branchElec,
                                       TClonesArray* branchMuon,
                                       TClonesArray* branchJet) {
        // 기준 동일 → v1 구현 재사용
        return v1::CountVetoLeptons(branchElec, branchMuon, branchJet);
    }

    // [v2] MET object (v1과 동일)
    inline SelMET GetMET(TClonesArray* branchMissingET) {
        return v1::GetMET(branchMissingET);
    }

} // namespace v21
} // namespace ObjSel
