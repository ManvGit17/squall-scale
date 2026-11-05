// Unit tests for the backend's pure logic: request-line parsing and the
// Prometheus metrics rendering. No sockets, no threads.

#include "../src/http.hpp"
#include "../src/metrics.hpp"
#include "check.hpp"

#include <string>

static void test_parse_request_line() {
    using ss::http::parse_request_line;

    auto get = parse_request_line("GET /metrics HTTP/1.1\r\nHost: x\r\n\r\n");
    CHECK_EQ(get.method, std::string("GET"));
    CHECK_EQ(get.path, std::string("/metrics"));

    // Query string is stripped so routing sees the path alone.
    auto q = parse_request_line("GET /?delay=5 HTTP/1.1\r\n");
    CHECK_EQ(q.path, std::string("/"));

    auto post = parse_request_line("POST /save HTTP/1.0\r\n");
    CHECK_EQ(post.method, std::string("POST"));
    CHECK_EQ(post.path, std::string("/save"));

    // Malformed lines yield empty method/path rather than crashing.
    auto bad = parse_request_line("not a request");  // target "a" has no '/'
    CHECK(bad.method.empty());
    CHECK(bad.path.empty());

    auto no_spaces = parse_request_line("garbage");
    CHECK(no_spaces.method.empty());

    auto empty = parse_request_line("");
    CHECK(empty.method.empty());
}

static void test_make_response() {
    const std::string r =
        ss::http::make_response(200, "OK", "text/plain", "hi\n");
    CHECK(r.rfind("HTTP/1.1 200 OK\r\n", 0) == 0);
    CHECK(r.find("Content-Length: 3\r\n") != std::string::npos);
    CHECK(r.find("Connection: close\r\n") != std::string::npos);
    CHECK(r.size() >= 3 && r.substr(r.size() - 3) == "hi\n");
}

static void test_counters_and_render() {
    ss::metrics::Counters c;
    c.request_started();
    c.request_started();
    CHECK_EQ(c.in_flight.load(), 2);
    c.request_finished(1'500'000);  // 1.5s
    CHECK_EQ(c.in_flight.load(), 1);
    CHECK_EQ(c.requests_total.load(), 2);

    const auto snap = c.snapshot("backend-7", 12.5);
    const std::string out = ss::metrics::render_prometheus(snap);

    CHECK(out.find("squallscale_requests_total 2\n") != std::string::npos);
    CHECK(out.find("squallscale_requests_in_flight 1\n") != std::string::npos);
    CHECK(out.find("squallscale_request_duration_seconds_count 1\n") !=
          std::string::npos);
    CHECK(out.find("squallscale_request_duration_seconds_sum 1.5\n") !=
          std::string::npos);
    CHECK(out.find("squallscale_backend_info{host=\"backend-7\"} 1\n") !=
          std::string::npos);
    // Every HELP line should be paired with a TYPE line.
    CHECK(out.find("# TYPE squallscale_uptime_seconds gauge\n") !=
          std::string::npos);
}

static void test_num_formatting() {
    using ss::metrics::num;
    CHECK_EQ(num(1.5), std::string("1.5"));
    CHECK_EQ(num(2.0), std::string("2"));
    CHECK_EQ(num(0.0), std::string("0"));
}

int main() {
    test_parse_request_line();
    test_make_response();
    test_counters_and_render();
    test_num_formatting();
    return ss::test::report();
}
