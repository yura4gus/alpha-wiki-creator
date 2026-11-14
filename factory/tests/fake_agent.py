"""Scripted stand-in for an agent CLI. Real CLIs (opencode, codex) plug in the same way."""
import os
import pathlib
import sys
import time

cmd, *rest = sys.argv[1:]
if cmd == "write":
    path, text = rest
    target = pathlib.Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text + "\n")
elif cmd == "slow-write":
    path, text, seconds = rest
    time.sleep(float(seconds))
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text(text + "\n")
elif cmd == "sleep":
    seconds, pidfile = rest
    pathlib.Path(pidfile).write_text(str(os.getpid()))
    time.sleep(float(seconds))
elif cmd == "noop":
    pass
elif cmd == "fail":
    print("agent failed on purpose")
    sys.exit(3)
else:
    sys.exit(2)
