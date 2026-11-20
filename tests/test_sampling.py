import os

from taskmgr.sampling import Sampler, SysSampler


def test_sampler_sees_this_process():
    s = Sampler()
    s.sample()
    rows = s.sample()
    me = next(r for r in rows if r["pid"] == os.getpid())
    assert me["mem"] > 0 and me["threads"] >= 1


def test_system_sample_shape():
    s = SysSampler()
    d = s.sample()
    assert 0 <= d["cpu"] <= 100
    assert {"read", "write", "active"} <= d["disk"].keys()
    assert {"sent", "recv"} <= d["net"].keys()
