# -*- coding: utf-8 -*-
"""
A pytest plugin to trace resource leaks
"""
from __future__ import print_function

import sys
import gc
import warnings
from inspect import isabstract
from array import array
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
def config_options(request):
    return request.config.option


@pytest.fixture
def getini(request):
    return request.config.getini


@pytest.fixture
def leaks_checker(request):
    return request.config.pluginmanager.get_plugin('leaks_checker')


class Leaks(odict):
    pass


class LeakChecker(object):
    def __init__(self, config):
        self.stab = 4
        self.run = 1
        # TODO: det defaults from config.
        self.count_blocks = 0 and hasattr(sys, 'getallocatedblocks')
        self.count_refs = 1 and hasattr(sys, 'gettotalrefcount')
        self.test_resource_count = 0
        self.resources = self.find_resources()
        n = len(self.resources)
        self.counts_before = array('l', [0] * n)
        self.counts_after = array('l', [0] * n)

    def find_resources(self):
        resources = odict()
        resources['test'] = lambda: self.test_resource_count
        if self.count_refs:
            resources['refs'] = sys.gettotalrefcount
        if self.count_blocks:
            resources['blocks'] = sys.getallocatedblocks
        return resources

    def leak(self):
        self.test_resource_count += 1

    def get_counts(self):
        gc.collect()
        counts = [f() for f in self.resources.values()]
        return array('l', counts)

    def get_leaks(self):
        leaks = Leaks()
        for n, (b, a) in zip(self.resources,
                             zip(self.counts_before,
                                 self.counts_after)):
            if b != a:
                leaks[n] = a - b
        return leaks

    def hunt_leaks(self, func):
        return hunt_leaks(func, self.stab, self.run)

    @pytest.hookimpl(hookwrapper=True, trylast=True)
    def pytest_runtest_call(self, item):
        for _ in range(self.stab):
            item.runtest()  # warm-up runs
        self.counts_before[:] = self.get_counts()
        for _ in range(self.run - 1):
            item.runtest()  # extra runs
        outcome = yield  # This runs the test for the last time
        self.counts_after[:] = self.get_counts()
        leaks = self.get_leaks()
        if leaks:
            outcome.force_result(leaks)

    @pytest.hookimpl(hookwrapper=True, trylast=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        # Find Leaks object in result
        if call.when == 'call':
            # NB: call may not have the result attribute
            r = getattr(call, 'result', None)
            if isinstance(r, Leaks):
                outcome.result.leaks = r

    @pytest.hookimpl(hookwrapper=True, trylast=True)
    def pytest_report_teststatus(self, report):
        outcome = yield
        if hasattr(report, 'leaks'):
            # cat, letter, word
            outcome.force_result(('leaked', 'L', 'LEAKED'))

    @pytest.hookimpl
    def pytest_terminal_summary(self, terminalreporter, exitstatus):
        tr = terminalreporter
        leaked = tr.getreports('leaked')
        if leaked:
            tr.write_sep("=", 'leaks summary', cyan=True)
            for rep in leaked:
                tr.line("%s: %r" % (rep.nodeid, rep.leaks))


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

    leaks = {}
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
        import gc
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
        for abc in [getattr(collections.abc, a) for a in collections.abc.__all__]:
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
