# Routines from cpython Lib/test/support/__init__.py

import sys
import os
import errno
import gc


SAVEDCWD = "/"


def gc_collect():
    gc.collect()
    gc.collect()
    gc.collect()


def fd_count():
    """Count the number of open file descriptors.
    """
    if sys.platform.startswith(('linux', 'freebsd')):
        try:
            names = os.listdir("/proc/self/fd")
            # Substract one because listdir() opens internally a file
            # descriptor to list the content of the /proc/self/fd/ directory.
            return len(names) - 1
        except FileNotFoundError:
            pass

    MAXFD = 256
    if hasattr(os, 'sysconf'):
        try:
            MAXFD = os.sysconf("SC_OPEN_MAX")
        except OSError:
            pass

    old_modes = None
    if sys.platform == 'win32':
        # bpo-25306, bpo-31009: Call CrtSetReportMode() to not kill the process
        # on invalid file descriptor if Python is compiled in debug mode
        try:
            import msvcrt
            msvcrt.CrtSetReportMode
        except (AttributeError, ImportError):
            # no msvcrt or a release build
            pass
        else:
            old_modes = {}
            for report_type in (msvcrt.CRT_WARN,
                                msvcrt.CRT_ERROR,
                                msvcrt.CRT_ASSERT):
                old_modes[report_type] = msvcrt.CrtSetReportMode(
                    report_type, 0)

    try:
        count = 0
        for fd in range(MAXFD):
            try:
                # Prefer dup() over fstat(). fstat() can require input/output
                # whereas dup() doesn't.
                fd2 = os.dup(fd)
            except OSError as e:
                if e.errno != errno.EBADF:
                    raise
            else:
                os.close(fd2)
                count += 1
    finally:
        if old_modes is not None:
            for report_type in (msvcrt.CRT_WARN,
                                msvcrt.CRT_ERROR,
                                msvcrt.CRT_ASSERT):
                msvcrt.CrtSetReportMode(report_type, old_modes[report_type])

    return count
