"""Human-readable formatting helpers."""


def fmt_bytes(n):
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def fmt_mem(n):
    return f"{n / 1048576:.1f} MB" if n < 1073741824 else f"{n / 1073741824:.2f} GB"


def fmt_rate(n):
    return f"{n / 1048576:.1f} MB/s"


def fmt_bits(n):
    bits = n * 8
    if bits >= 1e6:
        return f"{bits / 1e6:.1f} Mbps"
    return f"{bits / 1e3:.0f} Kbps"


def fmt_pct(v):
    return "0%" if v < 0.05 else (f"{v:.1f}%" if v < 10 else f"{v:.0f}%")


def fmt_uptime(sec):
    sec = int(sec)
    d, r = divmod(sec, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    return f"{d}:{h:02d}:{m:02d}:{s:02d}"
