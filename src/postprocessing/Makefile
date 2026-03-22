CXX      := g++
CXXFLAGS := -std=c++17 -O2 -Wall
ROOTFLAGS := $(shell root-config --cflags)
ROOTLIBS  := $(shell root-config --libs)
 
TARGET := postprocess
 
.PHONY: all clean
 
all: $(TARGET)
 
$(TARGET): postprocess.cpp
	$(CXX) $(CXXFLAGS) $(ROOTFLAGS) -o $@ $< $(ROOTLIBS)
 
clean:
	rm -f $(TARGET)
 

