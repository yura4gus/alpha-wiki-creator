"""Exec-wrapper that installs POSIX rlimits, then replaces itself with the target.

Usage: `<python> limit_exec.py <cpu_s> <memory_bytes> <output_bytes> <argv...>`

It only uses `resource` and `os.execv`; no shell, no argument evaluation. If a
limit cannot be installed the wrapper exits 126 and prints the reason, so the
parent reports a configuration failure rather than running unbounded.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    if len(sys.argv) < 5:
        print("limit_exec: missing arguments", file=sys.stderr)
        return 126
    try:
        cpu_seconds = int(sys.argv[1])
        memory_bytes = int(sys.argv[2])
        output_bytes = int(sys.argv[3])
        argv = sys.argv[4:]
    except ValueError:
        print("limit_exec: non-integer limit", file=sys.stderr)
        return 126

    try:
        import resource
    except ImportError:
        print("limit_exec: POSIX resource limits are unavailable", file=sys.stderr)
        return 126

    def apply(kind, value, limit) -> bool:
        try:
            resource.setrlimit(limit, (value, value))
        except (ValueError, OSError) as exc:
            # Some kernels (notably macOS) expose RLIMIT_AS but reject lowering
            # it. Keep the CPU and output caps and record the unsupported one.
            if kind == "memory":
                print(f"limit_exec: memory rlimit unsupported: {exc}", file=sys.stderr)
                return False
            print(f"limit_exec: cannot install {kind} limit: {exc}", file=sys.stderr)
            raise
        return True

    try:
        if cpu_seconds > 0:
            apply("cpu", cpu_seconds, resource.RLIMIT_CPU)
        if memory_bytes > 0:
            apply("memory", memory_bytes, resource.RLIMIT_AS)
        if output_bytes > 0:
            apply("output", output_bytes, resource.RLIMIT_FSIZE)
    except (ValueError, OSError):
        return 126

    try:
        os.execv(argv[0], argv)
    except OSError as exc:
        print(f"limit_exec: cannot execute {argv[0]!r}: {exc}", file=sys.stderr)
        return 126


if __name__ == "__main__":
    sys.exit(main())
