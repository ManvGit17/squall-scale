// Minimal, dependency-free HTTP helpers.
//
// Only what a tiny backend needs: pull the method and path out of a request
// line, and build a small plain-text or JSON response. Kept header-only and
// free of sockets so it can be unit-tested on its own.
#pragma once

#include <string>
#include <string_view>

namespace ss::http {

struct Request {
    std::string method;  // e.g. "GET"; empty if the line could not be parsed
    std::string path;    // e.g. "/metrics"; query string stripped
};

// Parse the first line of an HTTP request, e.g. "GET /metrics?x=1 HTTP/1.1".
// Returns an empty method/path when the line is malformed. The query string
// (everything from '?') is dropped so routing matches on the path alone.
inline Request parse_request_line(std::string_view raw) {
    Request req;

    // The request line ends at the first CR or LF.
    const std::size_t line_end = raw.find_first_of("\r\n");
    std::string_view line = (line_end == std::string_view::npos)
                                ? raw
                                : raw.substr(0, line_end);

    const std::size_t first_space = line.find(' ');
    if (first_space == std::string_view::npos) return req;
    const std::size_t second_space = line.find(' ', first_space + 1);
    if (second_space == std::string_view::npos) return req;

    req.method = std::string(line.substr(0, first_space));

    std::string_view target =
        line.substr(first_space + 1, second_space - first_space - 1);
    // A request target for this server is an origin-form path: it must start
    // with '/'. Anything else is treated as malformed.
    if (target.empty() || target.front() != '/') {
        req.method.clear();
        return req;
    }

    const std::size_t query = target.find('?');
    if (query != std::string_view::npos) target = target.substr(0, query);
    req.path = std::string(target);
    return req;
}

// Build a complete HTTP/1.1 response with an explicit length and a
// Connection: close header (the server closes after every response).
inline std::string make_response(int status, std::string_view reason,
                                 std::string_view content_type,
                                 std::string_view body) {
    std::string out;
    out.reserve(body.size() + 128);
    out += "HTTP/1.1 ";
    out += std::to_string(status);
    out += ' ';
    out += reason;
    out += "\r\nContent-Type: ";
    out += content_type;
    out += "\r\nContent-Length: ";
    out += std::to_string(body.size());
    out += "\r\nConnection: close\r\n\r\n";
    out += body;
    return out;
}

}  // namespace ss::http
