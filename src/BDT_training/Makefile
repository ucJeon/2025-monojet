CXX      = g++
CXXFLAGS = $(shell root-config --cflags) -O2 -Wall
LIBS     = $(shell root-config --libs) -lTMVA

TARGET   = bdt_training
SRC      = bdt_training.cpp
LDFLAGS  = -Wl,-rpath,$(shell root-config --libdir)

$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) -o $@ $< $(LIBS) $(LDFLAGS)

clean:
	rm -f $(TARGET)