from taskmgr.apps import exec_key


def test_plain_binary():
    assert exec_key(["/usr/bin/firefox", "%u"]) == "firefox"


def test_env_and_wrappers_skipped():
    assert exec_key(["env", "FOO=1", "/opt/app/bin/thing", "--flag"]) == "thing"


def test_interpreter_uses_script_name():
    assert exec_key(["python3", "-u", "/home/x/taskmgr.py"]) == "taskmgr"


def test_flatpak_run():
    assert exec_key(["flatpak", "run", "--branch=stable", "org.example.App"]) == "org.example.app"
