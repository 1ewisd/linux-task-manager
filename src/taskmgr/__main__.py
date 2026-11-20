import signal

from .app import main

signal.signal(signal.SIGINT, signal.SIG_DFL)
main()
