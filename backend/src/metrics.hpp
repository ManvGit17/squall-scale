// Backend metrics: live counters plus a scrapeable text rendering.
//
// The counters are atomic so worker threads can update them without locking.
// The rendering is a pure function over a plain snapshot, so it can be
// unit-tested without threads or sockets.
#pragma once

#include <atomic>
#include <cstdint>
#include <string>

namespace ss::metrics {

// A point-in-time copy of the counters, safe to format at leisure.
struct Snapshot {
    std::string host;
    std::int64_t requests_total = 0;
    std::int64_t in_flight = 0;
    double duration_seconds_sum = 0.0;
    std::int64_t duration_seconds_count = 0;
    double uptime_seconds = 0.0;
};

// Live counters shared by the worker threads.
struct Counters {
    std::atomic<std::int64_t> requests_total{0};
    std::atomic<std::int64_t> in_flight{0};
    std::atomic<std::int64_t> duration_micros_sum{0};
    std::atomic<std::int64_t> duration_count{0};

    void request_started() {
        requests_total.fetch_add(1, std::memory_order_relaxed);
        in_flight.fetch_add(1, std::memory_order_relaxed);
    }

    void request_finished(std::int64_t micros) {
        in_flight.fetch_sub(1, std::memory_order_relaxed);
        duration_micros_sum.fetch_add(micros, std::memory_order_relaxed);
        duration_count.fetch_add(1, std::memory_order_relaxed);
    }

    Snapshot snapshot(const std::string& host, double uptime_seconds) const {
        Snapshot s;
        s.host = host;
        s.requests_total = requests_total.load(std::memory_order_relaxed);
        s.in_flight = in_flight.load(std::memory_order_relaxed);
        s.duration_seconds_sum =
            duration_micros_sum.load(std::memory_order_relaxed) / 1e6;
        s.duration_seconds_count = duration_count.load(std::memory_order_relaxed);
        s.uptime_seconds = uptime_seconds;
        return s;
    }
};

// Format a double without a trailing newline and without locale surprises.
inline std::string num(double v) {
    std::string s = std::to_string(v);
    // std::to_string gives 6 decimals; trim trailing zeros for readability.
    const std::size_t dot = s.find('.');
    if (dot != std::string::npos) {
        std::size_t last = s.find_last_not_of('0');
        if (last == dot) last = dot - 1;  // drop a bare trailing dot
        s.erase(last + 1);
    }
    return s;
}

// Render the snapshot in Prometheus text exposition format. Any monitor that
// speaks Prometheus can scrape it; the controller parses these same lines.
inline std::string render_prometheus(const Snapshot& s) {
    std::string out;
    out.reserve(512);

    out += "# HELP squallscale_requests_total Requests served (excludes health and metrics).\n";
    out += "# TYPE squallscale_requests_total counter\n";
    out += "squallscale_requests_total " + std::to_string(s.requests_total) + "\n";

    out += "# HELP squallscale_requests_in_flight Requests currently being handled.\n";
    out += "# TYPE squallscale_requests_in_flight gauge\n";
    out += "squallscale_requests_in_flight " + std::to_string(s.in_flight) + "\n";

    out += "# HELP squallscale_request_duration_seconds Cumulative request handling time.\n";
    out += "# TYPE squallscale_request_duration_seconds summary\n";
    out += "squallscale_request_duration_seconds_sum " + num(s.duration_seconds_sum) + "\n";
    out += "squallscale_request_duration_seconds_count " +
           std::to_string(s.duration_seconds_count) + "\n";

    out += "# HELP squallscale_uptime_seconds Seconds since the backend started.\n";
    out += "# TYPE squallscale_uptime_seconds gauge\n";
    out += "squallscale_uptime_seconds " + num(s.uptime_seconds) + "\n";

    out += "# HELP squallscale_backend_info Static labels for this backend.\n";
    out += "# TYPE squallscale_backend_info gauge\n";
    out += "squallscale_backend_info{host=\"" + s.host + "\"} 1\n";

    return out;
}

}  // namespace ss::metrics
