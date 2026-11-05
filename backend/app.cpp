// squallscale backend: a small C++ HTTP server that reports its own load.
//
// It still answers the original greeting on every app path, but now does so
// from a thread pool, measures how long each request takes, and exposes
// /healthz and a Prometheus /metrics endpoint so a controller can scrape its
// load and decide when the fleet needs to grow or shrink. A per-request work
// cost (WORK_MS) makes that load controllable for demonstrations.
//
// Configuration (environment variables, all optional):
//   PORT              listen port                       (default 8080)
//   THREADS           worker threads in the pool        (default 8)
//   MAX_QUEUE         max connections queued for a slot (default 1024)
//   WORK_MS           simulated work per request, ms    (default 0)
//   DRAIN_TIMEOUT_MS  grace to finish in-flight on stop (default 8000)

#include <arpa/inet.h>
#include <poll.h>
#include <signal.h>
#include <unistd.h>

#include <atomic>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>

#include "src/http.hpp"
#include "src/metrics.hpp"
#include "src/threadpool.hpp"

namespace {

std::atomic<bool> g_stop{false};

void on_signal(int) { g_stop.store(true, std::memory_order_relaxed); }

int env_int(const char* name, int fallback) {
    const char* v = std::getenv(name);
    if (v == nullptr || *v == '\0') return fallback;
    char* end = nullptr;
    const long parsed = std::strtol(v, &end, 10);
    if (end == v || parsed < 0) return fallback;
    return static_cast<int>(parsed);
}

bool send_all(int fd, const std::string& data) {
    std::size_t sent = 0;
    while (sent < data.size()) {
        const ssize_t n = ::send(fd, data.data() + sent, data.size() - sent, 0);
        if (n <= 0) return false;
        sent += static_cast<std::size_t>(n);
    }
    return true;
}

// `app healthcheck`: connect to ourselves, hit /healthz, exit 0 if healthy.
// Lets the Docker image run a health check without curl or wget installed.
int run_healthcheck(int port) {
    const int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return 1;
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(static_cast<uint16_t>(port));
    ::inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr);
    if (::connect(fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) {
        ::close(fd);
        return 1;
    }
    const std::string req = "GET /healthz HTTP/1.0\r\n\r\n";
    ::send(fd, req.data(), req.size(), 0);
    char buf[256];
    const ssize_t n = ::recv(fd, buf, sizeof(buf) - 1, 0);
    ::close(fd);
    if (n <= 0) return 1;
    return std::string(buf, static_cast<std::size_t>(n)).find("200") !=
                   std::string::npos
               ? 0
               : 1;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc > 1 && std::string(argv[1]) == "healthcheck") {
        return run_healthcheck(env_int("PORT", 8080));
    }

    const int port = env_int("PORT", 8080);
    const int threads = env_int("THREADS", 8);
    const int max_queue = env_int("MAX_QUEUE", 1024);
    const int work_ms = env_int("WORK_MS", 0);
    const int drain_timeout_ms = env_int("DRAIN_TIMEOUT_MS", 8000);

    char hostname[256] = {0};
    ::gethostname(hostname, sizeof(hostname) - 1);
    const std::string host(hostname);

    ss::metrics::Counters counters;
    const auto started = std::chrono::steady_clock::now();
    auto uptime_seconds = [&started] {
        return std::chrono::duration<double>(
                   std::chrono::steady_clock::now() - started)
            .count();
    };

    // Clean shutdown on container stop (SIGTERM) and Ctrl-C (SIGINT).
    struct sigaction sa {};
    sa.sa_handler = on_signal;
    ::sigaction(SIGTERM, &sa, nullptr);
    ::sigaction(SIGINT, &sa, nullptr);
    ::signal(SIGPIPE, SIG_IGN);  // a client that hangs up must not kill us

    const int server_fd = ::socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd == -1) {
        ::perror("socket");
        return 1;
    }
    int opt = 1;
    ::setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;  // 0.0.0.0
    address.sin_port = htons(static_cast<uint16_t>(port));

    if (::bind(server_fd, reinterpret_cast<sockaddr*>(&address),
               sizeof(address)) < 0) {
        ::perror("bind");
        return 1;
    }
    if (::listen(server_fd, 128) < 0) {
        ::perror("listen");
        return 1;
    }

    ss::ThreadPool pool(static_cast<std::size_t>(threads),
                        static_cast<std::size_t>(max_queue));

    std::cout << "squallscale backend on 0.0.0.0:" << port << " host=" << host
              << " threads=" << pool.worker_count() << " work_ms=" << work_ms
              << std::endl;

    using clock = std::chrono::steady_clock;
    auto handle = [&counters, &host, &uptime_seconds, work_ms](
                      int client_fd, clock::time_point accepted) {
        char buf[4096];
        const ssize_t n = ::recv(client_fd, buf, sizeof(buf) - 1, 0);
        std::string response;
        if (n > 0) {
            buf[n] = '\0';
            const ss::http::Request req =
                ss::http::parse_request_line(std::string_view(buf, n));

            if (req.path == "/healthz") {
                response = ss::http::make_response(200, "OK", "text/plain",
                                                   "ok\n");
            } else if (req.path == "/metrics") {
                const auto snap = counters.snapshot(host, uptime_seconds());
                response = ss::http::make_response(
                    200, "OK", "text/plain; version=0.0.4",
                    ss::metrics::render_prometheus(snap));
            } else {
                // Any application path: count it, do the (simulated) work.
                counters.request_started();
                if (work_ms > 0) {
                    std::this_thread::sleep_for(
                        std::chrono::milliseconds(work_ms));
                }
                response = ss::http::make_response(
                    200, "OK", "text/plain",
                    "Served by backend: " + host + "\n");
                // Latency is measured from acceptance, so it includes time
                // spent waiting in the pool queue — that queue wait is what
                // signals saturation to the autoscaler.
                const auto micros =
                    std::chrono::duration_cast<std::chrono::microseconds>(
                        clock::now() - accepted)
                        .count();
                send_all(client_fd, response);
                ::close(client_fd);
                counters.request_finished(micros);
                return;
            }
        }
        send_all(client_fd, response);
        ::close(client_fd);
    };

    // Accept loop: poll so the loop can notice a stop signal promptly.
    while (!g_stop.load(std::memory_order_relaxed)) {
        pollfd pfd{server_fd, POLLIN, 0};
        const int ready = ::poll(&pfd, 1, 200);
        if (ready <= 0) continue;  // timeout or interrupted; re-check the flag

        const int client_fd = ::accept(server_fd, nullptr, nullptr);
        if (client_fd < 0) continue;
        const auto accepted = clock::now();

        if (!pool.submit([client_fd, accepted, &handle] {
                handle(client_fd, accepted);
            })) {
            // Pool saturated: shed the load rather than queue without bound.
            const std::string busy = ss::http::make_response(
                503, "Service Unavailable", "text/plain", "busy\n");
            send_all(client_fd, busy);
            ::close(client_fd);
        }
    }

    // Stop accepting, then let in-flight requests drain within the grace window.
    std::cout << "draining..." << std::endl;
    ::close(server_fd);
    const auto deadline = std::chrono::steady_clock::now() +
                          std::chrono::milliseconds(drain_timeout_ms);
    while (counters.in_flight.load(std::memory_order_relaxed) > 0 &&
           std::chrono::steady_clock::now() < deadline) {
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
    pool.shutdown();
    std::cout << "stopped." << std::endl;
    return 0;
}
