// A tiny test harness: enough to assert and report, no dependencies.
#pragma once

#include <iostream>
#include <string>

namespace ss::test {

inline int& failures() {
    static int n = 0;
    return n;
}
inline int& checks() {
    static int n = 0;
    return n;
}

inline void check(bool cond, const std::string& what, const char* file,
                  int line) {
    ++checks();
    if (!cond) {
        ++failures();
        std::cerr << "FAIL " << file << ":" << line << "  " << what << "\n";
    }
}

inline int report() {
    std::cout << checks() << " checks, " << failures() << " failed\n";
    return failures() == 0 ? 0 : 1;
}

}  // namespace ss::test

#define CHECK(cond) ::ss::test::check((cond), #cond, __FILE__, __LINE__)
#define CHECK_EQ(a, b)                                                      \
    ::ss::test::check((a) == (b), #a " == " #b, __FILE__, __LINE__)
