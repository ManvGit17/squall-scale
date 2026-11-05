from scrape import (
    Sample, parse_host, parse_prometheus, recent_latency_ms,
    recent_throughput_rps,
)

SAMPLE = """\
# HELP squallscale_requests_total Requests served.
# TYPE squallscale_requests_total counter
squallscale_requests_total 100
# TYPE squallscale_requests_in_flight gauge
squallscale_requests_in_flight 3
squallscale_request_duration_seconds_sum 5.0
squallscale_request_duration_seconds_count 100
squallscale_uptime_seconds 42.5
squallscale_backend_info{host="backend-9"} 1
"""


def test_parse_prometheus_skips_comments_and_labels():
    m = parse_prometheus(SAMPLE)
    assert m["squallscale_requests_total"] == 100.0
    assert m["squallscale_requests_in_flight"] == 3.0
    assert m["squallscale_request_duration_seconds_count"] == 100.0
    # Labelled series are not in the flat map.
    assert "squallscale_backend_info" not in m


def test_parse_host():
    assert parse_host(SAMPLE) == "backend-9"
    assert parse_host("nothing here") is None


def test_sample_from_text():
    s = Sample.from_text(SAMPLE)
    assert s.requests_total == 100.0
    assert s.duration_sum == 5.0
    assert s.uptime == 42.5


def test_recent_latency_from_deltas():
    prev = Sample(duration_sum=5.0, duration_count=100)
    cur = Sample(duration_sum=7.0, duration_count=110)
    # 2.0s over 10 requests = 200ms average.
    assert recent_latency_ms(prev, cur) == 200.0


def test_recent_latency_none_when_idle():
    prev = Sample(duration_sum=5.0, duration_count=100)
    cur = Sample(duration_sum=5.0, duration_count=100)
    assert recent_latency_ms(prev, cur) is None


def test_recent_throughput():
    prev = Sample(duration_count=100)
    cur = Sample(duration_count=140)
    assert recent_throughput_rps(prev, cur, 2.0) == 20.0
