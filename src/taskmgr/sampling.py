"""Process and system sampling built on psutil."""
import glob
import os
import pwd
import time

import psutil

NCPU = psutil.cpu_count() or 1


class Sampler:
    def __init__(self):
        self.static, self.prev_io, self.no_io = {}, {}, set()
        self.last = time.monotonic()
        self.users = {}

    def _user(self, uid):
        if uid not in self.users:
            try:
                self.users[uid] = pwd.getpwuid(uid).pw_name
            except KeyError:
                self.users[uid] = str(uid)
        return self.users[uid]

    def _static(self, p, ct):
        try:
            cmd = p.cmdline()
        except psutil.Error:
            cmd = []
        try:
            exe = p.exe()
        except psutil.Error:
            exe = ""
        ppid = p.ppid()
        return dict(ct=ct, cmd=cmd, exe=exe, ppid=ppid, user=self._user(p.uids().real),
                    kernel=(p.pid == 2 or ppid == 2))

    def sample(self):
        now = time.monotonic()
        dt = max(now - self.last, 1e-3)
        self.last = now
        rows, seen = [], set()
        for p in psutil.process_iter():
            try:
                with p.oneshot():
                    pid = p.pid
                    ct = p.create_time()
                    st = self.static.get(pid)
                    if st is None or st["ct"] != ct:
                        st = self.static[pid] = self._static(p, ct)
                    name = p.name()
                    cpu = p.cpu_percent(None) / NCPU
                    mi = p.memory_info()
                    status = p.status()
                    threads = p.num_threads()
                    io = 0.0
                    if pid not in self.no_io:
                        try:
                            c = p.io_counters()
                            tot = c.read_bytes + c.write_bytes
                            prev = self.prev_io.get(pid)
                            if prev is not None:
                                io = max(tot - prev, 0) / dt
                            self.prev_io[pid] = tot
                        except (psutil.AccessDenied, AttributeError):
                            self.no_io.add(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            seen.add(pid)
            rows.append(dict(pid=pid, name=name, cpu=cpu, mem=max(mi.rss - getattr(mi, "shared", 0), 0),
                             disk=io, status=status, threads=threads, exe=st["exe"], cmd=st["cmd"],
                             user=st["user"], kernel=st["kernel"], ppid=st["ppid"]))
        for d in (self.static, self.prev_io):
            for pid in [k for k in d if k not in seen]:
                del d[pid]
        self.no_io &= seen
        return rows


class SysSampler:
    def __init__(self):
        self.t = time.monotonic()
        self.disk = self._disk()
        self.net = self._net()
        self.gpu = glob.glob("/sys/class/drm/card*/device/gpu_busy_percent")
        psutil.cpu_percent(None)

    @staticmethod
    def _disk():
        out = {}
        for n, c in psutil.disk_io_counters(perdisk=True).items():
            if os.path.exists(f"/sys/block/{n}") and not n.startswith(("loop", "ram", "zram")):
                out[n] = c
        return out

    @staticmethod
    def _net():
        sent = recv = 0
        for n, c in psutil.net_io_counters(pernic=True).items():
            if not n.startswith(("lo", "veth", "docker", "br-", "virbr", "vnet")):
                sent += c.bytes_sent
                recv += c.bytes_recv
        return sent, recv

    @staticmethod
    def _read(path, default=0):
        try:
            with open(path) as f:
                return int(f.read().strip())
        except (OSError, ValueError):
            return default

    def sample(self):
        now = time.monotonic()
        dt = max(now - self.t, 1e-3)
        self.t = now
        d = {}
        d["cpu"] = psutil.cpu_percent(None)
        f = psutil.cpu_freq()
        d["freq"] = f.current if f else 0
        d["mem"] = psutil.virtual_memory()
        d["swap"] = psutil.swap_memory()
        nd = self._disk()
        rd = wr = 0
        busy = 0.0
        for n, c in nd.items():
            p = self.disk.get(n)
            if p:
                rd += c.read_bytes - p.read_bytes
                wr += c.write_bytes - p.write_bytes
                busy = max(busy, (getattr(c, "busy_time", 0) - getattr(p, "busy_time", 0)) / (dt * 10))
        self.disk = nd
        d["disk"] = dict(read=max(rd, 0) / dt, write=max(wr, 0) / dt, active=min(busy, 100.0))
        sent, recv = self._net()
        d["net"] = dict(sent=max(sent - self.net[0], 0) / dt, recv=max(recv - self.net[1], 0) / dt)
        self.net = (sent, recv)
        if self.gpu:
            base = os.path.dirname(self.gpu[0])
            d["gpu"] = dict(busy=self._read(self.gpu[0]), vram_used=self._read(base + "/mem_info_vram_used"),
                            vram_total=self._read(base + "/mem_info_vram_total"))
        return d
