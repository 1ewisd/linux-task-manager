"""Map running processes to desktop applications (name + icon) via .desktop files."""
import configparser
import functools
import glob
import os
import shlex


WRAPPERS = {"env", "flatpak", "run", "sh", "bash", "dash", "nohup", "setsid", "gtk-launch", "sudo"}
INTERP = ("python", "node", "java", "electron", "perl", "ruby", "wine")
GENERIC = {"python", "python3", "sh", "bash", "env", "java", "node", "wine", "electron", ""}


def exec_key(argv):
    toks = [t for t in argv if t]
    i = 0
    while i < len(toks):
        t = toks[i]
        b = os.path.basename(t).lower()
        if ("=" in b and not t.startswith("/")) or b in WRAPPERS or t.startswith(("-", "%")):
            i += 1
            continue
        if b.startswith(INTERP):
            j = i + 1
            while j < len(toks) and toks[j].startswith("-"):
                j += 1
            if j < len(toks):
                b = os.path.basename(toks[j]).lower()
        return b[:-3] if b.endswith(".py") else b
    return None


def load_apps():
    """Map lowercase process-ish keys -> (display name, icon)."""
    strong, weak = {}, {}
    dirs = ["/usr/share/applications", os.path.expanduser("~/.local/share/applications"),
            "/var/lib/flatpak/exports/share/applications",
            os.path.expanduser("~/.local/share/flatpak/exports/share/applications")]
    for d in dirs:
        for path in glob.glob(os.path.join(d, "*.desktop")):
            try:
                cp = configparser.RawConfigParser(strict=False)
                cp.read(path, encoding="utf-8")
                e = cp["Desktop Entry"]
                if e.get("Type", "Application") != "Application":
                    continue
                if e.get("NoDisplay", "").lower() == "true" or e.get("Hidden", "").lower() == "true":
                    continue
                if e.get("Terminal", "").lower() == "true":
                    continue
                name, icon = e.get("Name", ""), e.get("Icon", "")
                if not name:
                    continue
                argv = shlex.split(e.get("Exec", ""))
                val = (name, icon)
                k = exec_key(argv)
                if k and k not in GENERIC:
                    strong.setdefault(k, val)
                for t in argv:
                    if t.startswith("--command="):
                        strong.setdefault(t.split("=", 1)[1].lower(), val)
                wm = e.get("StartupWMClass", "").lower()
                if wm:
                    strong.setdefault(wm, val)
                stem = os.path.basename(path)[:-8].lower().split(".")[-1]
                weak.setdefault(stem, val)
                if icon:
                    weak.setdefault(os.path.basename(icon).lower().rsplit(".", 1)[0], val)
            except Exception:
                continue
    for k, v in weak.items():
        if k not in GENERIC:
            strong.setdefault(k, v)
    return strong


@functools.cache
def get_apps():
    return load_apps()


def lookup_app(row):
    apps = get_apps()
    cands = [os.path.basename(row["exe"]).lower(), row["name"].lower(), exec_key(row["cmd"]) or ""]
    for c in cands:
        for k in (c, c.removesuffix("-bin"), c.removesuffix("-stable")):
            if k and k not in GENERIC and k in apps:
                return apps[k]
    return None
