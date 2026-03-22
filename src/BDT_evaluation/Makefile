CXX      := g++
CXXFLAGS := -O2 -Wall -Wextra -std=c++20
ROOTCFLAGS := $(shell root-config --cflags)
ROOTLIBS   := $(shell root-config --glibs)
TMVALIBS   := -lTMVA

TARGET := apply_bdt
SRC    := apply_bdt.cpp

all: $(TARGET)

$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) $(ROOTCFLAGS) -o $@ $< $(ROOTLIBS) $(TMVALIBS)

clean:
	rm -f $(TARGET)
