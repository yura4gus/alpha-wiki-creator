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
elif cmd == "context":
    target = pathlib.Path(rest[0])
    source = os.environ.get("FACTORY_CONTEXT_FILE", "")
    if not source or not pathlib.Path(source).is_file():
        print("pinned context file is missing")
        sys.exit(4)
    text = pathlib.Path(source).read_text()
    if "# Task " not in text:
        print("pinned context file has no task header")
        sys.exit(5)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("context recovered\n")
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
