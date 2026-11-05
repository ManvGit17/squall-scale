from nginx_conf import render_nginx_conf


def test_renders_all_backends():
    conf = render_nginx_conf(["backend-1", "backend-2"], port=8080)
    assert "server backend-1:8080 max_fails=3 fail_timeout=5s;" in conf
    assert "server backend-2:8080 max_fails=3 fail_timeout=5s;" in conf
    assert "proxy_pass http://backend_servers;" in conf
    assert "add_header X-Backend $upstream_addr always;" in conf


def test_empty_fleet_returns_503():
    conf = render_nginx_conf([])
    assert "return 503" in conf
    assert "upstream backend_servers" not in conf


def test_custom_port():
    conf = render_nginx_conf(["b"], port=9000)
    assert "server b:9000" in conf
