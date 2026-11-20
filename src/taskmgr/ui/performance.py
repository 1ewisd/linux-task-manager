"""Performance tab: live CPU / Memory / Disk / Network / GPU graphs."""
import collections
import time

import psutil
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QStackedWidget, QVBoxLayout, QWidget)

from ..formatting import fmt_bits, fmt_bytes, fmt_mem, fmt_rate, fmt_uptime
from ..sampling import NCPU


class Graph(QWidget):
    N = 60

    def __init__(self, color, series=1, fixed_max=None, floor=1.0, mini=False):
        super().__init__()
        self.color, self.fixed, self.floor, self.mini = QColor(color), fixed_max, floor, mini
        self.data = [collections.deque([0.0] * self.N, maxlen=self.N) for _ in range(series)]
        self.tick = 0
        if mini:
            self.setFixedSize(84, 52)
        else:
            self.setMinimumHeight(110)

    def scale(self):
        return self.fixed or max(self.floor, max(max(d) for d in self.data) * 1.1)

    def push(self, *vals):
        for d, v in zip(self.data, vals):
            d.append(float(v))
        self.tick += 1
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width() - 1, self.height() - 1
        p.fillRect(self.rect(), self.palette().base())
        grid = QColor(self.color)
        grid.setAlpha(55)
        if not self.mini:
            step = w / (self.N - 1)
            cell = step * 6
            p.setPen(QPen(grid, 1))
            x = w - (self.tick * step) % cell
            while x > 0:
                p.drawLine(int(x), 0, int(x), h)
                x -= cell
            for i in range(1, 4):
                p.drawLine(0, h * i // 4, w, h * i // 4)
        top = self.scale()
        for si, d in enumerate(self.data):
            pts = [QPointF(w * i / (self.N - 1), h - h * min(v / top, 1.0)) for i, v in enumerate(d)]
            if si == 0:
                fill = QColor(self.color)
                fill.setAlpha(60)
                path = QPainterPath(QPointF(0, h))
                for pt in pts:
                    path.lineTo(pt)
                path.lineTo(QPointF(w, h))
                path.closeSubpath()
                p.fillPath(path, fill)
            pen = QPen(self.color, 1.5)
            if si == 1:
                pen.setStyle(Qt.DashLine)
            p.setPen(pen)
            p.drawPolyline(QPolygonF(pts))
        p.setPen(QPen(self.color, 1))
        p.drawRect(0, 0, w, h)


class Page(QWidget):
    def __init__(self, title, color, graphs, fields, cols=4):
        super().__init__()
        v = QVBoxLayout(self)
        head = QHBoxLayout()
        self.title = QLabel(title)
        f = self.title.font()
        f.setPointSize(f.pointSize() + 8)
        self.title.setFont(f)
        self.sub = QLabel()
        self.sub.setStyleSheet("color: gray")
        head.addWidget(self.title)
        head.addStretch()
        head.addWidget(self.sub)
        v.addLayout(head)
        self.graphs, self.fmts, self.maxlabels = [], [], []
        for caption, series, fixed, fmt, floor in graphs:
            row = QHBoxLayout()
            row.addWidget(QLabel(caption))
            row.addStretch()
            ml = QLabel()
            row.addWidget(ml)
            v.addLayout(row)
            g = Graph(color, series, fixed, floor)
            v.addWidget(g, 1)
            foot = QHBoxLayout()
            foot.addWidget(QLabel("60 seconds"))
            foot.addStretch()
            foot.addWidget(QLabel("0"))
            v.addLayout(foot)
            self.graphs.append(g)
            self.fmts.append(fmt)
            self.maxlabels.append(ml)
        grid = QGridLayout()
        grid.setHorizontalSpacing(40)
        self.vals = {}
        for i, (key, caption) in enumerate(fields):
            cap = QLabel(caption)
            cap.setStyleSheet("color: gray")
            val = QLabel("–")
            vf = val.font()
            vf.setPointSize(vf.pointSize() + 5)
            val.setFont(vf)
            r, c = divmod(i, cols)
            grid.addWidget(cap, r * 2, c)
            grid.addWidget(val, r * 2 + 1, c)
            self.vals[key] = val
        v.addLayout(grid)

    def push(self, i, *vals):
        self.graphs[i].push(*vals)
        self.maxlabels[i].setText(self.fmts[i](self.graphs[i].scale()))

    def set(self, **kw):
        for k, txt in kw.items():
            self.vals[k].setText(txt)


class Card(QWidget):
    def __init__(self, title, color, series=1, fixed=100.0, floor=1.0):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(6, 4, 6, 4)
        self.graph = Graph(color, series, fixed, floor, mini=True)
        h.addWidget(self.graph)
        col = QVBoxLayout()
        col.setSpacing(0)
        t = QLabel(title)
        tf = t.font()
        tf.setBold(True)
        t.setFont(tf)
        self.sub = QLabel()
        sf = self.sub.font()
        sf.setPointSizeF(sf.pointSizeF() - 1)
        self.sub.setFont(sf)
        col.addStretch()
        col.addWidget(t)
        col.addWidget(self.sub)
        col.addStretch()
        h.addLayout(col)


class PerfTab(QWidget):
    def __init__(self, has_gpu):
        super().__init__()
        h = QHBoxLayout(self)
        self.list = QListWidget()
        self.list.setFixedWidth(265)
        self.stack = QStackedWidget()
        h.addWidget(self.list)
        h.addWidget(self.stack, 1)
        self.cards, self.pages = {}, {}
        pct = lambda m: f"{m:.0f}%"
        try:
            model = next(l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name"))
        except Exception:
            model = "CPU"
        vm = psutil.virtual_memory()
        specs = [
            ("cpu", "CPU", "#117dbb", Page("CPU", "#117dbb", [("% Utilization", 1, 100.0, pct, 1)],
                                          [("util", "Utilization"), ("speed", "Speed"), ("procs", "Processes"),
                                           ("threads", "Threads"), ("up", "Up time"), ("cores", "Cores"),
                                           ("logical", "Logical processors")]), Card("CPU", "#117dbb")),
            ("mem", "Memory", "#8b12ae", Page("Memory", "#8b12ae", [("Memory usage", 1, 100.0, pct, 1)],
                                              [("inuse", "In use"), ("avail", "Available"), ("cached", "Cached"),
                                               ("total", "Total"), ("swap", "Swap used")]), Card("Memory", "#8b12ae")),
            ("disk", "Disk", "#4daa32", Page("Disk", "#4daa32",
                                            [("Active time", 1, 100.0, pct, 1),
                                             ("Disk transfer rate", 2, None, fmt_rate, 1e6)],
                                            [("read", "Read speed"), ("write", "Write speed"),
                                             ("active", "Active time"), ("cap", "Root filesystem")]),
             Card("Disk", "#4daa32")),
            ("net", "Network", "#a35d1d", Page("Network", "#a35d1d", [("Throughput", 2, None, fmt_bits, 125000.0)],
                                              [("send", "Send"), ("recv", "Receive"), ("iface", "Interface"),
                                               ("ip", "IPv4 address")]), Card("Network", "#a35d1d", 2, None, 125000.0)),
        ]
        if has_gpu:
            specs.append(("gpu", "GPU", "#1a8f8f", Page("GPU", "#1a8f8f", [("% Utilization", 1, 100.0, pct, 1)],
                                                        [("util", "Utilization"), ("vram", "Dedicated GPU memory")]),
                          Card("GPU", "#1a8f8f")))
        for key, title, _c, page, card in specs:
            self.pages[key], self.cards[key] = page, card
            it = QListWidgetItem()
            it.setSizeHint(card.sizeHint().expandedTo(card.minimumSizeHint()))
            self.list.addItem(it)
            self.list.setItemWidget(it, card)
            self.stack.addWidget(page)
        self.pages["cpu"].sub.setText(model)
        self.pages["mem"].sub.setText(fmt_mem(vm.total))
        self.list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.list.setCurrentRow(0)

    @staticmethod
    def _net_info():
        iface, ip = "–", "–"
        for n, st in psutil.net_if_stats().items():
            if st.isup and not n.startswith(("lo", "veth", "docker", "br-", "virbr", "vnet")):
                iface = n
                for a in psutil.net_if_addrs().get(n, []):
                    if a.family.name == "AF_INET":
                        ip = a.address
                break
        return iface, ip

    def update(self, s, nprocs, nthreads, tick):
        P, C = self.pages, self.cards
        P["cpu"].push(0, s["cpu"])
        C["cpu"].graph.push(s["cpu"])
        C["cpu"].sub.setText(f'{s["cpu"]:.0f}%  {s["freq"] / 1000:.2f} GHz')
        P["cpu"].set(util=f'{s["cpu"]:.0f}%', speed=f'{s["freq"] / 1000:.2f} GHz', procs=str(nprocs),
                     threads=str(nthreads), up=fmt_uptime(time.time() - psutil.boot_time()),
                     cores=str(psutil.cpu_count(logical=False) or NCPU), logical=str(NCPU))
        m = s["mem"]
        P["mem"].push(0, m.percent)
        C["mem"].graph.push(m.percent)
        C["mem"].sub.setText(f"{(m.total - m.available) / 2**30:.1f}/{m.total / 2**30:.1f} GB ({m.percent:.0f}%)")
        P["mem"].set(inuse=fmt_mem(m.total - m.available), avail=fmt_mem(m.available),
                     cached=fmt_mem(getattr(m, "cached", 0)), total=fmt_mem(m.total),
                     swap=f'{fmt_mem(s["swap"].used)} / {fmt_mem(s["swap"].total)}')
        d = s["disk"]
        P["disk"].push(0, d["active"])
        P["disk"].push(1, d["read"], d["write"])
        C["disk"].graph.push(d["active"])
        C["disk"].sub.setText(f'{d["active"]:.0f}%  {fmt_rate(d["read"] + d["write"])}')
        if tick % 10 == 0:
            du = psutil.disk_usage("/")
            P["disk"].set(cap=f"{fmt_bytes(du.used)} / {fmt_bytes(du.total)}")
            iface, ip = self._net_info()
            P["net"].set(iface=iface, ip=ip)
            P["net"].sub.setText(iface)
        P["disk"].set(read=fmt_rate(d["read"]), write=fmt_rate(d["write"]), active=f'{d["active"]:.0f}%')
        n = s["net"]
        P["net"].push(0, n["sent"], n["recv"])
        C["net"].graph.push(n["sent"], n["recv"])
        C["net"].sub.setText(f'S: {fmt_bits(n["sent"])}  R: {fmt_bits(n["recv"])}')
        P["net"].set(send=fmt_bits(n["sent"]), recv=fmt_bits(n["recv"]))
        if "gpu" in s:
            g = s["gpu"]
            P["gpu"].push(0, g["busy"])
            C["gpu"].graph.push(g["busy"])
            C["gpu"].sub.setText(f'{g["busy"]:.0f}%')
            P["gpu"].set(util=f'{g["busy"]:.0f}%', vram=f'{fmt_mem(g["vram_used"])} / {fmt_mem(g["vram_total"])}')
