# Makefile
# Usage:
#   make        → v2  (CMS 스타일, default)
#   make V=1    → v1  (기존 방식)
#   make V=2    → v2  (CMS 스타일) <- selected
#   make V=21   → v21 (+morethan 1 jets)
#   make clean

CXX      := g++
CXXFLAGS := -O2 -std=c++17 -Wall

# ROOT / Delphes 경로 (환경에 맞게 수정)
ROOT_CFLAGS  := $(shell root-config --cflags)
ROOT_LIBS    := $(shell root-config --libs)
DELPHES_DIR  ?= /users/ujeon/2025-monojet/condor/3.DelphesStep/analyzer/delphes
DELPHES_INC  := -I$(DELPHES_DIR)
DELPHES_LIB  := -L$(DELPHES_DIR) -lDelphes -Wl,-rpath,$(DELPHES_DIR)

# 버전 선택 (default: 2)
V ?= 2

TARGET  := main
SRCS    := main.cpp
HEADERS := xs_map.hpp object_selection.hpp event_selection.hpp main.hpp

$(TARGET): $(SRCS) $(HEADERS)
	$(CXX) $(CXXFLAGS) $(ROOT_CFLAGS) $(DELPHES_INC) \
	    -DSEL_VERSION=$(V) \
	    -o $@ $(SRCS) \
	    $(ROOT_LIBS) $(DELPHES_LIB)
	@echo "Built $(TARGET) with SEL_VERSION=$(V)"

clean:
	rm -f $(TARGET) cutflow_*.csv

.PHONY: clean
