from taskmgr.formatting import fmt_bits, fmt_bytes, fmt_mem, fmt_pct, fmt_rate, fmt_uptime


def test_bytes():
    assert fmt_bytes(512) == "512 B"
    assert fmt_bytes(1536) == "1.5 KB"


def test_mem_switches_to_gb():
    assert fmt_mem(100 * 1024**2) == "100.0 MB"
    assert fmt_mem(2 * 1024**3) == "2.00 GB"


def test_rate_and_bits():
    assert fmt_rate(1048576) == "1.0 MB/s"
    assert fmt_bits(125000) == "1.0 Mbps"


def test_pct():
    assert fmt_pct(0) == "0%"
    assert fmt_pct(4.56) == "4.6%"
    assert fmt_pct(42.4) == "42%"


def test_uptime():
    assert fmt_uptime(90061) == "1:01:01:01"
