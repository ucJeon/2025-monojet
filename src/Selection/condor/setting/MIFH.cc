/**
 * make_inputs_from_mc.cpp
 *
 * MC HDFS 디렉토리를 스캔하여 GenHisto용 input 파일 생성
 *
 * 파일명 형식 : {sample}.{sub_idx}.{parallel}.root
 *   e.g.  wjets.3.7.root  →  sample=wjets, sub_idx=3, parallel=7
 * 출력 형식  : {filename},{replica1_hostname},{replica2_hostname}
 * 출력 파일  : inputs.monojetSelectionDiet.{sample}.{sub_idx}.txt
 *
 * Compile:
 *   g++ -O2 -std=c++17 -o make_inputs_from_mc make_inputs_from_mc.cpp
 *
 * Usage:
 *   ./make_inputs_from_mc
 *   ./make_inputs_from_mc --mc-dir /hdfs/user/ujeon/monojet/mc/v1.2.0
 *   ./make_inputs_from_mc --test       # 각 그룹 첫 번째 파일만 처리
 */

#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace fs = std::filesystem;

// ── 경로 설정 ──────────────────────────────────────────────────────────────────
const std::string MC_DIR     = "/hdfs/user/ujeon/monojet/mc/v1.1.0";
const std::string OUTPUT_DIR = "/users/ujeon/2025-monojet/MONOJET-WORKSPACE/src/Selection/condor/inputs";

// ── 유틸: 명령어 실행 후 stdout 반환 ──────────────────────────────────────────
std::string exec(const std::string& cmd) {
    std::array<char, 256> buf;
    std::string result;
    std::unique_ptr<FILE, decltype(&pclose)> pipe(popen(cmd.c_str(), "r"), pclose);
    if (!pipe) throw std::runtime_error("popen() 실패: " + cmd);
    while (fgets(buf.data(), buf.size(), pipe.get()) != nullptr)
        result += buf.data();
    return result;
}

// ── 문자열 split ──────────────────────────────────────────────────────────────
std::vector<std::string> split(const std::string& s, char delim) {
    std::vector<std::string> tokens;
    std::istringstream ss(s);
    std::string tok;
    while (std::getline(ss, tok, delim))
        tokens.push_back(tok);
    return tokens;
}

// ── trim ──────────────────────────────────────────────────────────────────────
std::string trim(const std::string& s) {
    size_t a = s.find_first_not_of(" \t\r\n");
    size_t b = s.find_last_not_of(" \t\r\n");
    return (a == std::string::npos) ? "" : s.substr(a, b - a + 1);
}

// ── hdfs dfs -ls 파싱 → {fname, fpath} 목록 ──────────────────────────────────
struct FileEntry {
    std::string name;
    std::string path;
};

std::vector<FileEntry> hdfs_ls(const std::string& path) {
    std::string out = exec("hdfs dfs -ls " + path + " 2>&1");
    std::vector<FileEntry> entries;

    for (auto& line : split(out, '\n')) {
        if (line.empty() || line[0] == 'd' || line.rfind("Found", 0) == 0)
            continue;
        auto parts = split(line, ' ');
        // 공백 토큰 제거
        parts.erase(std::remove_if(parts.begin(), parts.end(),
                    [](const std::string& s){ return s.empty(); }), parts.end());
        // 형식: permissions rep owner group size date time path (8개)
        if (parts.size() < 8) continue;

        std::string fpath = parts[7];
        std::string fname = fpath.substr(fpath.rfind('/') + 1);

        if (fname.size() < 5 || fname.substr(fname.size() - 5) != ".root")
            continue;

        entries.push_back({fname, fpath});
    }
    return entries;
}

// ── hdfs fsck 로 replica hostname 목록 반환 ───────────────────────────────────
// hdfs fsck <internal_path> -files -blocks -locations 출력에서
// DatanodeInfoWithStorage[hostname/ip:port, ...] 패턴 파싱
std::vector<std::string> get_replica_nodes(const std::string& hdfs_path) {
    // /hdfs/... → /... (internal path)
    std::string internal = hdfs_path;
    if (internal.rfind("/hdfs/", 0) == 0)
        internal = internal.substr(5);   // "/hdfs" 제거

    std::string cmd = "hdfs fsck " + internal + " -files -blocks -locations 2>/dev/null";
    std::string out;
    try { out = exec(cmd); }
    catch (...) { return {}; }

    // DatanodeInfoWithStorage[dn27.sscc.uos/10.10.x.x:port, ...]
    std::regex re(R"(DatanodeInfoWithStorage\[([^/\]]+))");
    std::vector<std::string> hostnames;
    std::sregex_iterator it(out.begin(), out.end(), re), end;
    for (; it != end; ++it)
        hostnames.push_back((*it)[1].str());

    // 중복 제거 (순서 유지)
    std::vector<std::string> unique_nodes;
    for (auto& h : hostnames)
        if (std::find(unique_nodes.begin(), unique_nodes.end(), h) == unique_nodes.end())
            unique_nodes.push_back(h);

    return unique_nodes;
}

// ── 그룹 키: (sample, sub_idx) ────────────────────────────────────────────────
struct GroupKey {
    std::string sample;
    std::string sub_idx;
    bool operator<(const GroupKey& o) const {
        if (sample != o.sample) return sample < o.sample;
        // sub_idx 숫자 정렬
        try {
            int a = std::stoi(sub_idx), b = std::stoi(o.sub_idx);
            return a < b;
        } catch (...) { return sub_idx < o.sub_idx; }
    }
};

struct FileInfo {
    int         parallel;
    std::string fname;
    std::string fpath;
};

// ── main ──────────────────────────────────────────────────────────────────────
int main(int argc, char* argv[]) {
    std::string mc_dir     = MC_DIR;
    std::string output_dir = OUTPUT_DIR;
    bool        test_mode  = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--mc-dir"  && i + 1 < argc) mc_dir     = argv[++i];
        if (arg == "--out-dir" && i + 1 < argc) output_dir = argv[++i];
        if (arg == "--test")                     test_mode  = true;
        if (arg == "--help") {
            std::cout << "Usage: ./make_inputs_from_mc [--mc-dir PATH] [--out-dir PATH] [--test]\n";
            return 0;
        }
    }

    std::cout << "###################################################################\n"
              << "#        GenHisto Input 파일 생성 (MC + replica node)               #\n"
              << "###################################################################\n\n"
              << "MC 디렉토리 : " << mc_dir     << "\n"
              << "출력 디렉토리: " << output_dir << "\n\n";

    // ── 1. MC 파일 목록 수집 ───────────────────────────────────────────────────
    std::cout << "[1/3] MC 파일 목록 수집 중...\n";
    auto entries = hdfs_ls(mc_dir);
    std::cout << "      -> " << entries.size() << "개 .root 파일 발견\n\n";

    // ── 2. (sample, sub_idx) 기준으로 분류 & parallel 정렬 ────────────────────
    std::map<GroupKey, std::vector<FileInfo>> group_map;

    for (auto& e : entries) {
        auto parts = split(e.name, '.');
        // 형식: sample.sub_idx.parallel.root → 최소 4 토큰
        if (parts.size() < 4) {
            std::cerr << "  ⚠  파일명 형식 오류, 건너뜀: " << e.name << "\n";
            continue;
        }
        std::string sample  = parts[0];
        std::string sub_idx = parts[1];
        int parallel;
        try { parallel = std::stoi(parts[2]); }
        catch (...) {
            std::cerr << "  ⚠  parallel idx 파싱 실패, 건너뜀: " << e.name << "\n";
            continue;
        }
        group_map[{sample, sub_idx}].push_back({parallel, e.name, e.path});
    }

    // parallel 오름차순 정렬
    for (auto& [key, vec] : group_map)
        std::sort(vec.begin(), vec.end(),
                  [](const FileInfo& a, const FileInfo& b){ return a.parallel < b.parallel; });

    // ── 3. replica 조회 & 파일 저장 ───────────────────────────────────────────
    fs::create_directories(output_dir);
    std::cout << "[2/3] replica node 조회 및 파일 저장 중...\n\n";

    int g_idx = 0, total = (int)group_map.size();
    for (auto& [key, file_list] : group_map) {
        ++g_idx;
        auto& [sample, sub_idx] = key;
        auto  work_list = file_list;
        if (test_mode && work_list.size() > 1)
            work_list.resize(1);

        std::cout << "  [" << g_idx << "/" << total << "] "
                  << sample << "." << sub_idx
                  << "  (" << work_list.size() << "개 파일)\n";

        std::vector<std::string> rows;
        for (int i = 0; i < (int)work_list.size(); ++i) {
            auto& fi = work_list[i];
            std::cout << "    " << (i+1) << "/" << work_list.size()
                      << "  " << fi.fname << "  " << std::flush;

            auto nodes = get_replica_nodes(fi.fpath);

            // row 조립
            std::string row = fi.fname;
            for (auto& n : nodes) row += "," + n;
            rows.push_back(row);

            // 출력
            std::cout << "-> [";
            for (int j = 0; j < (int)nodes.size(); ++j) {
                if (j) std::cout << ", ";
                std::cout << nodes[j];
            }
            std::cout << "]\n";
        }

        // 파일 저장
        std::string out_path = output_dir + "/inputs.monojetSelectionDiet."
                               + sample + "." + sub_idx + ".txt";
        std::ofstream ofs(out_path);
        if (!ofs) {
            std::cerr << "  ❌ 파일 저장 실패: " << out_path << "\n";
            continue;
        }
        for (auto& row : rows) ofs << row << "\n";
        std::cout << "  ✅ 저장: " << out_path << "\n\n";
    }

    std::cout << "[3/3] 완료. 총 " << total << "개 그룹 처리.\n";
    return 0;
}
