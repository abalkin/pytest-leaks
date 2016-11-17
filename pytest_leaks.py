# -*- coding: utf-8 -*-
"""
A pytest plugin to trace resource leaks
"""
from __future__ import print_function

import sys
import gc
import warnings
from inspect import isabstract
from collections import OrderedDict as odict

import pytest

_py3 = sys.version_info[0] >= 3


def pytest_addoption(parser):
    group = parser.getgroup('leaks')
    group.addoption(
        '-R', '--leaks',
        action='store',
        dest='leaks',
        help='''\
runs each test several times and examines sys.gettotalrefcount() to
see if the test appears to be leaking references.  The argument should
be of the form stab:run:fname where 'stab' is the number of times the
test is run to let gettotalrefcount settle down, 'run' is the number
of times further it is run and 'fname' is the name of the file the
reports are written to.  These parameters all have defaults (5, 4 and
"reflog.txt" respectively), and the minimal invocation is '-R :'.
'''
    )

    parser.addini('leaks_stab',
                  'the number of times the test is run to let '
                  'gettotalrefcount settle down', default=5)
    parser.addini('leaks_run',
                  'the number of times the test is run', default=4)


def pytest_configure(config):
    leaks = config.getvalue("leaks")
    if leaks:
        checker = LeakChecker(config)
        config.pluginmanager.register(checker, 'leaks_checker')


@pytest.fixture
def leaks_checker(request):
    return request.config.pluginmanager.get_plugin('leaks_checker')


class Leaks(odict):
    pass


class LeakChecker(object):
    def __init__(self, config):
        self.stab = 4
        self.run = 1
        # TODO: get defaults from config.
        # Get access to the builtin "runner" plugin.
        self.runner = config.pluginmanager.get_plugin('runner')
        self.leaks = {}  # nodeid -> leaks

    def hunt_leaks(self, func):
        return hunt_leaks(func, self.stab, self.run)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item, nextitem):
        def run_test():
            hook = item.ihook
            hook.pytest_runtest_setup(item=item)
            hook.pytest_runtest_call(item=item)
            hook.pytest_runtest_teardown(item=item, nextitem=nextitem)

        call = self.runner.CallInfo(lambda: self.hunt_leaks(run_test),
                                    'leakshunt')
        if call.excinfo is None and call.result:
            self.leaks[item.nodeid] = call.result
        yield

    @pytest.hookimpl(hookwrapper=True, trylast=True)
    def pytest_report_teststatus(self, report):
        outcome = yield
        if report.when == 'call' and report.outcome == 'passed':
            leaks = self.leaks.get(report.nodeid)
            if leaks:
                # cat, letter, word
                outcome.force_result(('leaked', 'L', 'LEAKED'))

    @pytest.hookimpl
    def pytest_terminal_summary(self, terminalreporter, exitstatus):
        tr = terminalreporter
        leaked = tr.getreports('leaked')
        if leaked:
            tr.write_sep("=", 'leaks summary', cyan=True)
            for rep in leaked:
                tr.line("%s: %r" % (rep.nodeid, self.leaks[rep.nodeid]))


def hunt_leaks(func, nwarmup, ntracked):
    """Run a func multiple times, looking for leaks."""
    # This code is hackish and inelegant, but it seems to do the job.
    import copyreg
    import collections.abc

    # Save current values for cleanup() to restore.
    fs = warnings.filters[:]
    ps = copyreg.dispatch_table.copy()
    pic = sys.path_importer_cache.copy()
    try:
        import zipimport
    except ImportError:
        zdc = None  # Run unmodified on platforms without zipimport support
    else:
        zdc = zipimport._zip_directory_cache.copy()
    abcs = {}
    for abc in [getattr(collections.abc, a) for a in collections.abc.__all__]:
        if not isabstract(abc):
            continue
        for obj in abc.__subclasses__() + [abc]:
            abcs[obj] = obj._abc_registry.copy()
    repcount = nwarmup + ntracked
    rc_deltas = [0] * repcount
    alloc_deltas = [0] * repcount
    # initialize variables to make pyflakes quiet
    rc_before = alloc_before = 0
    for i in range(repcount):
        func()
        alloc_after, rc_after = cleanup(fs, ps, pic, zdc, abcs)
        if i >= nwarmup:
            rc_deltas[i] = rc_after - rc_before
            alloc_deltas[i] = alloc_after - alloc_before
        alloc_before = alloc_after
        rc_before = rc_after

    # These checkers return False on success, True on failure
    def check_rc_deltas(deltas):
        return any(deltas)

    def check_alloc_deltas(deltas):
        # At least 1/3rd of 0s
        if 3 * deltas.count(0) < len(deltas):
            return True
        # Nothing else than 1s, 0s and -1s
        if not set(deltas) <= {1, 0, -1}:
            return True
        return False

    leaks = Leaks()
    for deltas, item_name, checker in [
        (rc_deltas, 'refs', check_rc_deltas),
        (alloc_deltas, 'blocks', check_alloc_deltas)
    ]:
        if checker(deltas):
            leaks[item_name] = deltas[nwarmup:]
    return leaks

# The following code is mostly copied from Python 2.7 / 3.5 dash_R_cleanup
if _py3:
    def cleanup(warning_filters, copyreg_dispatch_table, path_importer_cache,
                zip_directory_cache, abcs):
        import copyreg
        import re
        import warnings
        import _strptime
        import linecache
        import urllib.parse
        import urllib.request
        import mimetypes
        import doctest
        import struct
        import filecmp
        import collections.abc
        from distutils.dir_util import _path_created
        from weakref import WeakSet

        # Clear the warnings registry, so they can be displayed again
        for mod in sys.modules.values():
            if hasattr(mod, '__warningregistry__'):
                del mod.__warningregistry__

        # Restore some original values.
        warnings.filters[:] = warning_filters
        copyreg.dispatch_table.clear()
        copyreg.dispatch_table.update(copyreg_dispatch_table)
        sys.path_importer_cache.clear()
        sys.path_importer_cache.update(path_importer_cache)
        try:
            import zipimport
        except ImportError:
            pass  # Run unmodified on platforms without zipimport support
        else:
            zipimport._zip_directory_cache.clear()
            zipimport._zip_directory_cache.update(zip_directory_cache)

        # clear type cache
        sys._clear_type_cache()

        # Clear ABC registries, restoring previously saved ABC registries.
        for a in collections.abc.__all__:
            abc = getattr(collections.abc, a)
            if not isabstract(abc):
                continue
            for obj in abc.__subclasses__() + [abc]:
                obj._abc_registry = abcs.get(obj, WeakSet()).copy()
                obj._abc_cache.clear()
                obj._abc_negative_cache.clear()

        # Flush standard output, so that buffered data is sent to the OS and
        # associated Python objects are reclaimed.
        for stream in (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__):
            if stream is not None:
                stream.flush()

        # Clear assorted module caches.
        _path_created.clear()
        re.purge()
        _strptime._regex_cache.clear()
        urllib.parse.clear_cache()
        urllib.request.urlcleanup()
        linecache.clearcache()
        mimetypes._default_mime_types()
        filecmp._cache.clear()
        struct._clearcache()
        doctest.master = None
        try:
            import ctypes
        except ImportError:
            # Don't worry about resetting the cache if ctypes is not supported
            pass
        else:
            ctypes._reset_cache()

        # Collect cyclic trash and read memory statistics immediately after.
        func1 = sys.getallocatedblocks
        func2 = sys.gettotalrefcount
        gc.collect()
        return func1(), func2()
else:
    def cleanup(warning_filters, copyreg_dispatch_table, path_importer_cache,
                zip_directory_cache, abcs):
        pass
