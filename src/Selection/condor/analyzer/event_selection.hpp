#pragma once
// event_selection.hpp
// Event-level selection 모듈
//
// [버전 구조]
//   namespace EvtSel::v1  ←  기존 5단계 (원본 코드)
//   namespace EvtSel::v2  ←  CMS 스타일 7단계
//
// [새 버전 추가 방법]
//   1. namespace EvtSel::v3 { ... } 블록 추가
//   2. EventSelResult에 필요한 카운터 추가
//   3. main에서 RunEventSelection = EvtSel::v3::Run 으로 스위치
// ============================================================

#include <vector>
#include <string>
#include <cmath>
#include <TLorentzVector.h>
#include "object_selection.hpp"

// ============================================================
// 공통: 이벤트 루프 결과 (cut별 raw count)
// 버전마다 사용하는 카운터가 다를 수 있으므로 전부 보유
// ============================================================
struct EventSelResult {
    // ---- 공통 ----
    Long64_t n_generated = 0;

    // ---- v1 (5단계) ----
    Long64_t n_lep       = 0;  // lepton veto
    Long64_t n_ujet      = 0;  // nQJet >= 1 (v1: !isB && pT>150)
    Long64_t n_qjet      = 0;  // nBJet==1 && nQJet==1
    Long64_t n_met       = 0;  // MET > 150
    Long64_t n_sel       = 0;  // 최종 (= n_met in v1)

    // ---- v2 추가 단계 ----
    Long64_t n_ge1_qjet  = 0;  // ≥1 qjet (overlap 제거 후)
    Long64_t n_eq1_qjet  = 0;  // ==1 qjet
    Long64_t n_eq1_bjet  = 0;  // ==1 bjet (qjet과 독립)
    // n_met, n_sel 공용

    // ---- 선택된 이벤트 4-momentum (sel 통과한 이벤트만) ----
    std::vector<TLorentzVector> u1_4moms;   // leading qjet
    std::vector<TLorentzVector> b1_4moms;   // leading bjet
    std::vector<TLorentzVector> met_4moms;  // MET (eta=0, mass=0)

    // ---- 버전 태그 ----
    std::string version;
};

// ============================================================
// namespace EvtSel::v1
// 기존 5단계: generated → lveto → ujet → qjet → met → sel
// ============================================================
namespace EvtSel {
namespace v1 {

    inline std::vector<std::string> CutNames() {
        return {"generated", "l_veto", "ujet", "qjet", "met", "sel"};
    }

    inline std::vector<Long64_t> GetCounts(const EventSelResult& r) {
        return {r.n_generated, r.n_lep, r.n_ujet,
                r.n_qjet, r.n_met, r.n_sel};
    }

    inline EventSelResult Run(TChain& chain,
                               TClonesArray* branchJet,
                               TClonesArray* branchElec,
                               TClonesArray* branchMuon,
                               TClonesArray* branchMissingET) {
        EventSelResult res;
        res.version      = "v1";
        res.n_generated  = chain.GetEntries();

        for (Long64_t ievt = 0; ievt < res.n_generated; ++ievt) {
            chain.GetEntry(ievt);

            auto lep = ObjSel::v1::CountVetoLeptons(branchElec, branchMuon, branchJet);
            if (lep.nTotal() != 0) continue;
            ++res.n_lep;

            auto jets = ObjSel::v1::SelectJets(branchJet);
            if (jets.qjets.size() >= 1) ++res.n_ujet;
            if (jets.bjets.size() != 1 || jets.qjets.size() != 1) continue;
            ++res.n_qjet;

            auto met = ObjSel::v1::GetMET(branchMissingET);
            if (met.pt <= 150.f) continue;
            ++res.n_met;

            ++res.n_sel;

            TLorentzVector u1, b1, met4;
            u1.SetPtEtaPhiM(jets.qjets[0]->PT, jets.qjets[0]->Eta,
                             jets.qjets[0]->Phi, jets.qjets[0]->Mass);
            b1.SetPtEtaPhiM(jets.bjets[0]->PT, jets.bjets[0]->Eta,
                             jets.bjets[0]->Phi, jets.bjets[0]->Mass);
            met4.SetPtEtaPhiM(met.pt, 0., met.phi, 0.);
            res.u1_4moms.push_back(u1);
            res.b1_4moms.push_back(b1);
            res.met_4moms.push_back(met4);
        }
        return res;
    }

} // namespace v1

// ============================================================
// namespace EvtSel::v2
// CMS 스타일 7단계:
//   generated → l_veto → ≥1 qjet → ==1 qjet → ==1 bjet → met → sel
// ============================================================
namespace v2 {

    inline std::vector<std::string> CutNames() {
        return {"generated", "l_veto",
                "ge1_qjet", "eq1_qjet", "eq1_bjet",
                "met", "sel"};
    }

    inline std::vector<Long64_t> GetCounts(const EventSelResult& r) {
        return {r.n_generated, r.n_lep,
                r.n_ge1_qjet, r.n_eq1_qjet, r.n_eq1_bjet,
                r.n_met, r.n_sel};
    }

    inline EventSelResult Run(TChain& chain,
                               TClonesArray* branchJet,
                               TClonesArray* branchElec,
                               TClonesArray* branchMuon,
                               TClonesArray* branchMissingET) {
        EventSelResult res;
        res.version     = "v2";
        res.n_generated = chain.GetEntries();

        for (Long64_t ievt = 0; ievt < res.n_generated; ++ievt) {
            chain.GetEntry(ievt);

            auto lep       = ObjSel::v2::CountVetoLeptons(branchElec, branchMuon, branchJet);
            auto bjets     = ObjSel::v2::SelectBJets(branchJet);
            auto qjets_raw = ObjSel::v2::SelectQJets(branchJet);
            auto qjets     = ObjSel::v2::RemoveBJetOverlap(qjets_raw, bjets);
            auto met       = ObjSel::v2::GetMET(branchMissingET);

            if (lep.nTotal() != 0) continue;
            ++res.n_lep;

            if (qjets.empty()) continue;
            ++res.n_ge1_qjet;

            if (qjets.size() != 1) continue;
            ++res.n_eq1_qjet;

            if (bjets.size() != 1) continue;
            ++res.n_eq1_bjet;

            if (met.pt <= 150.f) continue;
            ++res.n_met;

            ++res.n_sel;

            // ── 4-momentum 저장 ──
            TLorentzVector u1, b1, met4;
            u1.SetPtEtaPhiM(qjets[0]->PT, qjets[0]->Eta,
                             qjets[0]->Phi, qjets[0]->Mass);
            b1.SetPtEtaPhiM(bjets[0]->PT, bjets[0]->Eta,
                             bjets[0]->Phi, bjets[0]->Mass);
            met4.SetPtEtaPhiM(met.pt, 0., met.phi, 0.);
            res.u1_4moms.push_back(u1);
            res.b1_4moms.push_back(b1);
            res.met_4moms.push_back(met4);
        }
        return res;
    }

} // namespace v2

// ============================================================
// namespace EvtSel::v21
//   generated → l_veto → ≥1 qjet → ≥1 bjet → met → sel
// ============================================================
namespace v21 {

    inline std::vector<std::string> CutNames() {
        return {"generated", "l_veto",
                "ge1_qjet", "eq1_qjet", "eq1_bjet",
                "met", "sel"};
    }

    inline std::vector<Long64_t> GetCounts(const EventSelResult& r) {
        return {r.n_generated, r.n_lep,
                r.n_ge1_qjet, r.n_eq1_qjet, r.n_eq1_bjet,
                r.n_met, r.n_sel};
    }

    inline EventSelResult Run(TChain& chain,
                               TClonesArray* branchJet,
                               TClonesArray* branchElec,
                               TClonesArray* branchMuon,
                               TClonesArray* branchMissingET) {
        EventSelResult res;
        res.version     = "v21";
        res.n_generated = chain.GetEntries();

        for (Long64_t ievt = 0; ievt < res.n_generated; ++ievt) {
            chain.GetEntry(ievt);

            auto lep       = ObjSel::v2::CountVetoLeptons(branchElec, branchMuon, branchJet);
            auto bjets     = ObjSel::v21::SelectBJets(branchJet);
            auto qjets_raw = ObjSel::v21::SelectQJets(branchJet);
            auto qjets     = ObjSel::v21::RemoveBJetOverlap(qjets_raw, bjets);
            auto met       = ObjSel::v21::GetMET(branchMissingET);

            if (lep.nTotal() != 0) continue;
            ++res.n_lep;

            if (qjets.empty()) continue;
            ++res.n_ge1_qjet;
            ++res.n_eq1_qjet;  // 무조건 만족

            if (bjets.empty()) continue;
            ++res.n_eq1_bjet;

            if (met.pt <= 150.f) continue;
            ++res.n_met;

            ++res.n_sel;

            // ── 4-momentum 저장 ──
            TLorentzVector u1, b1, met4;
            u1.SetPtEtaPhiM(qjets[0]->PT, qjets[0]->Eta,
                             qjets[0]->Phi, qjets[0]->Mass);
            b1.SetPtEtaPhiM(bjets[0]->PT, bjets[0]->Eta,
                             bjets[0]->Phi, bjets[0]->Mass);
            met4.SetPtEtaPhiM(met.pt, 0., met.phi, 0.);
            res.u1_4moms.push_back(u1);
            res.b1_4moms.push_back(b1);
            res.met_4moms.push_back(met4);
        }
        return res;
    }

} // namespace v21

} // namespace EvtSel
