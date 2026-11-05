CXX ?= g++
CXXFLAGS ?= -std=c++17 -O2 -pthread -Wall -Wextra

HEADERS := $(wildcard src/*.hpp)

app: app.cpp $(HEADERS)
	$(CXX) $(CXXFLAGS) app.cpp -o app

test_main: tests/test_main.cpp $(HEADERS) tests/check.hpp
	$(CXX) $(CXXFLAGS) tests/test_main.cpp -o test_main

test: test_main
	./test_main

clean:
	rm -f app test_main

.PHONY: test clean
